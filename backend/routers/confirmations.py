import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import (
    UserSession, Form, FormField, ConfirmationNonce,
    FieldStatus, FormStatus, BoundAction, AuditLog, EventType
)
from schemas import (
    ConfirmationCreateRequest, ConfirmationCreateResponse,
    ConfirmationRespondRequest, ConfirmationRespondResponse,
)
from services.nonce_service import (
    create_nonce, validate_and_consume, build_challenge_audio_text
)
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/confirmations", tags=["confirmations"])
logger = logging.getLogger("finaccess.confirmations")


@router.post("", response_model=ConfirmationCreateResponse)
def issue_challenge(data: ConfirmationCreateRequest, db: DBSession = Depends(get_db)):
    """
    Issue a new randomized challenge nonce for a given action.
    Used when the frontend needs to trigger a fresh confirmation gate.
    """
    session = db.query(UserSession).filter(UserSession.id == data.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if data.bound_action == BoundAction.CONFIRM_FIELD:
        field = db.query(FormField).join(Form).filter(
            FormField.id == data.bound_target_id,
            Form.session_id == data.session_id,
        ).first()
        if not field:
            raise HTTPException(status_code=404, detail="Field not found")
    elif data.bound_action == BoundAction.SUBMIT_FORM:
        form = db.query(Form).filter(
            Form.id == data.bound_target_id,
            Form.session_id == data.session_id,
        ).first()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        unanswered = db.query(FormField).filter(
            FormField.form_id == form.id,
            FormField.status.notin_([FieldStatus.CONFIRMED, FieldStatus.SKIPPED]),
            FormField.confirmed_value.is_(None),
        ).first()
        if unanswered:
            raise HTTPException(status_code=409, detail="Resolve every field before final confirmation")

    nonce = create_nonce(
        db=db,
        session_id=data.session_id,
        bound_action=data.bound_action,
        bound_target_id=data.bound_target_id,
    )

    lang = session.preferred_language if session else "en"
    return ConfirmationCreateResponse(
        nonce_id=nonce.id,
        challenge_phrase=nonce.challenge_phrase,
        challenge_digits=nonce.challenge_digits,
        challenge_audio_text=build_challenge_audio_text(nonce.challenge_digits, language=lang),
        expires_in_seconds=settings.NONCE_EXPIRY_SECONDS,
        bound_action=str(nonce.bound_action.value),
        bound_target_id=nonce.bound_target_id,
    )


@router.post("/{nonce_id}/respond", response_model=ConfirmationRespondResponse)
def respond_to_challenge(
    nonce_id: str,
    data: ConfirmationRespondRequest,
    db: DBSession = Depends(get_db),
):
    """
    Submit spoken transcription for a challenge nonce.
    Server validates: nonce exists, not expired, not consumed, session matches, phrase matches.
    On success: consumes nonce and commits the bound action.
    On failure: returns new nonce for retry.
    """
    # Load nonce first to get action context
    nonce: ConfirmationNonce | None = db.query(ConfirmationNonce).filter(
        ConfirmationNonce.id == nonce_id
    ).first()
    if not nonce:
        raise HTTPException(status_code=404, detail="Nonce not found")

    result = validate_and_consume(
        db=db,
        nonce_id=nonce_id,
        session_id=data.session_id,
        transcribed_text=data.transcribed_text,
    )

    if result.success:
        # Commit the bound action
        action_committed = _commit_action(
            db=db,
            bound_action=nonce.bound_action,
            bound_target_id=nonce.bound_target_id,
            session_id=data.session_id,
        )
        return ConfirmationRespondResponse(
            success=True,
            nonce_id=nonce_id,
            message="Confirmed successfully! Moving to the next step.",
            action_committed=action_committed,
        )
    else:
        # Issue a fresh nonce for retry (if not a session/action mismatch)
        new_nonce_resp = None
        if "mismatch" not in result.reason.lower():
            try:
                new_nonce = create_nonce(
                    db=db,
                    session_id=data.session_id,
                    bound_action=nonce.bound_action,
                    bound_target_id=nonce.bound_target_id,
                )
                session_obj = db.query(UserSession).filter(UserSession.id == data.session_id).first()
                retry_lang = session_obj.preferred_language if session_obj else "en"
                new_nonce_resp = ConfirmationCreateResponse(
                    nonce_id=new_nonce.id,
                    challenge_phrase=new_nonce.challenge_phrase,
                    challenge_digits=new_nonce.challenge_digits,
                    challenge_audio_text=build_challenge_audio_text(new_nonce.challenge_digits, language=retry_lang),
                    expires_in_seconds=settings.NONCE_EXPIRY_SECONDS,
                    bound_action=str(new_nonce.bound_action.value),
                    bound_target_id=new_nonce.bound_target_id,
                )
            except Exception:
                pass

        return ConfirmationRespondResponse(
            success=False,
            nonce_id=nonce_id,
            message=result.reason,
            action_committed=False,
            new_nonce=new_nonce_resp,
        )


def _commit_action(
    db: DBSession,
    bound_action: BoundAction,
    bound_target_id: str,
    session_id: str,
) -> bool:
    """Execute the action that was gated behind the confirmation."""
    try:
        if bound_action == BoundAction.CONFIRM_FIELD:
            field = db.query(FormField).join(Form).filter(
                FormField.id == bound_target_id,
                Form.session_id == session_id,
            ).first()
            if field and field.confirmed_value is not None:
                # One successful phrase challenge confirms the current field
                # and all earlier answered fields in this three-question batch.
                batch_fields = db.query(FormField).filter(
                    FormField.form_id == field.form_id,
                    FormField.order_index <= field.order_index,
                    FormField.status != FieldStatus.SKIPPED,
                    FormField.confirmed_value.isnot(None),
                ).order_by(FormField.order_index).all()
                field_ids = [item.id for item in batch_fields]
                for item in batch_fields:
                    if item.status != FieldStatus.CONFIRMED:
                        item.status = FieldStatus.CONFIRMED
                        db.add(AuditLog(
                            session_id=session_id,
                            event_type=EventType.FIELD_CONFIRMED,
                            payload={
                                "field_id": item.id,
                                "label": item.label,
                                "value": item.confirmed_value,
                                "confirmation_method": "voice_batch_challenge",
                            },
                        ))
                if field_ids:
                    db.query(ConfirmationNonce).filter(
                        ConfirmationNonce.session_id == session_id,
                        ConfirmationNonce.bound_action == BoundAction.CONFIRM_FIELD,
                        ConfirmationNonce.bound_target_id.in_(field_ids),
                        ConfirmationNonce.consumed == False,
                    ).update({"consumed": True, "consumed_at": datetime.now(timezone.utc)})
                db.commit()
                return field.status == FieldStatus.CONFIRMED

        elif bound_action == BoundAction.SUBMIT_FORM:
            form = db.query(Form).filter(
                Form.id == bound_target_id, Form.session_id == session_id
            ).first()
            if form:
                unanswered = db.query(FormField).filter(
                    FormField.form_id == form.id,
                    FormField.status.notin_([FieldStatus.CONFIRMED, FieldStatus.SKIPPED]),
                    FormField.confirmed_value.is_(None),
                ).first()
                if unanswered:
                    return False
                pending_fields = db.query(FormField).filter(
                    FormField.form_id == form.id,
                    FormField.status.notin_([FieldStatus.CONFIRMED, FieldStatus.SKIPPED]),
                    FormField.confirmed_value.isnot(None),
                ).order_by(FormField.order_index).all()
                for field in pending_fields:
                    field.status = FieldStatus.CONFIRMED
                    db.add(AuditLog(
                        session_id=session_id,
                        event_type=EventType.FIELD_CONFIRMED,
                        payload={
                            "field_id": field.id,
                            "label": field.label,
                            "value": field.confirmed_value,
                            "confirmation_method": "final_voice_challenge",
                        },
                    ))
                form.status = FormStatus.COMPLETED
                db.commit()
                return True

        elif bound_action == BoundAction.CONFIRM_SCHEME_APPLICATION:
            db.add(AuditLog(
                session_id=session_id,
                event_type=EventType.SCHEME_MATCHED,
                payload={"scheme_id": bound_target_id, "status": "application_confirmed"},
            ))
            db.commit()
            return True

    except Exception as e:
        db.rollback()
        logger.exception("Failed to commit confirmation action")
        return False

    return False

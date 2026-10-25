import os
import uuid
import shutil
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form as FastForm
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import (
    UserSession, Form, FormField, ConfirmationNonce, AuditLog,
    FormStatus, FieldStatus, EventType, BoundAction
)
from schemas import (
    FormUploadResponse, FieldSchema, NextFieldResponse,
    FieldAnswerRequest, FieldAnswerResponse, FormFinalizeResponse,
    FieldPosition
)
from services import ocr_service, voice_service, pdf_service, otp_service
from services.form_language import translate_label, localized_question, form_value
from services.nonce_service import create_nonce, build_challenge_audio_text
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/forms", tags=["forms"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def _revoke_field_nonces(db: DBSession, session_id: str, field_id: str) -> None:
    db.query(ConfirmationNonce).filter(
        ConfirmationNonce.session_id == session_id,
        ConfirmationNonce.bound_action == BoundAction.CONFIRM_FIELD,
        ConfirmationNonce.bound_target_id == field_id,
        ConfirmationNonce.consumed == False,
    ).update({"consumed": True, "consumed_at": datetime.now(timezone.utc)})


def _find_generated_pdf(form_id: str) -> Optional[str]:
    matches = [
        os.path.join(settings.UPLOAD_DIR, name)
        for name in os.listdir(settings.UPLOAD_DIR)
        if name.startswith(f"form_{form_id}_") and name.endswith(".pdf")
    ]
    if not matches:
        matches = [
            os.path.join(settings.UPLOAD_DIR, name)
            for name in os.listdir(settings.UPLOAD_DIR)
            if name.startswith(f"form_{form_id}") and name.endswith(".pdf")
        ]
    if not matches:
        return None
    matches.sort(key=os.path.getmtime)
    return matches[-1]


@router.post("/upload", response_model=FormUploadResponse)
async def upload_form(
    session_id: str = FastForm(...),
    file: UploadFile = File(...),
    language: Optional[str] = FastForm(None),
    db: DBSession = Depends(get_db),
):
    """Upload a form image/PDF and extract structured field schema via OCR."""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    norm_lang = (language or (session.preferred_language if session else "hi")).split("-")[0].lower()
    if settings.MFA_REQUIRED and not otp_service.is_session_verified(session):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "form_auth_required",
                "message": "Verify your phone before uploading a form.",
            },
        )
    if not session:
        # Gracefully auto-create session so uploads never fail if user hasn't visited landing first
        new_sid = session_id if session_id and session_id != "demo-session" else str(uuid.uuid4())
        session = UserSession(
            id=new_sid,
            preferred_language=norm_lang,
            started_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    elif language and session.preferred_language != norm_lang:
        session.preferred_language = norm_lang
        db.commit()

    # Save uploaded file
    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    saved_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run OCR
    ocr_result = ocr_service.process_form_image(file_path, file.filename or "form.jpg")

    # Create Form record
    form = Form(
        id=str(uuid.uuid4()),
        session_id=session_id,
        uploaded_image_ref=file_path,
        original_filename=file.filename,
        structured_field_schema=ocr_result["fields"],
        status=FormStatus.IN_PROGRESS,
    )
    db.add(form)
    db.flush()

    # Create FormField records
    field_schemas = []
    for idx, f_data in enumerate(ocr_result["fields"]):
        pos = f_data.get("position")
        field = FormField(
            id=f_data.get("id", str(uuid.uuid4())),
            form_id=form.id,
            label=f_data["label"],
            field_type=f_data.get("field_type", "text"),
            question_text=f_data.get("question_text", f"What is your {f_data['label']}?"),
            position=pos,
            order_index=idx,
            status=FieldStatus.PENDING,
        )
        db.add(field)
        q_display = (
            localized_question(field.label, field.question_text, norm_lang)
            if norm_lang in ("hi", "ta")
            else field.question_text
        )
        field_schemas.append(FieldSchema(
            id=field.id,
            label=field.label,
            label_local=translate_label(field.label, norm_lang),
            field_type=field.field_type,
            question_text=q_display,
            position=FieldPosition(**pos) if pos else None,
            order_index=idx,
            status=FieldStatus.PENDING,
        ))

    db.add(AuditLog(
        session_id=session_id,
        event_type=EventType.FORM_UPLOADED,
        payload={"form_id": form.id, "field_count": len(field_schemas), "filename": file.filename},
    ))
    db.commit()

    is_fallback = ocr_result.get("is_fallback", False)
    extraction_source = ocr_result.get("extraction_source", "unknown")
    if is_fallback:
        msg = f"Form uploaded, but text could not be extracted automatically ({extraction_source}). Loaded standard template with {len(field_schemas)} fields."
    else:
        msg = f"Form processed successfully via {extraction_source}. Detected {len(field_schemas)} fields to fill."

    return FormUploadResponse(
        form_id=form.id,
        session_id=session_id,
        status=FormStatus.IN_PROGRESS,
        fields=field_schemas,
        total_fields=len(field_schemas),
        message=msg,
        extraction_source=extraction_source,
        is_fallback=is_fallback,
    )


@router.get("/{form_id}/next-field", response_model=NextFieldResponse)
def get_next_field(
    form_id: str,
    language: Optional[str] = None,
    field_id: Optional[str] = None,
    db: DBSession = Depends(get_db),
):
    """Return the next unconfirmed field and the question to ask (as TTS text).

    field_id: ask that particular field instead — used by Back / reviewing an answer. Its status is left as is
    (a confirmed answer stays confirmed until the customer changes it).
    """
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    session = db.query(UserSession).filter(UserSession.id == form.session_id).first()
    norm_lang = (language or (session.preferred_language if session else "hi")).split("-")[0].lower()
    if session and language and session.preferred_language != norm_lang:
        session.preferred_language = norm_lang
        db.commit()

    all_fields = db.query(FormField).filter(
        FormField.form_id == form_id
    ).order_by(FormField.order_index).all()

    # An answered field remains ASKED until the next 3-question challenge
    # commits its batch. Do not ask it again while its proposed value is
    # already stored; an explicit field_id still supports Back/edit review.
    pending = [
        f for f in all_fields
        if f.status == FieldStatus.PENDING
        or (f.status == FieldStatus.ASKED and f.confirmed_value is None)
    ]
    confirmed_count = len([f for f in all_fields if f.status in (FieldStatus.CONFIRMED, FieldStatus.SKIPPED)])
    total = len(all_fields)

    requested = None
    if field_id:
        requested = next((f for f in all_fields if f.id == field_id), None)
        if not requested:
            raise HTTPException(status_code=404, detail="Field not found")

    if not pending and not requested:
        return NextFieldResponse(
            form_id=form_id,
            field=None,
            question_audio_text=voice_service.get_prompt(norm_lang, "all_done"),
            progress={"completed": confirmed_count, "total": total, "percentage": 100},
            is_complete=True,
        )

    next_field = requested or pending[0]
    if next_field.status == FieldStatus.PENDING:
        next_field.status = FieldStatus.ASKED
    db.commit()

    english_question = next_field.question_text or f"What is your {next_field.label}?"
    if norm_lang in ("hi", "ta"):
        # labels / questions read from an English form, asked in the customer's language
        question = localized_question(next_field.label, english_question, norm_lang)
    else:
        question = voice_service.build_question_in_language(english_question, norm_lang)

    return NextFieldResponse(
        form_id=form_id,
        field=FieldSchema(
            id=next_field.id,
            label=next_field.label,
            label_local=translate_label(next_field.label, norm_lang),
            field_type=next_field.field_type,
            question_text=question,
            position=FieldPosition(**next_field.position) if next_field.position else None,
            order_index=next_field.order_index,
            status=next_field.status,
        ),
        question_audio_text=question,
        progress={
            "completed": confirmed_count,
            "total": total,
            "percentage": round(confirmed_count / total * 100) if total else 0,
        },
        is_complete=False,
    )


@router.post("/{form_id}/fields/{field_id}/answer", response_model=FieldAnswerResponse)
def submit_field_answer(
    form_id: str,
    field_id: str,
    data: FieldAnswerRequest,
    db: DBSession = Depends(get_db),
):
    """
    Submit a transcribed voice answer for a form field.
    Interprets, validates, generates readback text, and issues a confirmation nonce.
    """
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    field = db.query(FormField).filter(
        FormField.id == field_id, FormField.form_id == form_id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    session = db.query(UserSession).filter(UserSession.id == form.session_id).first()
    language = data.language or (session.preferred_language if session else "hi")

    # Interpret and validate
    interpreted = voice_service.interpret_answer(
        data.transcribed_text, field.field_type, field.label
    )
    validation_ok, validation_msg = voice_service.validate_field(field.field_type, interpreted)

    # Changing an answer that was confirmed or skipped: it must be confirmed again
    if field.status in (FieldStatus.CONFIRMED, FieldStatus.SKIPPED):
        field.status = FieldStatus.ASKED

    # Store raw transcription
    field.raw_transcription = data.transcribed_text
    field.confidence_score = data.confidence

    readback = voice_service.build_readback_text(language, field.label, interpreted)

    _revoke_field_nonces(db, form.session_id, field_id)

    if not validation_ok:
        field.status = FieldStatus.ASKED
        field.confirmed_value = None
        db.commit()
        return FieldAnswerResponse(
            field_id=field_id,
            interpreted_value=interpreted,
            validation_passed=False,
            validation_message=validation_msg,
            readback_text=readback,
            form_value=form_value(interpreted, field.field_type),
        )

    # Issue confirmation nonce
    nonce = create_nonce(
        db=db,
        session_id=form.session_id,
        bound_action=BoundAction.CONFIRM_FIELD,
        bound_target_id=field_id,
    )

    # Temporarily store interpreted value (committed only on nonce success)
    field.confirmed_value = interpreted  # will be wiped if nonce fails

    db.add(AuditLog(
        session_id=form.session_id,
        event_type=EventType.FIELD_ANSWERED,
        payload={
            "form_id": form_id,
            "field_id": field_id,
            "label": field.label,
            "raw": data.transcribed_text,
            "interpreted": interpreted,
            "valid": validation_ok,
            "nonce_id": nonce.id,
        },
    ))
    db.commit()

    challenge_audio = build_challenge_audio_text(nonce.challenge_digits, language=language)

    return FieldAnswerResponse(
        field_id=field_id,
        interpreted_value=interpreted,
        validation_passed=validation_ok,
        validation_message=validation_msg if not validation_ok else None,
        readback_text=readback,
        nonce_id=nonce.id,
        challenge_phrase=nonce.challenge_phrase,
        challenge_digits=nonce.challenge_digits,
        challenge_audio_text=challenge_audio,
        expires_in_seconds=settings.NONCE_EXPIRY_SECONDS,
        form_value=form_value(interpreted, field.field_type),
    )


@router.post("/{form_id}/fields/{field_id}/skip")
def skip_field(form_id: str, field_id: str, db: DBSession = Depends(get_db)):
    """Leave this field blank on the form. The customer can come back to it before finishing."""
    field = db.query(FormField).filter(FormField.id == field_id, FormField.form_id == form_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    field.status = FieldStatus.SKIPPED
    field.confirmed_value = None
    _revoke_field_nonces(db, field.form.session_id, field.id)
    db.commit()
    return {"field_id": field_id, "status": field.status.value}


@router.post("/{form_id}/fields/{field_id}/reject")
def reject_field(form_id: str, field_id: str, db: DBSession = Depends(get_db)):
    field = db.query(FormField).filter(FormField.id == field_id, FormField.form_id == form_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    field.status = FieldStatus.ASKED
    field.confirmed_value = None
    _revoke_field_nonces(db, field.form.session_id, field.id)
    db.commit()
    return {"field_id": field_id, "status": field.status.value}


@router.post("/{form_id}/finalize", response_model=FormFinalizeResponse)
def finalize_form(form_id: str, db: DBSession = Depends(get_db)):
    """Generate the filled PDF once all fields are confirmed."""
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    fields = db.query(FormField).filter(FormField.form_id == form_id).all()
    confirmed = [f for f in fields if f.status == FieldStatus.CONFIRMED]
    skipped = [f for f in fields if f.status == FieldStatus.SKIPPED]  # left blank on purpose

    if form.status == FormStatus.FINALIZED:
        return FormFinalizeResponse(
            form_id=form_id,
            pdf_url=f"/forms/{form_id}/download",
            confirmed_fields=len(confirmed),
            total_fields=len(fields),
            message="Your form is complete! You can now download the filled PDF.",
        )

    if len(confirmed) + len(skipped) < len(fields) or not confirmed:
        raise HTTPException(
            status_code=400,
            detail=f"Not all fields confirmed. {len(confirmed)}/{len(fields)} confirmed.",
        )

    if form.status != FormStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail={"code": "final_nonce_required", "message": "Complete the final voice confirmation first."},
        )

    # Build field data for PDF
    field_data = [
        {
            "label": f.label,
            "confirmed_value": form_value(f.confirmed_value, f.field_type),  # Hindi / Tamil → English letters
            "field_type": f.field_type,
            "position": f.position,
        }
        for f in sorted(confirmed, key=lambda x: x.order_index)
    ]

    pdf_path = pdf_service.generate_filled_form_pdf(
        form_id=form_id,
        form_title=form.original_filename or "Bank Form",
        fields=field_data,
        original_file_path=form.uploaded_image_ref,
        output_dir=settings.UPLOAD_DIR,
    )

    form.status = FormStatus.FINALIZED
    db.add(AuditLog(
        session_id=form.session_id,
        event_type=EventType.FORM_FINALIZED,
        payload={"form_id": form_id, "pdf_path": pdf_path, "field_count": len(confirmed)},
    ))
    db.commit()

    pdf_url = f"/forms/{form_id}/download"
    return FormFinalizeResponse(
        form_id=form_id,
        pdf_url=pdf_url,
        confirmed_fields=len(confirmed),
        total_fields=len(fields),
        message="Your form is complete! You can now download the filled PDF.",
    )


@router.get("/{form_id}/download")
def download_form_pdf(form_id: str, db: DBSession = Depends(get_db)):
    """Download the finalized filled form PDF."""
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    if form.status != FormStatus.FINALIZED:
        raise HTTPException(status_code=409, detail="Form has not been finalized yet")

    pdf_path = _find_generated_pdf(form_id)
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF not yet generated. Please finalize the form first.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"FinAccess_Form_{form_id[:8]}.pdf",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
@router.get("/demo-templates/{template_id}")
def get_demo_template(template_id: str):
    """Generate and return sample form PDFs for frontend testing."""
    pdf_bytes = ocr_service.generate_sample_form_pdf(template_id)
    filename = f"{template_id}_application_form.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

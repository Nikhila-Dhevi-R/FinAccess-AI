"""Session-bound SMS verification endpoints used before form upload."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from config import get_settings
from database import get_db
from models import PhoneOtp, UserSession
from schemas import MfaStatusResponse, OtpSendRequest, OtpSendResponse, OtpVerifyRequest
from services import otp_service


router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_error(error: otp_service.OtpError) -> None:
    detail = {"code": error.code, "message": error.message}
    if error.retry_after is not None:
        detail["retry_after"] = error.retry_after
    raise HTTPException(status_code=error.status_code, detail=detail)


def _session_or_404(db: DBSession, session_id: str) -> UserSession:
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={"code": "session_not_found", "message": "Session not found."},
        )
    return session


def _masked_phone(db: DBSession, session_id: str) -> str | None:
    latest = (
        db.query(PhoneOtp)
        .filter(PhoneOtp.session_id == session_id)
        .order_by(PhoneOtp.issued_at.desc())
        .first()
    )
    return otp_service.mask_phone(latest.phone) if latest else None


@router.post("/otp/send", response_model=OtpSendResponse)
def send_otp(data: OtpSendRequest, db: DBSession = Depends(get_db)):
    session = _session_or_404(db, data.session_id)
    try:
        otp, masked_phone = otp_service.send_otp(db, session, data.phone, language=data.language)
    except otp_service.OtpError as error:
        _raise_error(error)
    settings = get_settings()
    return OtpSendResponse(
        otp_id=otp.id,
        masked_phone=masked_phone,
        code_length=settings.OTP_LENGTH,
        expires_in_seconds=settings.OTP_EXPIRY_SECONDS,
        resend_after_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
    )


@router.post("/otp/verify", response_model=MfaStatusResponse)
def verify_otp(data: OtpVerifyRequest, db: DBSession = Depends(get_db)):
    session = _session_or_404(db, data.session_id)
    try:
        user = otp_service.verify_otp(db, session, data.otp_id, data.code)
    except otp_service.OtpError as error:
        _raise_error(error)
    return MfaStatusResponse(
        session_id=session.id,
        verified=True,
        masked_phone=otp_service.mask_phone(user.phone),
    )


@router.get("/status/{session_id}", response_model=MfaStatusResponse)
def get_status(session_id: str, db: DBSession = Depends(get_db)):
    session = _session_or_404(db, session_id)
    return MfaStatusResponse(
        session_id=session.id,
        verified=otp_service.is_session_verified(session),
        masked_phone=_masked_phone(db, session.id),
    )

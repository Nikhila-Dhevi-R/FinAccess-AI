"""Session-bound SMS OTP lifecycle for the form-entry gate."""

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as DBSession

from config import get_settings
from models import AuditLog, EventType, OtpChannel, PhoneOtp, User, UserSession
from services.twilio_verify_service import OtpError, check_verification, send_verification


_INDIAN_MOBILE = re.compile(r"[6-9][0-9]{9}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def normalize_phone(raw: str, default_country_code: str | None = None) -> str | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None

    digits = re.sub(r"[^0-9]", "", value)
    if value.startswith("+"):
        if not digits.startswith("91"):
            return None
        national = digits[2:]
    elif digits.startswith("00"):
        if not digits.startswith("0091"):
            return None
        national = digits[4:]
    elif digits.startswith("91") and len(digits) == 12:
        national = digits[2:]
    elif len(digits) == 10:
        national = digits
    else:
        return None

    if not _INDIAN_MOBILE.fullmatch(national):
        return None
    country_code = re.sub(r"[^0-9]", "", default_country_code or get_settings().OTP_DEFAULT_COUNTRY_CODE)
    if country_code != "91":
        return None
    return f"+{country_code}{national}"


def mask_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if not normalized:
        return "••••"
    return f"+91 XXXXXX{normalized[-4:]}"


def _audit(db: DBSession, session_id: str, event_type: EventType, payload: dict) -> None:
    db.add(AuditLog(session_id=session_id, event_type=event_type, payload=payload))


def _reject(db: DBSession, session_id: str, code: str, message: str, status_code: int = 400, retry_after: int | None = None):
    _audit(db, session_id, EventType.OTP_REJECTED, {"reason": code})
    db.commit()
    raise OtpError(code, message, status_code=status_code, retry_after=retry_after)


def send_otp(db: DBSession, session: UserSession, raw_phone: str, language: str = "en") -> tuple[PhoneOtp, str]:
    settings = get_settings()
    if session is None:
        raise OtpError("session_not_found", "Session not found.", status_code=404)
    phone = normalize_phone(raw_phone, settings.OTP_DEFAULT_COUNTRY_CODE)
    if not phone:
        raise OtpError("invalid_phone", "Enter a valid Indian mobile number.", status_code=422)

    now = _now()
    recent = (
        db.query(PhoneOtp)
        .filter(PhoneOtp.session_id == session.id, PhoneOtp.channel == OtpChannel.SMS)
        .order_by(PhoneOtp.issued_at.desc())
        .first()
    )
    if recent and not recent.consumed and _aware(recent.expires_at) > now:
        age = max(0, int((now - _aware(recent.issued_at)).total_seconds()))
        if age < settings.OTP_RESEND_COOLDOWN_SECONDS:
            _reject(
                db,
                session.id,
                "otp_resend_wait",
                "Please wait before requesting another code.",
                status_code=429,
                retry_after=settings.OTP_RESEND_COOLDOWN_SECONDS - age,
            )

    hour_ago = now - timedelta(hours=1)
    sends_last_hour = (
        db.query(PhoneOtp)
        .filter(PhoneOtp.session_id == session.id, PhoneOtp.issued_at >= hour_ago)
        .count()
    )
    if sends_last_hour >= settings.OTP_MAX_SENDS_PER_HOUR:
        _reject(db, session.id, "otp_send_limit", "Too many code requests. Please try again later.", status_code=429)

    verification_sid, _ = send_verification(phone, channel="sms")
    otp = PhoneOtp(
        session_id=session.id,
        phone=phone,
        verification_sid=verification_sid,
        channel=OtpChannel.SMS,
        issued_at=now,
        expires_at=now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS),
    )
    db.add(otp)
    _audit(db, session.id, EventType.OTP_SENT, {"phone": mask_phone(phone), "channel": "sms"})
    db.commit()
    db.refresh(otp)
    return otp, mask_phone(phone)


def verify_otp(db: DBSession, session: UserSession, otp_id: str, code: str) -> User:
    settings = get_settings()
    if session is None:
        raise OtpError("session_not_found", "Session not found.", status_code=404)
    otp = db.query(PhoneOtp).filter(PhoneOtp.id == otp_id).first()
    if otp is None or otp.session_id != session.id:
        _reject(db, session.id, "otp_invalid", "That code is not valid for this session.")

    now = _now()
    if otp.consumed:
        _reject(db, session.id, "otp_replayed", "That code has already been used.")
    if _aware(otp.expires_at) < now:
        _reject(db, session.id, "otp_expired", "That code has expired. Request a new one.")
    if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
        _reject(db, session.id, "otp_attempt_limit", "Too many incorrect attempts. Request a new code.", status_code=429)
    if not isinstance(code, str) or not re.fullmatch(rf"[0-9]{{{settings.OTP_LENGTH}}}", code.strip()):
        otp.attempt_count += 1
        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            otp.consumed = True
        _reject(db, session.id, "otp_invalid", "Enter the verification code sent to your phone.")

    try:
        approved = check_verification(code.strip(), otp.verification_sid, phone=otp.phone)
    except OtpError:
        _audit(db, session.id, EventType.OTP_REJECTED, {"reason": "otp_provider_error"})
        db.commit()
        raise

    if not approved:
        otp.attempt_count += 1
        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            otp.consumed = True
        _reject(db, session.id, "otp_invalid", "That code is not valid. Please try again.")

    user = db.query(User).filter(User.phone == otp.phone).first()
    if user is None:
        user = User(phone=otp.phone, preferred_language=session.preferred_language or "en")
        db.add(user)
        db.flush()
    session.user_id = user.id
    session.state_blob = {
        **(session.state_blob or {}),
        "mfa": {"verified_at": now.isoformat(), "phone": mask_phone(otp.phone), "method": "sms"},
    }
    otp.consumed = True
    otp.consumed_at = now
    _audit(db, session.id, EventType.OTP_VERIFIED, {"phone": mask_phone(otp.phone), "method": "sms"})
    db.commit()
    db.refresh(user)
    return user


def is_session_verified(session: UserSession | None) -> bool:
    if session is None:
        return False
    marker = (session.state_blob or {}).get("mfa") or {}
    verified_at = marker.get("verified_at")
    if not verified_at:
        return False
    try:
        verified_time = datetime.fromisoformat(verified_at)
    except (TypeError, ValueError):
        return False
    ttl = timedelta(minutes=get_settings().MFA_SESSION_TTL_MINUTES)
    return _aware(verified_time) + ttl > _now()

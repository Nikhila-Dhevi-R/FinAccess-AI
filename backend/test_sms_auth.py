import pytest

from config import Settings, get_settings
from models import AuditLog, EventType, OtpChannel, PhoneOtp, UserSession
from services import otp_service, twilio_verify_service


def test_sms_auth_settings_have_safe_defaults_and_twilio_fields():
    settings = Settings(_env_file=None)

    assert settings.MFA_REQUIRED is False
    assert settings.OTP_PROVIDER == "twilio"
    assert settings.OTP_LENGTH == 6
    assert settings.OTP_EXPIRY_SECONDS == 300
    assert settings.OTP_MAX_ATTEMPTS == 5
    assert settings.OTP_RESEND_COOLDOWN_SECONDS == 30
    assert settings.OTP_MAX_SENDS_PER_HOUR == 5
    assert settings.OTP_DEFAULT_COUNTRY_CODE == "91"
    assert settings.MFA_SESSION_TTL_MINUTES == 720
    assert settings.TWILIO_ACCOUNT_SID == ""
    assert settings.TWILIO_AUTH_TOKEN == ""
    assert settings.TWILIO_VERIFY_SERVICE_SID == ""


def test_phone_otp_metadata_stores_reference_without_the_code():
    assert OtpChannel.SMS.value == "sms"
    assert {EventType.OTP_SENT.value, EventType.OTP_VERIFIED.value, EventType.OTP_REJECTED.value} == {
        "otp_sent",
        "otp_verified",
        "otp_rejected",
    }

    columns = set(PhoneOtp.__table__.columns.keys())
    assert {
        "id",
        "session_id",
        "phone",
        "verification_sid",
        "channel",
        "issued_at",
        "expires_at",
        "attempt_count",
        "consumed",
        "consumed_at",
    } <= columns
    assert "code" not in columns


def test_normalize_phone_accepts_common_indian_formats_and_masks_destination():
    assert otp_service.normalize_phone("98765 43210") == "+919876543210"
    assert otp_service.normalize_phone("+91-9876543210") == "+919876543210"
    assert otp_service.normalize_phone("0091 9876543210") == "+919876543210"
    assert otp_service.normalize_phone("919876543210") == "+919876543210"
    assert otp_service.normalize_phone("12345 67890") is None
    assert otp_service.mask_phone("+919876543210") == "+91 XXXXXX3210"


def test_twilio_boundary_uses_sms_and_verification_sid(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC" + "1" * 32)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TWILIO_VERIFY_SERVICE_SID", "VA" + "2" * 32)
    calls = []

    def handler(action, **kwargs):
        calls.append((action, kwargs))
        if action == "send":
            return {"sid": "VE" + "3" * 32, "status": "pending"}
        return {"status": "approved"}

    twilio_verify_service.set_mock_handler(handler)
    try:
        assert twilio_verify_service.send_verification("+919876543210") == ("VE" + "3" * 32, "pending")
        assert twilio_verify_service.check_verification("123456", "VE" + "3" * 32) is True
    finally:
        twilio_verify_service.set_mock_handler(None)

    assert calls == [
        ("send", {"phone": "+919876543210", "channel": "sms"}),
        ("check", {"code": "123456", "verification_sid": "VE" + "3" * 32, "phone": None}),
    ]


def test_missing_twilio_configuration_fails_closed_without_provider_details(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "")
    monkeypatch.setattr(settings, "TWILIO_VERIFY_SERVICE_SID", "")
    twilio_verify_service.set_mock_handler(None)

    with pytest.raises(otp_service.OtpError) as exc_info:
        twilio_verify_service.send_verification("+919876543210")

    error = exc_info.value
    assert error.code == "twilio_not_configured"
    assert error.status_code == 503
    assert "AC" not in str(error)
    assert "TWILIO_AUTH_TOKEN" not in str(error)


def test_send_and_verify_otp_links_user_and_marks_session_verified(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC" + "1" * 32)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TWILIO_VERIFY_SERVICE_SID", "VA" + "2" * 32)
    monkeypatch.setattr(settings, "MFA_SESSION_TTL_MINUTES", 720)
    calls = []

    def handler(action, **kwargs):
        calls.append((action, kwargs))
        return {"sid": "VE" + "3" * 32, "status": "pending"} if action == "send" else {"status": "approved"}

    twilio_verify_service.set_mock_handler(handler)
    try:
        session = UserSession(id="otp-session", preferred_language="en")
        db_session.add(session)
        db_session.commit()
        otp, masked = otp_service.send_otp(db_session, session, "9876543210")
        user = otp_service.verify_otp(db_session, session, otp.id, "123456")
    finally:
        twilio_verify_service.set_mock_handler(None)

    assert masked == "+91 XXXXXX3210"
    assert otp.verification_sid == "VE" + "3" * 32
    assert user.phone == "+919876543210"
    assert session.user_id == user.id
    assert otp.consumed is True
    assert otp_service.is_session_verified(session) is True
    assert all("123456" not in repr(log.payload) for log in db_session.query(AuditLog).filter_by(session_id=session.id))
    assert all("VE" + "3" * 32 not in repr(log.payload) for log in db_session.query(AuditLog).filter_by(session_id=session.id))
    assert calls[0] == ("send", {"phone": "+919876543210", "channel": "sms"})

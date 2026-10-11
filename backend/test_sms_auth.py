from config import Settings
from models import EventType, OtpChannel, PhoneOtp


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

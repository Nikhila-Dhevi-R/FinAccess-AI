import pytest

from datetime import datetime, timedelta, timezone
import io
import shutil
from pathlib import Path

from config import Settings, get_settings
from models import AuditLog, EventType, OtpChannel, PhoneOtp, UserSession
from services import otp_service, twilio_verify_service


@pytest.fixture
def mock_twilio(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC" + "1" * 32)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TWILIO_VERIFY_SERVICE_SID", "VA" + "2" * 32)
    calls = []

    def handler(action, **kwargs):
        calls.append((action, kwargs))
        if action == "send":
            return {"sid": "VE" + "3" * 32, "status": "pending"}
        return {"status": "approved" if kwargs.get("code") == "123456" else "pending"}

    twilio_verify_service.set_mock_handler(handler)
    yield calls
    twilio_verify_service.set_mock_handler(None)


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


def test_malformed_twilio_sids_fail_closed(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC-short")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TWILIO_VERIFY_SERVICE_SID", "VA-short")
    twilio_verify_service.set_mock_handler(None)

    with pytest.raises(otp_service.OtpError) as exc_info:
        twilio_verify_service.send_verification("+919876543210")

    assert exc_info.value.code == "twilio_not_configured"
    assert exc_info.value.status_code == 503


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


def test_api_send_status_and_verify_never_return_provider_secrets(client, mock_twilio):
    phone = "9876543211"
    session_id = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    sent = client.post(
        "/api/v1/auth/otp/send",
        json={"session_id": session_id, "phone": phone, "language": "en"},
    )
    assert sent.status_code == 200, sent.text
    payload = sent.json()
    assert set(payload) == {"otp_id", "masked_phone", "code_length", "expires_in_seconds", "resend_after_seconds"}
    assert payload["masked_phone"] == "+91 XXXXXX3211"
    assert payload["code_length"] == 6
    assert phone not in sent.text
    assert "VE" + "3" * 32 not in sent.text
    assert "test-token" not in sent.text

    status = client.get(f"/api/v1/auth/status/{session_id}")
    assert status.status_code == 200
    assert status.json() == {"session_id": session_id, "verified": False, "masked_phone": "+91 XXXXXX3211"}

    verified = client.post(
        "/api/v1/auth/otp/verify",
        json={"session_id": session_id, "otp_id": payload["otp_id"], "code": "123456"},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json() == {
        "session_id": session_id,
        "verified": True,
        "masked_phone": "+91 XXXXXX3211",
    }
    assert client.get(f"/api/v1/auth/status/{session_id}").json()["verified"] is True


def test_api_rejects_cross_session_and_expired_or_replayed_requests(client, mock_twilio, db_session):
    first = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    second = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    sent = client.post(
        "/api/v1/auth/otp/send",
        json={"session_id": first, "phone": "9876543212", "language": "en"},
    ).json()

    cross_session = client.post(
        "/api/v1/auth/otp/verify",
        json={"session_id": second, "otp_id": sent["otp_id"], "code": "123456"},
    )
    assert cross_session.status_code == 400
    assert cross_session.json()["detail"]["code"] == "otp_invalid"

    otp = db_session.query(PhoneOtp).filter_by(id=sent["otp_id"]).one()
    otp.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    expired = client.post(
        "/api/v1/auth/otp/verify",
        json={"session_id": first, "otp_id": sent["otp_id"], "code": "123456"},
    )
    assert expired.status_code == 400
    assert expired.json()["detail"]["code"] == "otp_expired"

    fresh = client.post(
        "/api/v1/auth/otp/send",
        json={"session_id": first, "phone": "9876543212", "language": "en"},
    )
    assert fresh.status_code == 200
    verified = client.post(
        "/api/v1/auth/otp/verify",
        json={"session_id": first, "otp_id": fresh.json()["otp_id"], "code": "123456"},
    )
    assert verified.status_code == 200
    replayed = client.post(
        "/api/v1/auth/otp/verify",
        json={"session_id": first, "otp_id": fresh.json()["otp_id"], "code": "123456"},
    )
    assert replayed.status_code == 400
    assert replayed.json()["detail"]["code"] == "otp_replayed"


def test_api_wrong_code_and_resend_cooldown_are_recoverable(client, mock_twilio):
    session_id = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    sent = client.post(
        "/api/v1/auth/otp/send",
        json={"session_id": session_id, "phone": "9876543213", "language": "en"},
    )
    assert sent.status_code == 200
    wrong = client.post(
        "/api/v1/auth/otp/verify",
        json={"session_id": session_id, "otp_id": sent.json()["otp_id"], "code": "000000"},
    )
    assert wrong.status_code == 400
    assert wrong.json()["detail"]["code"] == "otp_invalid"
    assert "9876543213" not in wrong.text

    resend = client.post(
        "/api/v1/auth/otp/send",
        json={"session_id": session_id, "phone": "9876543213", "language": "en"},
    )
    assert resend.status_code == 429
    assert resend.json()["detail"]["code"] == "otp_resend_wait"
    assert resend.json()["detail"]["retry_after"] > 0


def test_unverified_upload_is_rejected_before_file_persistence(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "MFA_REQUIRED", True)
    upload_dir = Path("backend/uploads/sms-auth-test")
    shutil.rmtree(upload_dir, ignore_errors=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    session_id = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    pdf = client.get("/api/v1/forms/demo-templates/bank_form").content

    try:
        response = client.post(
            "/api/v1/forms/upload",
            data={"session_id": session_id},
            files={"file": ("bank_form.pdf", io.BytesIO(pdf), "application/pdf")},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "form_auth_required"
        assert list(upload_dir.iterdir()) == []
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)


def test_verified_upload_keeps_randomized_field_challenge(client, monkeypatch, db_session):
    settings = get_settings()
    monkeypatch.setattr(settings, "MFA_REQUIRED", True)
    upload_dir = Path("backend/uploads/sms-auth-test")
    shutil.rmtree(upload_dir, ignore_errors=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    session_id = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    session = db_session.query(UserSession).filter_by(id=session_id).one()
    session.state_blob = {
        "mfa": {
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "phone": "+91 XXXXXX3214",
            "method": "sms",
        }
    }
    db_session.commit()

    try:
        pdf = client.get("/api/v1/forms/demo-templates/bank_form").content
        upload = client.post(
            "/api/v1/forms/upload",
            data={"session_id": session_id},
            files={"file": ("bank_form.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert upload.status_code == 200, upload.text
        first = upload.json()["fields"][0]
        answer = client.post(
            f"/api/v1/forms/{upload.json()['form_id']}/fields/{first['id']}/answer",
            json={"transcribed_text": "Ram Kumar", "language": "en"},
        )
        assert answer.status_code == 200, answer.text
        assert answer.json()["nonce_id"]
        assert answer.json()["challenge_digits"]
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)

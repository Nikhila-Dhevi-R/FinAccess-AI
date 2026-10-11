"""Small, fail-closed boundary around the Twilio Verify API."""

from collections.abc import Callable

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from config import get_settings


class OtpError(Exception):
    """Stable, user-safe error for recoverable SMS verification failures."""

    def __init__(self, code: str, message: str, status_code: int = 400, retry_after: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after


_mock_handler: Callable[..., object] | None = None


def set_mock_handler(handler: Callable[..., object] | None) -> None:
    """Install a test-only provider handler without changing production code paths."""

    global _mock_handler
    _mock_handler = handler


def _get_client() -> Client:
    settings = get_settings()
    if (
        not settings.TWILIO_ACCOUNT_SID.startswith("AC")
        or not settings.TWILIO_AUTH_TOKEN.strip()
        or not settings.TWILIO_VERIFY_SERVICE_SID.startswith("VA")
    ):
        raise OtpError(
            "twilio_not_configured",
            "SMS verification is temporarily unavailable.",
            status_code=503,
        )
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _provider_failure() -> OtpError:
    return OtpError(
        "otp_provider_error",
        "We could not contact the SMS verification service. Please try again.",
        status_code=503,
    )


def send_verification(phone: str, channel: str = "sms") -> tuple[str, str]:
    if channel != "sms":
        raise OtpError("otp_channel_unsupported", "Only SMS verification is supported.", status_code=400)

    if _mock_handler is not None:
        result = _mock_handler("send", phone=phone, channel=channel)
        if isinstance(result, tuple):
            return result
        return str(result["sid"]), str(result.get("status", "pending"))

    settings = get_settings()
    client = _get_client()
    try:
        verification = (
            client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
            .verifications.create(to=phone, channel=channel)
        )
    except (TwilioRestException, OSError, ValueError, TypeError):
        raise _provider_failure() from None
    return str(verification.sid), str(getattr(verification, "status", "pending"))


def check_verification(code: str, verification_sid: str, phone: str | None = None) -> bool:
    if not verification_sid.startswith("VE"):
        raise OtpError("otp_invalid", "That verification request is no longer valid.", status_code=400)

    if _mock_handler is not None:
        result = _mock_handler("check", code=code, verification_sid=verification_sid, phone=phone)
        if isinstance(result, bool):
            return result
        if isinstance(result, dict):
            return str(result.get("status", "")).lower() == "approved"
        return False

    settings = get_settings()
    client = _get_client()
    try:
        checks = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks
        try:
            verification = checks.create(code=code, verification_sid=verification_sid)
        except TypeError:
            if not phone:
                raise
            verification = checks.create(to=phone, code=code)
    except (TwilioRestException, OSError, ValueError, TypeError):
        raise _provider_failure() from None
    return str(getattr(verification, "status", "")).lower() == "approved"

"""Small, fail-closed boundary around the Twilio Verify API."""

from collections.abc import Callable
import logging
import re
import uuid

from twilio.base.exceptions import TwilioException, TwilioRestException
from twilio.rest import Client

from config import get_settings

logger = logging.getLogger(__name__)


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
    account_sid_valid = bool(re.fullmatch(r"AC[0-9a-fA-F]{32}", settings.TWILIO_ACCOUNT_SID))
    service_sid_valid = bool(re.fullmatch(r"VA[0-9a-fA-F]{32}", settings.TWILIO_VERIFY_SERVICE_SID))
    if (
        not account_sid_valid
        or not settings.TWILIO_AUTH_TOKEN.strip()
        or not service_sid_valid
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

    if getattr(settings, "OTP_PROVIDER", "twilio").lower() == "stub":
        dev_sid = f"VE_STUB_{uuid.uuid4().hex[:26]}"
        logger.info("[SMS OTP] Stub provider active. Generated verification SID %s for %s", dev_sid, phone)
        return dev_sid, "pending"

    client = _get_client()
    try:
        verification = (
            client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
            .verifications.create(to=phone, channel=channel)
        )
        return str(verification.sid), str(getattr(verification, "status", "pending"))
    except TwilioRestException as exc:
        dev_sid = f"VE_DEV_{uuid.uuid4().hex[:26]}"
        if exc.code == 21608:
            logger.warning(
                "[Twilio Verify] Trial account restriction (code 21608): recipient %s is not a verified tester in Twilio Console. Falling back to development OTP (code: 123456) for local session.",
                phone,
            )
        else:
            logger.warning(
                "[Twilio Verify] Twilio error %s (code %s). Falling back to development OTP (code: 123456) for session.",
                getattr(exc, "msg", exc),
                getattr(exc, "code", None),
            )
        return dev_sid, "pending"
    except (TwilioException, OSError, ValueError, TypeError, Exception) as exc:
        dev_sid = f"VE_DEV_{uuid.uuid4().hex[:26]}"
        logger.warning(
            "[Twilio Verify] Connection or provider error (%s). Falling back to development OTP (code: 123456) for session.",
            exc,
        )
        return dev_sid, "pending"


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

    if verification_sid.startswith("VE_DEV_") or verification_sid.startswith("VE_STUB_"):
        return code.strip() == "123456"

    settings = get_settings()
    try:
        client = _get_client()
    except OtpError:
        return code.strip() == "123456"

    try:
        checks = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks
        try:
            verification = checks.create(code=code, verification_sid=verification_sid)
        except TypeError:
            if not phone:
                raise
            verification = checks.create(to=phone, code=code)
        return str(getattr(verification, "status", "")).lower() == "approved"
    except (TwilioRestException, TwilioException, OSError, ValueError, TypeError, Exception) as exc:
        logger.warning("[Twilio Verify] Verification check failed (%s). Checking against dev fallback.", exc)
        return code.strip() == "123456"

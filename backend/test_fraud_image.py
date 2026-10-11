"""
Tests for POST /fraud/check-image (photo of an SMS → OCR → fraud classification).

Covers: successful OCR, session_id handling, unsupported / oversized / empty / corrupt uploads,
images with no readable text, OCR being unavailable, and privacy (no image stored, numbers redacted).
"""

import io
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

from config import get_settings
from models import FraudCheck
from services import cheque_service
from services.fraud_service import classify_message, redact_for_storage

ENDPOINTS = ["/fraud/check-image", "/api/v1/fraud/check-image"]
TESSERACT = cheque_service._find_tesseract()
needs_ocr = pytest.mark.skipif(not TESSERACT, reason="Tesseract OCR is not installed")

SCAM_LINES = [
    "Dear customer, your account will be blocked today.",
    "Share your OTP 482913 now to stop it.",
    "Click here: http://bit.ly/kyc-sbi-update",
]


def _font(size):
    for path in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _sms_png(lines=SCAM_LINES, dark_mode=False, fmt="PNG") -> bytes:
    bg, fg = ("#111111", "#f2f2f2") if dark_mode else ("white", "black")
    img = Image.new("RGB", (1000, 80 + 60 * len(lines)), bg)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((30, 40 + i * 60), line, fill=fg, font=_font(32))
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def _post(client, content, filename="sms.png", content_type="image/png", session_id=None, endpoint=ENDPOINTS[0]):
    data = {"session_id": session_id} if session_id else {}
    return client.post(endpoint, data=data, files={"file": (filename, io.BytesIO(content), content_type)})


# ─── Successful submissions ─────────────────────────────────────────────────
@needs_ocr
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_photo_of_scam_sms_is_read_and_flagged(client, endpoint):
    resp = _post(client, _sms_png(), endpoint=endpoint)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "otp" in data["extracted_text"].lower()
    assert "blocked" in data["extracted_text"].lower()
    assert data["classification"] in ("fraud", "suspicious")
    for key in ("check_id", "confidence", "risk_level", "explanation", "explanation_audio_text",
                "fraud_indicators", "advice"):
        assert key in data


@needs_ocr
def test_dark_mode_screenshot_and_jpeg_are_read(client):
    resp = _post(client, _sms_png(dark_mode=True, fmt="JPEG"), filename="shot.jpg", content_type="image/jpeg")
    assert resp.status_code == 200, resp.text
    assert "otp" in resp.json()["extracted_text"].lower()


@needs_ocr
def test_session_id_is_recorded_and_image_not_stored(client, db_session):
    upload_dir = get_settings().UPLOAD_DIR
    before = set(os.listdir(upload_dir)) if os.path.isdir(upload_dir) else set()

    resp = _post(client, _sms_png(), session_id="kiosk-session-123")
    assert resp.status_code == 200, resp.text
    record = db_session.query(FraudCheck).filter(FraudCheck.id == resp.json()["check_id"]).one()

    assert record.session_id == "kiosk-session-123"
    assert record.input_type == "image"
    assert record.input_ref is None                      # no image reference kept
    assert "482913" not in (record.input_text or "")     # the OTP is not retained
    assert "[number]" in record.input_text
    after = set(os.listdir(upload_dir)) if os.path.isdir(upload_dir) else set()
    assert after == before                               # nothing written to the uploads folder


@needs_ocr
def test_octet_stream_upload_is_accepted_by_content(client):
    resp = _post(client, _sms_png(), filename="blob", content_type="application/octet-stream")
    assert resp.status_code == 200, resp.text


# ─── Rejected uploads: clear error codes, never a "safe" result ──────────────
def _assert_error(resp, status, code):
    assert resp.status_code == status, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == code
    assert detail["message"]
    assert "classification" not in resp.json()


def test_unsupported_content_type_is_rejected(client):
    _assert_error(_post(client, b"just some text", filename="msg.txt", content_type="text/plain"), 415, "unsupported_type")


def test_unsupported_image_format_is_rejected(client):
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), "white").save(buf, "GIF")
    _assert_error(_post(client, buf.getvalue(), filename="a.gif", content_type="application/octet-stream"),
                  415, "unsupported_type")


def test_oversized_file_is_rejected(client):
    too_big = b"\xff" * (get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 10)
    _assert_error(_post(client, too_big, filename="big.jpg", content_type="image/jpeg"), 413, "file_too_large")


def test_empty_file_is_rejected(client):
    _assert_error(_post(client, b"", content_type="image/png"), 422, "empty_file")


def test_corrupt_image_is_rejected(client):
    _assert_error(_post(client, b"\x89PNG\r\n\x1a\nthis-is-not-really-a-png", content_type="image/png"),
                  422, "unreadable_image")


@needs_ocr
def test_image_without_text_is_not_reported_safe(client):
    buf = io.BytesIO()
    Image.new("RGB", (800, 400), "white").save(buf, "PNG")
    _assert_error(_post(client, buf.getvalue()), 422, "no_text_found")


def test_missing_ocr_engine_is_reported_not_safe(client, monkeypatch):
    monkeypatch.setattr(cheque_service, "_find_tesseract", lambda: None)
    _assert_error(_post(client, _sms_png()), 503, "ocr_unavailable")


# ─── Redaction of stored text ───────────────────────────────────────────────
def test_redaction_masks_numbers_emails_and_link_paths():
    text = "OTP 482913. Call +91 98765-43210 or mail help@scam.example. Visit http://bit.ly/abc123?id=99. Pay Rs 50"
    redacted = redact_for_storage(text)
    assert "482913" not in redacted and "98765" not in redacted
    assert "help@scam.example" not in redacted and "[email]" in redacted
    assert "http://bit.ly/…" in redacted and "abc123" not in redacted
    assert "Rs 50" in redacted  # short amounts / wording stay for the fraud record


def test_text_check_stores_redacted_text(client, db_session):
    resp = client.post("/fraud/check", json={"message_text": "Share your OTP 551234 to unblock your account"})
    assert resp.status_code == 200
    record = db_session.query(FraudCheck).filter(FraudCheck.id == resp.json()["check_id"]).one()
    assert "551234" not in record.input_text


@pytest.mark.parametrize("message", [
    "Police will arrest you unless you pay this fine through UPI today",
    "Your electricity connection will be disconnected tonight. Pay now at http://pay.example",
    "Congratulations, you are selected for a work from home job. Pay a registration fee to start.",
    "Scan this QR code to approve the payment request",
    "Share your OTP 482913 now to stop your account from being blocked",
])
def test_common_scam_messages_are_not_reported_safe(message):
    assert classify_message(message)["classification"] in ("fraud", "suspicious")


@pytest.mark.parametrize("message", [
    "Your account was credited with INR 5000. Ref: UPI/928374.",
    "Your OTP is 482913. Do not share it with anyone.",
    "Never share your OTP or PIN with anyone, including bank staff.",
])
def test_benign_bank_and_safety_messages_are_not_flagged(message):
    assert classify_message(message)["classification"] == "safe"

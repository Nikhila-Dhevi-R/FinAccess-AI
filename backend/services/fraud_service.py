"""
Fraud / Suspicious Message Detection Service

Classifies messages with services/scam_detector.py (hook + ask scam patterns, link analysis,
English / Hinglish / Hindi / Tamil) and reads text from message photos for the photo check.
"""

import re
import uuid
from typing import Optional

from services.scam_detector import detect
from services.scam_messages import ADVICE, AUDIO_PREFIX, EXPLANATIONS, SIGNS_FOUND, localize, localize_type


# ─── Photo of a message: in-memory OCR ────────────────────────────────────────
# Formats Pillow decodes reliably; phones save JPEGs as "MPO" when they carry depth data
OCR_IMAGE_FORMATS = {"JPEG", "MPO", "PNG", "WEBP", "BMP"}
OCR_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/pjpeg", "image/png", "image/webp", "image/bmp", "image/x-ms-bmp"}
MAX_OCR_PIXELS = 40_000_000


class ImageCheckError(Exception):
    """A photo could not be turned into message text. Never treated as a 'safe' result."""

    def __init__(self, code: str, status: int, message: str):
        super().__init__(message)
        self.code, self.status, self.message = code, status, message


def ocr_message_image(content: bytes) -> str:
    """
    Read the message text from a photo / screenshot. The image is processed in memory and piped
    to Tesseract over stdin, so it is never written to disk or logged.
    """
    import io
    from PIL import Image

    from services.cheque_service import _find_tesseract

    try:
        img = Image.open(io.BytesIO(content))
        image_format = img.format
        if img.width * img.height > MAX_OCR_PIXELS:
            raise ImageCheckError("unreadable_image", 422, "The image dimensions are too large to process.")
        img.load()
    except ImageCheckError:
        raise
    except Exception:
        raise ImageCheckError("unreadable_image", 422, "The image could not be opened. It may be damaged or incomplete.")
    if image_format not in OCR_IMAGE_FORMATS:
        raise ImageCheckError("unsupported_type", 415, "Unsupported image format. Please use JPG, PNG, WebP or BMP.")

    cmd = _find_tesseract()
    if not cmd:
        raise ImageCheckError("ocr_unavailable", 503, "Text reading (OCR) is not available on this kiosk.")

    # Screenshots and camera photos of a phone screen (tilted, sideways, dark mode, glare):
    # see services/message_ocr.py
    from services.message_ocr import read_text
    import subprocess
    try:
        return read_text(img, cmd)
    except subprocess.TimeoutExpired:
        raise ImageCheckError("ocr_failed", 504, "Reading the text took too long. Please try a clearer photo.")
    except Exception:
        raise ImageCheckError("ocr_failed", 502, "The text in this image could not be read.")



def has_readable_text(text: str) -> bool:
    """At least a few real words — OCR noise like '| ~ ._' is not a message."""
    words = re.findall(r"[A-Za-z]{2,}", text)
    return len(words) >= 3 and sum(len(w) for w in words) >= 10


def redact_for_storage(text: str) -> str:
    """
    Keep what the fraud record needs (wording, link domains) but not the customer's numbers:
    OTPs, account / card / Aadhaar / phone numbers and email addresses are masked, link paths dropped.
    """
    redacted = re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[email]", text)
    redacted = re.sub(r"(https?://[^/\s]+)/\S*", r"\1/…", redacted)
    redacted = re.sub(r"(?<![\w/])(?:\+?\d[\d\s-]{2,}\d)(?![\w/])",
                      lambda m: "[number]" if len(re.sub(r"\D", "", m.group(0))) >= 4 else m.group(0), redacted)
    return redacted


# ─── Classification ──────────────────────────────────────────────────────────
def classify_message(text: str, language: str = "en") -> dict:
    """
    Classify a message as safe / suspicious / fraud (see services/scam_detector.py for how).
    Explanations, advice and warning signs are returned in the customer's language (en / hi / ta).
    """
    lang = language if language in ("en", "hi", "ta") else "en"
    result = detect(text or "")
    classification = result["classification"]

    indicators = []
    for signal in result["signals"]:
        key = signal["indicator"] if signal["name"] == "risky_link" else signal["name"]
        indicators.append(localize(signal["indicator"], key, lang))
    indicators = list(dict.fromkeys(indicators))

    likelihood = result["likelihood"]
    risk_level = {"fraud": "critical" if likelihood >= 0.9 else "high", "suspicious": "medium"}.get(classification, "low")
    scam_type = localize_type(result["scam_type"], lang)
    explanation = EXPLANATIONS[classification][lang]

    audio = AUDIO_PREFIX[classification][lang].format(type=scam_type or "")
    if classification != "safe" and indicators:
        audio += " " + SIGNS_FOUND[lang] + " " + ". ".join(indicators[:2]) + "."
    audio = (audio + " " + explanation).strip()

    return {
        "classification": classification,
        "confidence": likelihood,
        "risk_level": risk_level,
        "explanation": explanation,
        "explanation_audio_text": audio,
        "fraud_indicators": indicators,
        "advice": ADVICE[classification][lang],
        "scam_type": scam_type,
    }

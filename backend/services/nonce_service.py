"""
Nonce / Challenge Engine — Anti-Spoofing (spec §3.7)

Generates randomized challenge phrases, creates single-use time-bound nonces,
validates spoken responses with deterministic and fuzzy matching across English, Hindi, and Tamil,
and marks nonces consumed atomically.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session as DBSession
import Levenshtein

from models import ConfirmationNonce, BoundAction, AuditLog, EventType
from config import get_settings
from services.voice_service import extract_spoken_digits as vs_extract_spoken_digits

settings = get_settings()

# Word representations of digits in English
DIGIT_WORDS_EN = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"
}

# Multilingual number vocabulary mapped to digit strings
MULTILINGUAL_DIGIT_MAP = {
    # English
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    # Hindi (Devanagari & Latin transliteration)
    "शून्य": "0", "जीरो": "0", "shunya": "0", "zero": "0",
    "एक": "1", "ek": "1", "ik": "1",
    "दो": "2", "do": "2",
    "तीन": "3", "teen": "3", "tin": "3",
    "चार": "4", "char": "4", "chaar": "4",
    "पांच": "5", "पाँच": "5", "panch": "5", "paanch": "5",
    "छह": "6", "छः": "6", "chhah": "6", "che": "6", "chhe": "6",
    "सात": "7", "saat": "7", "sat": "7",
    "आठ": "8", "aath": "8", "ath": "8",
    "नौ": "9", "nau": "9", "no": "9",
    # Tamil (Tamil script & Latin transliteration)
    "பூஜ்ஜியம்": "0", "பூஜ்யம்": "0", "poojiyam": "0",
    "ஒன்று": "1", "ஒரு": "1", "ondru": "1", "onru": "1", "onnu": "1",
    "இரண்டு": "2", "ரெண்டு": "2", "irandu": "2", "rendu": "2",
    "மூன்று": "3", "மூணு": "3", "moondru": "3", "moonu": "3",
    "நான்கு": "4", "நாலு": "4", "naangu": "4", "naalu": "4",
    "ஐந்து": "5", "அஞ்சு": "5", "ainthu": "5", "anju": "5",
    "ஆறு": "6", "aaru": "6",
    "ஏழு": "7", "ezhu": "7",
    "எட்டு": "8", "ettu": "8",
    "ஒன்பது": "9", "onpathu": "9", "ombadhu": "9",
    # Devanagari & Tamil raw numeral characters
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
    "௦": "0", "௧": "1", "௨": "2", "௩": "3", "௪": "4",
    "௫": "5", "௬": "6", "௭": "7", "௮": "8", "௯": "9",
}


def _generate_challenge() -> tuple[str, str]:
    """
    Generate a random 4-digit challenge.
    Returns (phrase_words, phrase_digits):
        phrase_words = "four seven two nine"
        phrase_digits = "4 7 2 9"
    """
    digits = [random.randint(1, 9) for _ in range(4)]  # Use 1-9 for easiest pronunciation
    phrase_words = " ".join(DIGIT_WORDS_EN[d] for d in digits)
    phrase_digits = " ".join(str(d) for d in digits)
    return phrase_words, phrase_digits


def create_nonce(
    db: DBSession,
    session_id: str,
    bound_action: BoundAction,
    bound_target_id: str,
) -> ConfirmationNonce:
    """Create a new single-use time-bound nonce with a random challenge phrase."""
    # A replacement challenge makes every older active challenge for the same
    # action/target stale immediately.
    db.query(ConfirmationNonce).filter(
        ConfirmationNonce.session_id == session_id,
        ConfirmationNonce.bound_action == bound_action,
        ConfirmationNonce.bound_target_id == bound_target_id,
        ConfirmationNonce.consumed == False,
    ).update({"consumed": True, "consumed_at": datetime.now(timezone.utc)})

    phrase_words, phrase_digits = _generate_challenge()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.NONCE_EXPIRY_SECONDS)

    nonce = ConfirmationNonce(
        id=str(uuid.uuid4()),
        session_id=session_id,
        bound_action=bound_action,
        bound_target_id=bound_target_id,
        challenge_phrase=phrase_words,
        challenge_digits=phrase_digits,
        issued_at=now,
        expires_at=expires_at,
        consumed=False,
        attempt_count=0,
    )
    db.add(nonce)
    db.commit()
    db.refresh(nonce)

    _audit(db, session_id, EventType.NONCE_ISSUED, {
        "nonce_id": nonce.id,
        "bound_action": bound_action,
        "bound_target_id": bound_target_id,
        "expires_at": expires_at.isoformat(),
    })
    return nonce


def extract_spoken_digits(text: str) -> str:
    """
    Extract a sequence of digits from spoken text in English, Hindi, Tamil, or raw numbers.
    e.g. "चार सात दो" -> "472"
         "four seven two nine" -> "4729"
         "4 7 2" -> "472"
    """
    return vs_extract_spoken_digits(text)


def _phrases_match(expected_digits_spaced: str, spoken: str) -> bool:
    """
    Check if the user's spoken response matches the expected challenge digits.
    Accepts raw digits, spoken English, Hindi, or Tamil words.
    Strictly requires all expected digits (rejects partial matches).
    """
    expected_pure = "".join(expected_digits_spaced.split())
    extracted_pure = extract_spoken_digits(spoken)

    return bool(extracted_pure) and extracted_pure == expected_pure


class NonceValidationResult:
    def __init__(self, success: bool, reason: str):
        self.success = success
        self.reason = reason


def validate_and_consume(
    db: DBSession,
    nonce_id: str,
    session_id: str,
    transcribed_text: str,
    expected_action: Optional[BoundAction] = None,
    expected_target_id: Optional[str] = None,
) -> NonceValidationResult:
    """
    Validate a nonce response:
    1. Nonce exists
    2. Not expired
    3. Not already consumed
    4. session_id matches
    5. action/target match (if provided)
    6. Spoken challenge matches expected digits (English, Hindi, Tamil, or numeric)
    On success: mark consumed atomically.
    """
    nonce: Optional[ConfirmationNonce] = db.query(ConfirmationNonce).filter(
        ConfirmationNonce.id == nonce_id
    ).first()

    if not nonce:
        return NonceValidationResult(False, "Nonce not found")

    nonce.attempt_count += 1
    db.commit()

    if nonce.session_id != session_id:
        _audit(db, session_id, EventType.NONCE_REJECTED, {"reason": "session_mismatch", "nonce_id": nonce_id})
        return NonceValidationResult(False, "Session mismatch")

    if nonce.consumed:
        _audit(db, session_id, EventType.NONCE_REJECTED, {"reason": "already_consumed", "nonce_id": nonce_id})
        return NonceValidationResult(False, "Nonce already consumed")

    if datetime.now(timezone.utc) > nonce.expires_at.replace(tzinfo=timezone.utc) if nonce.expires_at.tzinfo is None else nonce.expires_at:
        _audit(db, session_id, EventType.NONCE_EXPIRED, {"nonce_id": nonce_id})
        return NonceValidationResult(False, "Nonce expired — please try again")

    if expected_action and nonce.bound_action != expected_action:
        _audit(db, session_id, EventType.NONCE_REJECTED, {"reason": "action_mismatch", "nonce_id": nonce_id})
        return NonceValidationResult(False, "Action mismatch")

    if expected_target_id and nonce.bound_target_id != expected_target_id:
        _audit(db, session_id, EventType.NONCE_REJECTED, {"reason": "target_mismatch", "nonce_id": nonce_id})
        return NonceValidationResult(False, "Target mismatch")

    # Match digits (e.g. nonce.challenge_digits = "4 7 2")
    if not _phrases_match(nonce.challenge_digits, transcribed_text):
        _audit(db, session_id, EventType.NONCE_REJECTED, {
            "reason": "phrase_mismatch",
            "nonce_id": nonce_id,
            "expected": nonce.challenge_digits,
            "got": transcribed_text,
        })
        return NonceValidationResult(False, "Digits did not match — please repeat all 4 numbers clearly")

    # All checks passed — consume nonce atomically
    nonce.consumed = True
    nonce.consumed_at = datetime.now(timezone.utc)
    db.commit()

    _audit(db, session_id, EventType.NONCE_VALIDATED, {
        "nonce_id": nonce_id,
        "bound_action": str(nonce.bound_action),
        "bound_target_id": nonce.bound_target_id,
    })
    return NonceValidationResult(True, "Confirmed successfully")


def build_challenge_audio_text(phrase_digits: str, language: str = "en") -> str:
    """Build the TTS-ready challenge instruction in the user's language."""
    digits_spaced = ", ".join(list("".join(phrase_digits.split())))
    if language == "hi":
        return f"पुष्टि के लिए, कृपया ये चार अंक बोलें: {digits_spaced}"
    elif language == "ta":
        return f"உறுதிப்படுத்த, இந்த நான்கு எண்களைக் கூறுங்கள்: {digits_spaced}"
    return f"To confirm, please say the 4 digits: {digits_spaced}"


def _audit(db: DBSession, session_id: str, event_type: EventType, payload: dict):
    log = AuditLog(
        session_id=session_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(log)
    db.commit()

import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form as FastForm, HTTPException
from sqlalchemy.orm import Session as DBSession
from typing import Optional

from config import get_settings
from database import get_db
from models import FraudCheck as FraudCheckModel, AuditLog, EventType, UserSession
from schemas import FraudCheckRequest, FraudCheckResponse
from services.fraud_service import (
    classify_message, ocr_message_image, has_readable_text, redact_for_storage,
    ImageCheckError, OCR_CONTENT_TYPES,
)

settings = get_settings()

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.post("/check", response_model=FraudCheckResponse)
def check_fraud(data: FraudCheckRequest, db: DBSession = Depends(get_db)):
    """Classify a text message as safe / suspicious / fraud."""
    text = data.message_text or ""
    if not text.strip():
        return FraudCheckResponse(
            check_id=str(uuid.uuid4()),
            classification="safe",
            confidence=0.0,
            risk_level="low",
            explanation="No message text provided to analyze.",
            explanation_audio_text="Please paste or type a message to check.",
            fraud_indicators=[],
            advice="Please provide a message to analyze.",
        )

    result = classify_message(text, data.language)
    check_id = str(uuid.uuid4())

    valid_session = None
    if data.session_id:
        valid_session = db.query(UserSession).filter(UserSession.id == data.session_id).first()

    db_check = FraudCheckModel(
        id=check_id,
        session_id=valid_session.id if valid_session else None,
        input_type="text",
        input_text=redact_for_storage(text),  # numbers / emails / link paths are not retained
        classification=result["classification"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        fraud_indicators=result["fraud_indicators"],
    )
    db.add(db_check)

    db.add(AuditLog(
        session_id=valid_session.id if valid_session else None,
        event_type=EventType.FRAUD_CHECKED,
        payload={
            "check_id": check_id,
            "classification": result["classification"],
            "confidence": result["confidence"],
        },
    ))
    db.commit()

    return FraudCheckResponse(
        check_id=check_id,
        **result,
    )


def _image_error(code: str, status: int, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


@router.post("/check-image")
async def check_fraud_image(
    session_id: Optional[str] = FastForm(None),
    language: str = FastForm("en"),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    """
    Read the text of a message from a photo / screenshot the customer chose, then classify it.

    The image is only held in memory for OCR: it is never saved to disk, stored or logged.
    If no text can be read, an error is returned — an unreadable photo is never reported as "safe".
    Errors: {"detail": {"code", "message"}} with codes unsupported_type (415), file_too_large (413),
    empty_file / unreadable_image / no_text_found (422), ocr_failed (502/504), ocr_unavailable (503).
    """
    declared = (file.content_type or "").lower()
    if declared and declared not in OCR_CONTENT_TYPES and declared != "application/octet-stream":
        raise _image_error("unsupported_type", 415, "Unsupported file type. Please use a JPG, PNG, WebP or BMP image.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise _image_error("file_too_large", 413, f"The image is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.")
    if not content:
        raise _image_error("empty_file", 422, "The uploaded image is empty.")

    try:
        extracted_text = ocr_message_image(content)
    except ImageCheckError as e:
        raise _image_error(e.code, e.status, e.message)
    finally:
        del content  # nothing keeps the photo once OCR is done

    if not has_readable_text(extracted_text):
        raise _image_error("no_text_found", 422,
                           "No readable message text was found in the image. This does not mean the message is safe.")

    result = classify_message(extracted_text, language)
    check_id = str(uuid.uuid4())

    db.add(FraudCheckModel(
        id=check_id,
        session_id=session_id,
        input_type="image",
        input_text=redact_for_storage(extracted_text),  # the photo itself is never stored (input_ref stays empty)
        classification=result["classification"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        fraud_indicators=result["fraud_indicators"],
    ))
    db.commit()

    return {
        "check_id": check_id,
        "extracted_text": extracted_text,
        **result,
    }

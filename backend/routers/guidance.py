from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import AuditLog, EventType, UserSession
from schemas import GuidanceRequest, GuidanceResponse
from services.guidance_service import get_guidance

router = APIRouter(prefix="/guidance", tags=["guidance"])


@router.post("/ask", response_model=GuidanceResponse)
def ask_guidance(data: GuidanceRequest, db: DBSession = Depends(get_db)):
    """Answer a free-form financial/banking question."""
    result = get_guidance(data.question, data.language, history=data.history[-20:], context=data.context)

    valid_session = None
    if data.session_id:
        valid_session = db.query(UserSession).filter(UserSession.id == data.session_id).first()

    db.add(AuditLog(
        session_id=valid_session.id if valid_session else None,
        event_type=EventType.GUIDANCE_ASKED,
        payload={"question": data.question, "intent": result["intent"]},
    ))
    db.commit()

    return GuidanceResponse(**result)

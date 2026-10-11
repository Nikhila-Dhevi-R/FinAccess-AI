from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
import uuid
from datetime import datetime, timezone

from database import get_db
from models import User, UserSession, AuditLog, EventType
from schemas import SessionCreate, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
def create_session(data: SessionCreate, db: DBSession = Depends(get_db)):
    """Create a new user session. Optionally links to/creates a user by phone."""
    user = None
    if data.user_phone:
        user = db.query(User).filter(User.phone == data.user_phone).first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                phone=data.user_phone,
                preferred_language=data.preferred_language,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    session = UserSession(
        id=str(uuid.uuid4()),
        user_id=user.id if user else None,
        preferred_language=data.preferred_language,
        started_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
    db.add(session)

    log = AuditLog(
        session_id=session.id,
        event_type=EventType.SESSION_CREATED,
        payload={"preferred_language": data.preferred_language},
    )
    db.add(log)
    db.commit()
    db.refresh(session)

    return session


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}/language")
def update_language(session_id: str, language: str, db: DBSession = Depends(get_db)):
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.preferred_language = language
    db.commit()
    return {"session_id": session_id, "preferred_language": language}


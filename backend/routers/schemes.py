from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession
from typing import Optional

from database import get_db
from models import AuditLog, EventType
from schemas import UserProfile, SchemeMatchResponse, SchemeGroupInfo, SchemeCard
from services.scheme_service import (
    match_schemes_categorized,
    build_schemes_audio_summary,
    get_scheme_groups,
    get_schemes_by_group,
    get_scheme_by_id,
    SCHEMES,
)
from services.schemes_data import SCHEMES_CATALOGUE
from services.scheme_finder import filter_options, search as search_schemes, tags_for

router = APIRouter(prefix="/schemes", tags=["schemes"])


@router.get("/groups", response_model=list[SchemeGroupInfo])
def list_scheme_groups(language: str = Query("en", description="User language code (en, hi, ta)")):
    """Return all 8 scheme categories with localized titles, descriptions, and scheme counts."""
    return get_scheme_groups(language=language)


@router.get("/filters")
def list_scheme_filters(language: str = Query("en", description="User language code (en, hi, ta)")):
    """'Who is it for?' and 'What do you need?' filter options, labelled in the user's language, with counts."""
    return filter_options(language)


@router.get("", response_model=list[SchemeCard])
def list_schemes(
    group: Optional[str] = Query(None, description="Filter schemes by group ID"),
    language: str = Query("en", description="User language code (en, hi, ta)"),
    audience: Optional[str] = Query(None, description="Who it is for: farmer, woman, girl_child, student, senior, ..."),
    need: Optional[str] = Query(None, description="What it gives: pension, loan, house, insurance, education, ..."),
    q: Optional[str] = Query(None, description="Free-text search in English, Hindi, Tamil or Hinglish"),
):
    """List schemes, localized, filtered by category / audience / need and optionally searched (best match first)."""
    from services.scheme_service import _format_scheme_card
    if q and q.strip():
        by_id = {s["id"]: s for s in SCHEMES_CATALOGUE}
        candidates = [by_id[sid] for sid, _ in search_schemes(q)]
    elif group and not (audience or need):
        return get_schemes_by_group(group, language=language)
    else:
        candidates = list(SCHEMES_CATALOGUE)
    if group:
        candidates = [s for s in candidates if s["group_id"] == group]
    if audience:
        candidates = [s for s in candidates if audience in tags_for(s["id"])[0]]
    if need:
        candidates = [s for s in candidates if need in tags_for(s["id"])[1]]
    return [_format_scheme_card(s, language=language) for s in candidates]


@router.get("/all")
def list_all_schemes():
    """Return all available schemes (for backward reference/testing)."""
    return {"schemes": SCHEMES, "total": len(SCHEMES_CATALOGUE)}


@router.get("/{scheme_id}", response_model=SchemeCard)
def get_scheme(
    scheme_id: str,
    language: str = Query("en", description="User language code (en, hi, ta)"),
):
    """Get full details of a specific government scheme."""
    scheme = get_scheme_by_id(scheme_id, language=language)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme


@router.post("/match", response_model=SchemeMatchResponse)
def match_user_schemes(
    profile: UserProfile,
    language: str = Query("en", description="User language code (en, hi, ta)"),
    db: DBSession = Depends(get_db),
):
    """Match user profile attributes to eligible government schemes with categorized outcomes."""
    matched, needs_info = match_schemes_categorized(profile, language=language)
    audio_summary = build_schemes_audio_summary(matched, needs_info, language=language)

    db.add(AuditLog(
        session_id=None,
        event_type=EventType.SCHEME_MATCHED,
        payload={
            "profile": profile.model_dump(),
            "matched_count": len(matched),
            "needs_info_count": len(needs_info),
            "scheme_ids": [s.scheme_id for s in matched],
            "language": language,
        },
    ))
    db.commit()

    return SchemeMatchResponse(
        profile=profile,
        matched_schemes=matched,
        needs_more_info_schemes=needs_info,
        total_matched=len(matched),
        explanation_audio_text=audio_summary,
    )

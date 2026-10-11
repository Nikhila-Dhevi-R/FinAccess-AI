"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime
from models import FormStatus, FieldStatus, BoundAction


# ─── Session ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    preferred_language: str = "en"
    user_phone: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    preferred_language: str
    started_at: datetime
    current_workflow: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Form ─────────────────────────────────────────────────────────────────────

class FieldPosition(BaseModel):
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 20
    page: int = 1


class FieldSchema(BaseModel):
    id: str
    label: str
    label_local: Optional[str] = None  # the label in the customer's language (e.g. "नाम" for "Name")
    field_type: str = "text"
    question_text: Optional[str] = None
    position: Optional[FieldPosition] = None
    order_index: int = 0
    status: FieldStatus = FieldStatus.PENDING


class FormUploadResponse(BaseModel):
    form_id: str
    session_id: str
    status: FormStatus
    fields: list[FieldSchema]
    total_fields: int
    message: str


class NextFieldResponse(BaseModel):
    form_id: str
    field: Optional[FieldSchema] = None
    question_audio_text: str  # text to be spoken by TTS
    progress: dict  # {completed, total, percentage}
    is_complete: bool = False


class FieldAnswerRequest(BaseModel):
    transcribed_text: str
    language: str = "en"
    confidence: Optional[float] = None


class FieldAnswerResponse(BaseModel):
    field_id: str
    interpreted_value: str
    validation_passed: bool
    validation_message: Optional[str] = None
    readback_text: str  # "I heard: Ramesh Kumar — is that right?"
    nonce_id: Optional[str] = None  # Challenge nonce for confirmation
    challenge_phrase: Optional[str] = None  # e.g. "four seven two"
    challenge_digits: Optional[str] = None  # e.g. "4 7 2"
    challenge_audio_text: Optional[str] = None
    expires_in_seconds: int = 30
    form_value: Optional[str] = None  # how it will be written on the form (Hindi / Tamil → English letters)


class FormFinalizeResponse(BaseModel):
    form_id: str
    pdf_url: str
    confirmed_fields: int
    total_fields: int
    message: str


# ─── Confirmation ─────────────────────────────────────────────────────────────

class ConfirmationCreateRequest(BaseModel):
    session_id: str
    bound_action: BoundAction
    bound_target_id: str


class ConfirmationCreateResponse(BaseModel):
    nonce_id: str
    challenge_phrase: str
    challenge_digits: str
    challenge_audio_text: str
    expires_in_seconds: int = 30
    bound_action: str
    bound_target_id: str


class ConfirmationRespondRequest(BaseModel):
    session_id: str
    transcribed_text: str


class ConfirmationRespondResponse(BaseModel):
    success: bool
    nonce_id: str
    message: str
    action_committed: bool = False
    new_nonce: Optional["ConfirmationCreateResponse"] = None  # issued on retry


# ─── Schemes ─────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occupation: Optional[str] = None           # farmer | salaried | self_employed | unemployed | student | laborer
    gender: Optional[str] = None               # male | female | other
    age: Optional[int] = None
    annual_income: Optional[float] = None
    literacy: Optional[str] = None             # illiterate | low | basic | literate
    employment_status: Optional[str] = None    # employed | unemployed | self_employed
    disability_status: Optional[str] = None    # none | physical | visual | hearing | cognitive
    disability: Optional[bool] = None
    income_bracket: Optional[str] = None       # below_20k | 20k_60k | 60k_200k | above_200k (annual INR)
    land_ownership: Optional[str] = None       # none | <2ha | 2-5ha | >5ha
    state: Optional[str] = None
    caste_category: Optional[str] = None       # general | obc | sc | st
    has_bank_account: Optional[bool] = None
    has_aadhaar: Optional[bool] = None
    has_ration_card: Optional[bool] = None     # BPL / NFSA card status
    area_type: Optional[str] = None


class SchemeGroupInfo(BaseModel):
    id: str
    icon: str
    title: str
    description: str
    scheme_count: int = 0


class SchemeCard(BaseModel):
    scheme_id: str
    group_id: Optional[str] = None
    name: str
    short_name: Optional[str] = None
    ministry: Optional[str] = None
    benefit_summary: str
    eligibility_reason: str
    who_can_get: Optional[str] = None
    how_to_apply: Optional[str] = None
    where_to_apply: Optional[str] = None
    documents_required: list[str] = []
    helpline: Optional[str] = None
    website: Optional[str] = None
    audio_text: Optional[str] = None
    application_steps: list[str] = []
    tags: list[str] = []
    match_score: float = 0.8
    status: str = "matched"  # "matched" | "needs_more_info"
    missing_criteria: Optional[list[str]] = None


class SchemeMatchResponse(BaseModel):
    profile: UserProfile
    matched_schemes: list[SchemeCard]
    needs_more_info_schemes: list[SchemeCard] = []
    total_matched: int
    explanation_audio_text: str  # summary for TTS



# ─── Guidance ─────────────────────────────────────────────────────────────────

class GuidanceRequest(BaseModel):
    session_id: Optional[str] = None
    question: str
    language: str = "en"
    # conversation so far (kept by the browser) — lets follow-ups like "what documents?" or "yes" make sense
    history: list[dict] = []
    context: dict = {}


class GuidanceResponse(BaseModel):
    answer: str
    answer_audio_text: str  # simplified version for TTS
    intent: str  # detected intent
    sources: list[str] = []
    follow_up_suggestions: list[str] = []
    topic: Optional[str] = None   # knowledge-base topic answered
    context: dict = {}            # send back with the next question


# ─── Fraud Check ─────────────────────────────────────────────────────────────

class FraudCheckRequest(BaseModel):
    session_id: Optional[str] = None
    message_text: Optional[str] = None
    language: str = "en"


class FraudCheckResponse(BaseModel):
    check_id: str
    classification: str       # safe | suspicious | fraud
    confidence: float
    risk_level: str           # low | medium | high | critical
    explanation: str
    explanation_audio_text: str  # plain language for TTS
    fraud_indicators: list[str]
    advice: str
    scam_type: Optional[str] = None  # e.g. "Fake KYC update scam", in the requested language



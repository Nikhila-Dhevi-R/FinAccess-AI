"""ORM models for FinAccess AI."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class FormStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FINALIZED = "finalized"


class FieldStatus(str, enum.Enum):
    PENDING = "pending"
    ASKED = "asked"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class BoundAction(str, enum.Enum):
    CONFIRM_FIELD = "confirm_field"
    SUBMIT_FORM = "submit_form"
    CONFIRM_SCHEME_APPLICATION = "confirm_scheme_application"


class OtpChannel(str, enum.Enum):
    SMS = "sms"


class EventType(str, enum.Enum):
    SESSION_CREATED = "session_created"
    FORM_UPLOADED = "form_uploaded"
    FIELD_ANSWERED = "field_answered"
    NONCE_ISSUED = "nonce_issued"
    NONCE_VALIDATED = "nonce_validated"
    NONCE_REJECTED = "nonce_rejected"
    NONCE_EXPIRED = "nonce_expired"
    FIELD_CONFIRMED = "field_confirmed"
    FORM_FINALIZED = "form_finalized"
    SCHEME_MATCHED = "scheme_matched"
    FRAUD_CHECKED = "fraud_checked"
    GUIDANCE_ASKED = "guidance_asked"
    OTP_SENT = "otp_sent"
    OTP_VERIFIED = "otp_verified"
    OTP_REJECTED = "otp_rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    # Account identity fields are optional for legacy phone-only records.
    username = Column(String, nullable=True, unique=True, index=True)
    email = Column(String, nullable=True, unique=True, index=True)
    mpin_hash = Column(String, nullable=True)
    # Optional contact/profile data used by the separate form-fill OTP flow.
    phone = Column(String, unique=True, nullable=True)
    preferred_language = Column(String, default="en")
    profile_attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sessions = relationship("UserSession", back_populates="user")
    scheme_matches = relationship("SchemeMatch", back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    current_workflow = Column(String, nullable=True)
    current_step = Column(String, nullable=True)
    state_blob = Column(JSON, default=dict)
    preferred_language = Column(String, default="en")

    user = relationship("User", back_populates="sessions")
    forms = relationship("Form", back_populates="session")
    nonces = relationship("ConfirmationNonce", back_populates="session")
    audit_logs = relationship("AuditLog", back_populates="session")
    phone_otps = relationship("PhoneOtp", back_populates="session")


class PhoneOtp(Base):
    """Session-bound Twilio Verify request; the OTP itself is never stored."""

    __tablename__ = "phone_otps"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("user_sessions.id"), nullable=False)
    phone = Column(String, nullable=False, index=True)
    verification_sid = Column(String, nullable=False)
    channel = Column(SAEnum(OtpChannel), nullable=False, default=OtpChannel.SMS)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    attempt_count = Column(Integer, default=0)
    consumed = Column(Boolean, default=False)
    consumed_at = Column(DateTime, nullable=True)

    session = relationship("UserSession", back_populates="phone_otps")


class Form(Base):
    __tablename__ = "forms"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("user_sessions.id"), nullable=False)
    template_id = Column(String, nullable=True)
    uploaded_image_ref = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    structured_field_schema = Column(JSON, default=list)
    status = Column(SAEnum(FormStatus), default=FormStatus.UPLOADING)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    session = relationship("UserSession", back_populates="forms")
    fields = relationship("FormField", back_populates="form", order_by="FormField.order_index")


class FormField(Base):
    __tablename__ = "form_fields"

    id = Column(String, primary_key=True, default=gen_uuid)
    form_id = Column(String, ForeignKey("forms.id"), nullable=False)
    label = Column(String, nullable=False)
    field_type = Column(String, default="text")
    question_text = Column(Text, nullable=True)
    position = Column(JSON, nullable=True)
    confirmed_value = Column(Text, nullable=True)
    raw_transcription = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    status = Column(SAEnum(FieldStatus), default=FieldStatus.PENDING)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    form = relationship("Form", back_populates="fields")


class ConfirmationNonce(Base):
    """Randomized anti-spoofing phrase challenge record."""

    __tablename__ = "confirmation_nonces"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("user_sessions.id"), nullable=False)
    bound_action = Column(SAEnum(BoundAction), nullable=False)
    bound_target_id = Column(String, nullable=False)
    challenge_phrase = Column(String, nullable=False)
    challenge_digits = Column(String, nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, default=False)
    consumed_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, default=0)

    session = relationship("UserSession", back_populates="nonces")


class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=True)
    ministry = Column(String, nullable=True)
    benefit_summary = Column(Text, nullable=False)
    eligibility_rules = Column(JSON, default=dict)
    application_steps = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    matches = relationship("SchemeMatch", back_populates="scheme")


class SchemeMatch(Base):
    __tablename__ = "scheme_matches"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    session_id = Column(String, nullable=True)
    scheme_id = Column(String, ForeignKey("schemes.id"), nullable=False)
    matched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    eligibility_reason = Column(Text, nullable=True)
    match_score = Column(Float, default=1.0)

    user = relationship("User", back_populates="scheme_matches")
    scheme = relationship("Scheme", back_populates="matches")


class FraudCheck(Base):
    __tablename__ = "fraud_checks"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, nullable=True)
    input_type = Column(String, default="text")
    input_text = Column(Text, nullable=True)
    input_ref = Column(String, nullable=True)
    classification = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    fraud_indicators = Column(JSON, default=list)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("user_sessions.id"), nullable=True)
    event_type = Column(SAEnum(EventType), nullable=False)
    payload = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("UserSession", back_populates="audit_logs")

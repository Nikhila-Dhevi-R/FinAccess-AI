"""
Comprehensive Test Suite for FinAccess AI
Tests:
1. Government Schemes Catalogue (all 8 groups, en/hi/ta completeness, fields)
2. Deterministic Voice Parsing & Multilingual Interpreters
3. 5-Point Eligibility Matching Engine & Group Prioritization
4. Nonce Engine Security (anti-replay, expiry, session isolation, partial/wrong rejection)
5. FastAPI Versioned API (/api/v1) & Form Fill flow
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from main import app
from conftest import TestingSessionLocal

client = TestClient(app)
from models import UserSession, ConfirmationNonce, BoundAction, Form, FormField, FormStatus, FieldStatus
from services.schemes_data import SCHEMES_CATALOGUE, SCHEME_GROUPS
from services.scheme_service import (
    get_scheme_groups,
    get_schemes_by_group,
    get_scheme_by_id,
    match_schemes_categorized,
    build_schemes_audio_summary,
)
from services import voice_service, nonce_service


# ─── 1. SCHEMES CATALOGUE & LOCALIZATION TESTS ─────────────────────────────
class TestSchemesCatalogue:
    def test_all_8_groups_present(self):
        groups = get_scheme_groups("en")
        assert len(groups) == 8
        group_ids = [g.id for g in groups]
        expected_groups = [
            "farmers", "daily_wage_workers", "girls_and_students", "elderly",
            "women", "loans_and_business", "subsidies", "health_and_insurance"
        ]
        for eg in expected_groups:
            assert eg in group_ids

    def test_scheme_counts_and_multilingual_fields(self):
        # Must have at least 5-8 schemes in all 8 groups (we built 6 per group = 48 total)
        assert len(SCHEMES_CATALOGUE) >= 40

        for s in SCHEMES_CATALOGUE:
            # Check basic fields
            assert "id" in s and s["id"]
            assert "group_id" in s and s["group_id"]
            assert "helpline" in s and s["helpline"]
            assert "website" in s and s["website"]
            assert "translations" in s

            # Check English, Hindi, and Tamil localized metadata
            for lang in ["en", "hi", "ta"]:
                assert lang in s["translations"], f"Scheme {s['id']} missing '{lang}' translation"
                loc = s["translations"][lang]
                assert "name" in loc and loc["name"]
                assert "benefit_summary" in loc and loc["benefit_summary"]
                assert "who_can_get" in loc and loc["who_can_get"]
                assert "how_to_apply" in loc and loc["how_to_apply"]
                assert "documents_required" in loc and len(loc["documents_required"]) >= 1
                assert "audio_text" in loc and len(loc["audio_text"]) >= 10

    def test_tamil_and_hindi_retrieval(self):
        hi_schemes = get_schemes_by_group("farmers", language="hi")
        assert len(hi_schemes) >= 5
        assert "पीएम किसान" in hi_schemes[0].name or "किसान" in hi_schemes[0].name

        ta_schemes = get_schemes_by_group("farmers", language="ta")
        assert len(ta_schemes) >= 5
        assert any("விவசாயி" in s.name or "கிசான்" in s.name or "திட்டம்" in s.name for s in ta_schemes)


# ─── 2. DETERMINISTIC VOICE PARSING & VALIDATION TESTS ─────────────────────
class TestVoiceParsing:
    def test_normalize_digits(self):
        # Devanagari numerals ०-९
        assert voice_service.normalize_digits("१२३४५") == "12345"
        # Tamil numerals ௦-௯
        assert voice_service.normalize_digits("௧௨௩௪௫") == "12345"
        assert voice_service.normalize_digits("mixed ०1௨3") == "mixed 0123"

    def test_extract_spoken_digits_multilingual(self):
        # English
        assert voice_service.extract_spoken_digits("four seven two") == "472"
        assert voice_service.extract_spoken_digits("4 7 2") == "472"
        # Hindi
        assert voice_service.extract_spoken_digits("चार सात दो") == "472"
        assert voice_service.extract_spoken_digits("ek do teen") == "123"
        # Tamil
        assert voice_service.extract_spoken_digits("நான்கு ஏழு இரண்டு") == "472"
        assert voice_service.extract_spoken_digits("ondru irandu moondru") == "123"

    def test_yes_no_parser(self):
        # English
        assert voice_service.parse_yes_no("Yes, that is right") is True
        assert voice_service.parse_yes_no("No, cancel it") is False
        # Hindi
        assert voice_service.parse_yes_no("हाँ बिल्कुल सही") is True
        assert voice_service.parse_yes_no("नहीं गलत है") is False
        # Tamil
        assert voice_service.parse_yes_no("ஆம் சரிதான்") is True
        assert voice_service.parse_yes_no("இல்லை தவறு") is False

    def test_menu_choice_parser(self):
        assert voice_service.parse_menu_choice("1") == 1
        assert voice_service.parse_menu_choice("form fill please") == 1
        assert voice_service.parse_menu_choice("दो") == 2
        assert voice_service.parse_menu_choice("सरकारी योजनाएं") == 2
        assert voice_service.parse_menu_choice("3") == 3
        assert voice_service.parse_menu_choice("banking question") == 3
        assert voice_service.parse_menu_choice("चार") == 4
        assert voice_service.parse_menu_choice("check fraud scam") == 4

    def test_navigation_commands(self):
        assert voice_service.parse_navigation_command("next question please") == "next"
        assert voice_service.parse_navigation_command("आगे बढ़ो") == "next"
        assert voice_service.parse_navigation_command("அடுத்து") == "next"

        assert voice_service.parse_navigation_command("repeat again") == "repeat"
        assert voice_service.parse_navigation_command("दोबारा बोलो") == "repeat"
        assert voice_service.parse_navigation_command("மீண்டும்") == "repeat"

        assert voice_service.parse_navigation_command("go back") == "back"
        assert voice_service.parse_navigation_command("main menu home") == "home"
        assert voice_service.parse_navigation_command("stop now") == "stop"

    def test_field_validators(self):
        # Phone: 10 digits starting 6-9
        ok, _ = voice_service.validate_field("phone", "9876543210")
        assert ok is True
        ok, _ = voice_service.validate_field("phone", "1234567890")
        assert ok is False

        # PIN: 6 digits
        ok, _ = voice_service.validate_field("pin", "600001")
        assert ok is True
        ok, _ = voice_service.validate_field("pin", "012345")
        assert ok is False

        # Aadhaar: 12 digits
        ok, _ = voice_service.validate_field("aadhaar", "123456789012")
        assert ok is True
        ok, _ = voice_service.validate_field("aadhaar", "12345")
        assert ok is False


# ─── 3. DETERMINISTIC 5-POINT SCHEME MATCHING TESTS ────────────────────────
class TestSchemeMatching:
    def test_farmer_profile_prioritization(self):
        profile = {
            "occupation": "farmer",
            "gender": "male",
            "age": 45,
            "has_bank_account": True,
            "has_ration_card": True,
        }
        matched, needs_info = match_schemes_categorized(profile, language="en")
        assert len(matched) > 0
        first_match = matched[0]
        # Farmer scheme must be ranked top
        assert "Kisan" in first_match.name or "Fasal" in first_match.name or "Card" in first_match.name
        assert first_match.match_score >= 0.85

    def test_elderly_pension_profile(self):
        profile = {
            "occupation": "unemployed",
            "gender": "female",
            "age": 68,
            "has_bank_account": True,
            "has_ration_card": True,
        }
        matched, needs_info = match_schemes_categorized(profile, language="en")
        matched_names = [s.name for s in matched]
        assert any("Old Age Pension" in n or "Vayo" in n or "Jan Dhan" in n for n in matched_names)

    def test_student_scholarship_profile(self):
        profile = {
            "occupation": "student",
            "gender": "female",
            "age": 16,
            "has_bank_account": True,
            "has_ration_card": True,
        }
        matched, needs_info = match_schemes_categorized(profile, language="hi")
        assert len(matched) > 0
        audio_text = build_schemes_audio_summary(matched, needs_info, language="hi")
        assert "योजना" in audio_text or len(audio_text) > 10


# ─── 4. NONCE & SECURITY ENGINE TESTS ──────────────────────────────────────
class TestNonceSecurity:
    def test_nonce_creation_and_expiration(self):
        db = TestingSessionLocal()
        session = UserSession(id="sess-sec-1", preferred_language="en")
        db.add(session)
        db.commit()

        nonce = nonce_service.create_nonce(
            db=db,
            session_id="sess-sec-1",
            bound_action=BoundAction.CONFIRM_FIELD,
            bound_target_id="f-1",
        )
        assert nonce.id
        assert len(nonce.challenge_digits.split()) == 3
        assert nonce.consumed is False

        # Expired test
        nonce.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()

        res = nonce_service.validate_and_consume(
            db=db,
            nonce_id=nonce.id,
            session_id="sess-sec-1",
            transcribed_text=nonce.challenge_digits,
        )
        assert res.success is False
        assert "expired" in res.reason.lower()
        db.close()

    def test_nonce_anti_replay(self):
        db = TestingSessionLocal()
        session = UserSession(id="sess-sec-2", preferred_language="en")
        db.add(session)
        db.commit()

        nonce = nonce_service.create_nonce(
            db=db,
            session_id="sess-sec-2",
            bound_action=BoundAction.CONFIRM_FIELD,
            bound_target_id="f-2",
        )

        # 1st attempt: Valid
        res1 = nonce_service.validate_and_consume(
            db=db,
            nonce_id=nonce.id,
            session_id="sess-sec-2",
            transcribed_text=nonce.challenge_digits,
        )
        assert res1.success is True

        # 2nd attempt: Replay attack -> must reject
        res2 = nonce_service.validate_and_consume(
            db=db,
            nonce_id=nonce.id,
            session_id="sess-sec-2",
            transcribed_text=nonce.challenge_digits,
        )
        assert res2.success is False
        assert "consumed" in res2.reason.lower()
        db.close()

    def test_nonce_rejects_partial_and_wrong_digits(self):
        db = TestingSessionLocal()
        session = UserSession(id="sess-sec-3", preferred_language="en")
        db.add(session)
        db.commit()

        nonce = nonce_service.create_nonce(
            db=db,
            session_id="sess-sec-3",
            bound_action=BoundAction.CONFIRM_FIELD,
            bound_target_id="f-3",
        )
        # Expected e.g. "4 7 2"
        digits = nonce.challenge_digits.split()

        # Partial digit attempt (e.g. only first digit "4")
        res_partial = nonce_service.validate_and_consume(
            db=db,
            nonce_id=nonce.id,
            session_id="sess-sec-3",
            transcribed_text=digits[0],
        )
        assert res_partial.success is False

        # Wrong digits attempt
        res_wrong = nonce_service.validate_and_consume(
            db=db,
            nonce_id=nonce.id,
            session_id="sess-sec-3",
            transcribed_text="0 0 0",
        )
        assert res_wrong.success is False
        db.close()


# ─── 5. API V1 ENDPOINTS & FORM FILL FLOW TESTS ───────────────────────────
class TestApiV1Endpoints:
    def test_root_and_health(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["app"] == "FinAccess AI"

        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_session_lifecycle_v1(self):
        r = client.post("/api/v1/sessions", json={"preferred_language": "hi", "user_phone": "9876543210"})
        assert r.status_code == 200
        data = r.json()
        sid = data["id"]
        assert data["preferred_language"] == "hi"

        # Update language
        r2 = client.patch(f"/api/v1/sessions/{sid}/language?language=ta")
        assert r2.status_code == 200
        assert r2.json()["preferred_language"] == "ta"

    def test_schemes_api_v1(self):
        # Groups
        r = client.get("/api/v1/schemes/groups?language=hi")
        assert r.status_code == 200
        assert len(r.json()) == 8

        # Match API
        r_match = client.post("/api/v1/schemes/match?language=en", json={
            "occupation": "farmer",
            "gender": "male",
            "age": 40,
            "has_bank_account": True,
            "has_ration_card": True,
        })
        assert r_match.status_code == 200
        match_data = r_match.json()
        assert len(match_data["matched_schemes"]) > 0

    def test_guidance_and_fraud_v1(self):
        # Guidance
        r_guide = client.post("/api/v1/guidance/ask", json={
            "question": "How to open a Jan Dhan bank account?",
            "language": "en"
        })
        assert r_guide.status_code == 200
        assert "Jan Dhan" in r_guide.json()["answer"] or "account" in r_guide.json()["answer"]

        # Fraud check
        r_fraud = client.post("/api/v1/fraud/check", json={
            "message_text": "Dear user, share OTP immediately or your SBI account will be blocked.",
        })
        assert r_fraud.status_code == 200
        assert r_fraud.json()["classification"] in ["fraud", "suspicious"]

    def test_dynamic_document_extraction_and_overlay(self):
        import io
        # 1. Fetch official PM-Kisan test template
        template_res = client.get("/api/v1/forms/demo-templates/pm_kisan")
        assert template_res.status_code == 200
        pdf_bytes = template_res.content

        # 2. Upload PM-Kisan form
        files = {"file": ("pm_kisan_form.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        up_res = client.post("/api/v1/forms/upload", data={"session_id": "sess-dyn-test"}, files=files)
        assert up_res.status_code == 200
        form_data = up_res.json()
        form_id = form_data["form_id"]
        fields = form_data["fields"]

        # Verify ONLY document-specific fields were extracted
        labels = [f["label"] for f in fields]
        assert "Farmer Name" in labels
        assert "Land Holding (Acres)" in labels

        # Verify each field has extracted coordinates
        for f in fields:
            assert f["position"] is not None
            assert f["position"]["x"] > 0
            assert f["position"]["y"] > 0

        # 3. Answer and confirm each field
        for f in fields:
            ans_res = client.post(
                f"/api/v1/forms/{form_id}/fields/{f['id']}/answer",
                json={"transcribed_text": "Suresh Patel", "language": "en"}
            )
            assert ans_res.status_code == 200
            if not ans_res.json()["validation_passed"]:
                skip_res = client.post(f"/api/v1/forms/{form_id}/fields/{f['id']}/skip")
                assert skip_res.status_code == 200
                continue
            nid = ans_res.json()["nonce_id"]
            ndig = ans_res.json()["challenge_digits"]
            confirmed = client.post(
                f"/api/v1/confirmations/{nid}/respond",
                json={"session_id": "sess-dyn-test", "transcribed_text": ndig},
            )
            assert confirmed.status_code == 200, confirmed.text
            assert confirmed.json()["action_committed"] is True, confirmed.text

        for _ in range(len(fields) + 1):
            remaining = client.get(f"/api/v1/forms/{form_id}/next-field").json()
            if remaining["is_complete"]:
                break
            client.post(
                f"/api/v1/forms/{form_id}/fields/{remaining['field']['id']}/skip"
            )

        final_nonce_response = client.post("/api/v1/confirmations", json={
            "session_id": "sess-dyn-test",
            "bound_action": "submit_form",
            "bound_target_id": form_id,
        })
        assert final_nonce_response.status_code == 200, final_nonce_response.text
        final_nonce = final_nonce_response.json()
        final_confirm = client.post(
            f"/api/v1/confirmations/{final_nonce['nonce_id']}/respond",
            json={"session_id": "sess-dyn-test", "transcribed_text": final_nonce["challenge_digits"]},
        )
        assert final_confirm.json()["action_committed"] is True

        db = TestingSessionLocal()
        try:
            session = db.query(UserSession).filter(UserSession.id == "sess-dyn-test").one()
            session.state_blob = {
                **(session.state_blob or {}),
                "form_submission_authorized": {"form_id": form_id, "consumed": False},
            }
            db.commit()
        finally:
            db.close()

        # 4. Finalize and verify output PDF is merged with the original base form
        fin_res = client.post(f"/api/v1/forms/{form_id}/finalize")
        assert fin_res.status_code == 200, fin_res.text

        dl_res = client.get(f"/api/v1/forms/{form_id}/download")
        assert dl_res.status_code == 200
        assert len(dl_res.content) > 1500

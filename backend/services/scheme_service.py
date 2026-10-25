"""
FinAccess AI — Government Scheme Matching & Catalog Service
Deterministic rules engine with comprehensive 8-category multilingual catalogue.
"""

import re
from typing import Optional, Union
from schemas import UserProfile, SchemeCard, SchemeGroupInfo
from services.schemes_data import SCHEMES_CATALOGUE, SCHEME_GROUPS
from services.scheme_finder import localize_ministry, tags_for


def get_scheme_groups(language: str = "en") -> list[SchemeGroupInfo]:
    """Return all 8 scheme categories with localized titles and scheme counts."""
    lang = language if language in ("en", "hi", "ta") else "en"
    groups = []
    for g in SCHEME_GROUPS:
        count = len([s for s in SCHEMES_CATALOGUE if s["group_id"] == g["id"]])
        title = g["title"].get(lang, g["title"]["en"])
        desc = g["description"].get(lang, g["description"]["en"])
        groups.append(SchemeGroupInfo(
            id=g["id"],
            icon=g["icon"],
            title=title,
            description=desc,
            scheme_count=count,
        ))
    return groups


def _format_scheme_card(raw_scheme: dict, language: str = "en", status: str = "matched", score: float = 0.85, reason: str = "", missing: list[str] = None) -> SchemeCard:
    """Helper to build a localized SchemeCard model from raw scheme data."""
    lang = language if language in ("en", "hi", "ta") else "en"
    trans = raw_scheme.get("translations", {}).get(lang, raw_scheme.get("translations", {}).get("en", {}))

    name = trans.get("name", raw_scheme.get("name", "Government Scheme"))
    benefit = trans.get("benefit_summary", "")
    who = trans.get("who_can_get", "")
    how = trans.get("how_to_apply", "")
    where = trans.get("where_to_apply", "")
    docs = trans.get("documents_required", [])
    audio = trans.get("audio_text", f"{name}. {benefit}")

    # Generate step list if not explicit
    steps = [how] if how else ["Visit your local Common Service Centre (CSC) or government office with your Aadhaar card."]

    default_reason = {
        "en": "Matches your citizen profile requirements.",
        "hi": "आपकी प्रोफाइल के अनुसार पात्र।",
        "ta": "உங்கள் சுயவிவரத்தின்படி தகுதியானது.",
    }.get(lang, "Eligible based on profile.")

    return SchemeCard(
        scheme_id=raw_scheme["id"],
        group_id=raw_scheme.get("group_id"),
        name=name,
        short_name=trans.get("short_name") or raw_scheme.get("short_name"),
        ministry=trans.get("ministry") or localize_ministry(raw_scheme.get("ministry"), lang),
        benefit_summary=benefit,
        eligibility_reason=reason or default_reason,
        who_can_get=who,
        how_to_apply=how,
        where_to_apply=where,
        documents_required=docs,
        helpline=raw_scheme.get("helpline"),
        website=raw_scheme.get("website"),
        audio_text=audio,
        application_steps=steps,
        tags=[raw_scheme.get("group_id", "all")] + tags_for(raw_scheme["id"])[0] + tags_for(raw_scheme["id"])[1],
        match_score=score,
        status=status,
        missing_criteria=missing if missing else None,
    )


def get_schemes_by_group(group_id: str, language: str = "en") -> list[SchemeCard]:
    """Return all schemes belonging to a specific group."""
    matched = []
    for s in SCHEMES_CATALOGUE:
        if s["group_id"] == group_id:
            matched.append(_format_scheme_card(s, language=language))
    return matched


def get_scheme_by_id(scheme_id: str, language: str = "en") -> Optional[SchemeCard]:
    """Look up a single scheme by its unique ID."""
    for s in SCHEMES_CATALOGUE:
        if s["id"] == scheme_id:
            return _format_scheme_card(s, language=language)
    return None


_UPLOADED_STOP_WORDS = {
    "work", "worker", "person", "people", "individual", "individuals", "scheme", "schemes",
    "government", "india", "governmental", "category", "other", "the", "and", "for", "with",
}


def _uploaded_profile_terms(profile: UserProfile) -> list[str]:
    occupation = (profile.occupation or "").lower().strip()
    aliases = {
        "farmer": ["farmer", "farming", "agriculture", "agricultural", "kisan", "cultivator"],
        "laborer": ["labour", "labor", "worker", "construction", "daily wage", "unorganised", "unorganized", "shramik", "mazdoor"],
        "self_employed": ["business", "enterprise", "entrepreneur", "msme", "artisan", "vendor", "shopkeeper", "trader"],
        "student": ["student", "scholarship", "education", "school", "college", "university"],
        "unemployed": ["employment", "job", "jobs", "skill", "skills", "training", "worker"],
    }
    if occupation in aliases:
        return aliases[occupation]
    terms = [
        term for term in re.findall(r"[a-z0-9]{3,}", occupation)
        if term not in _UPLOADED_STOP_WORDS
    ]
    return list(dict.fromkeys([occupation, *terms])) if occupation else []


def _uploaded_age_ranges(text: str) -> list[tuple[int, int]]:
    ranges = []
    patterns = (
        r"\b(?:aged?|age group|between)\s*(\d{1,3})\s*(?:to|-|and)\s*(\d{1,3})\b",
        r"\b(\d{1,3})\s*(?:to|-)\s*(\d{1,3})\s*(?:years?|yrs?)\b",
    )
    for pattern in patterns:
        ranges.extend((int(low), int(high)) for low, high in re.findall(pattern, text, re.IGNORECASE))
    return list(dict.fromkeys(ranges))


def _evaluate_uploaded_scheme(
    profile: UserProfile, scheme: dict, language: str = "en"
) -> tuple[str, str, float, list[str]]:
    """Match a CSV row using its text and the available profile answers."""
    search_text = (scheme.get("search_text") or "").lower()
    eligibility_text = (scheme.get("eligibility_text") or "").lower()
    profile_terms = _uploaded_profile_terms(profile)
    term_hits = [term for term in profile_terms if term and term in search_text]
    generic_scheme = any(
        phrase in search_text
        for phrase in ("all citizens", "any citizen", "all residents", "any resident", "all individuals")
    )
    if not term_hits and not generic_scheme:
        return "ineligible", "Category does not match scheme details", 0.0, []

    reasons = []
    missing = []
    if term_hits:
        reasons.append(f"Your category matches the scheme details ({term_hits[0]})")
    elif generic_scheme:
        reasons.append("This scheme is described for all citizens or residents")

    female_only = any(term in eligibility_text for term in ("woman", "women", "female", "girl", "maternity", "pregnant", "widow"))
    male_only = any(term in eligibility_text for term in ("man", "men", "male", "boy"))
    if profile.gender == "male" and female_only:
        return "ineligible", "Gender does not match scheme eligibility", 0.0, []
    if profile.gender == "female" and male_only and not female_only:
        return "ineligible", "Gender does not match scheme eligibility", 0.0, []
    if female_only or male_only:
        if profile.gender is None:
            missing.append("Confirm your gender")
        else:
            reasons.append("Gender matches the eligibility text")

    age_ranges = _uploaded_age_ranges(eligibility_text)
    if age_ranges:
        if profile.age is None:
            missing.append("Confirm your age")
        elif not any(low <= profile.age <= high for low, high in age_ranges):
            return "ineligible", "Age does not match scheme eligibility", 0.0, []
        else:
            reasons.append(f"Age ({profile.age}) is within the stated range")

    bank_required = any(term in eligibility_text for term in ("bank account", "savings account", "bank details", "passbook"))
    if bank_required:
        if profile.has_bank_account is False:
            missing.append("Need to open or link a bank account")
        elif profile.has_bank_account is None:
            missing.append("Confirm whether you have a bank account")
        else:
            reasons.append("Bank-account requirement is confirmed")

    ration_required = any(term in eligibility_text for term in ("ration card", "bpl", "nfsa", "priority household"))
    if ration_required:
        if profile.has_ration_card is False:
            missing.append("Confirm eligibility without a ration card at the local office")
        elif profile.has_ration_card is None:
            missing.append("Confirm whether you have a ration card")
        else:
            reasons.append("Ration-card requirement is confirmed")

    score = min((0.74 if term_hits else 0.60) + (0.08 if len(term_hits) > 1 else 0.0) + (0.05 if age_ranges else 0.0), 0.95)
    if missing:
        return "needs_more_info", ". ".join(reasons), min(score, 0.75), missing
    return "matched", ". ".join(reasons), score, []


def _evaluate_scheme_eligibility(
    profile: UserProfile, scheme: dict, language: str = "en"
) -> tuple[str, str, float, list[str]]:
    """
    Deterministic 5-point eligibility evaluation:
    1. Occupation / Work
    2. Gender
    3. Age
    4. Bank Account
    5. BPL / Ration card

    Returns (status, reason, score, missing_criteria):
        status: "matched" | "needs_more_info" | "ineligible"
    """
    lang = language if language in ("en", "hi", "ta") else "en"
    if scheme.get("source") == "updated_data.csv":
        return _evaluate_uploaded_scheme(profile, scheme, language=lang)
    rules = scheme.get("eligibility_rules", {})
    reasons = []
    missing = []
    score = 0.60

    # 1. Occupation Check
    if "occupation" in rules:
        target_occs = [o.lower() for o in rules["occupation"]]
        user_occ = (profile.occupation or "").lower().strip()
        if user_occ:
            if user_occ in target_occs or any(t in user_occ for t in target_occs):
                reasons.append({
                    "en": f"Occupation ({profile.occupation}) qualifies",
                    "hi": f"व्यवसाय ({profile.occupation}) पात्र है",
                    "ta": f"தொழில் ({profile.occupation}) தகுதியானது",
                }.get(lang, "Occupation qualifies"))
                score += 0.25
            else:
                return "ineligible", "Occupation does not match scheme target", 0.0, []
        else:
            missing.append({
                "en": "Confirm specific occupation at office",
                "hi": "कार्यालय में अपने व्यवसाय की पुष्टि करें",
                "ta": "அலுவலகத்தில் தொழில் விவரத்தை உறுதிப்படுத்தவும்",
            }.get(lang, "Confirm occupation"))

    # Optional category check used by uploaded catalogues for custom groups
    # such as street vendors, artisans, domestic workers, or fishers.
    if "category" in rules:
        raw_categories = rules["category"]
        if isinstance(raw_categories, str):
            raw_categories = [raw_categories]
        target_categories = [str(value).lower().strip() for value in raw_categories]
        user_categories = [str(value).lower().strip() for value in (profile.category, profile.occupation) if value]
        if not user_categories:
            missing.append("Confirm your category")
        elif not any(
            user_value in target_categories
            or any(target in user_value for target in target_categories)
            for user_value in user_categories
        ):
            return "ineligible", "Category does not match scheme target", 0.0, []
        else:
            reasons.append("Category matches this scheme")

    # 2. Gender Check
    if "gender" in rules:
        target_genders = [g.lower() for g in rules["gender"]]
        user_gender = (profile.gender or "").lower().strip()
        if user_gender:
            if user_gender in target_genders:
                reasons.append({
                    "en": f"Eligible for {profile.gender}",
                    "hi": f"{profile.gender} के लिए विशेष योजना",
                    "ta": f"{profile.gender} பிரிவினருக்கான திட்டம்",
                }.get(lang, "Gender condition met"))
                score += 0.20
            else:
                return "ineligible", "Gender requirement not met", 0.0, []
        else:
            missing.append({
                "en": f"Targeted for {', '.join(rules['gender'])}",
                "hi": f"{', '.join(rules['gender'])} के लिए आरक्षित",
                "ta": f"{', '.join(rules['gender'])} பிரிவினருக்கானது",
            }.get(lang, "Gender confirmation"))

    # 3. Age Check
    if "min_age" in rules:
        min_a = rules["min_age"]
        if profile.age is not None:
            if profile.age < min_a:
                return "ineligible", f"Minimum age required is {min_a} years", 0.0, []
            reasons.append({
                "en": f"Age ({profile.age}) meets minimum age ({min_a}+)",
                "hi": f"आयु ({profile.age} वर्ष) न्यूनतम पात्रता ({min_a}+) पूरी करती है",
                "ta": f"வயது ({profile.age}) தகுதி வரம்பை பூர்த்தி செய்கிறது ({min_a}+)",
            }.get(lang, "Age qualifies"))
            score += 0.15
        else:
            missing.append({
                "en": f"Age verification required (minimum {min_a} years)",
                "hi": f"आयु सत्यापन (न्यूनतम {min_a} वर्ष) आवश्यक",
                "ta": f"வயது சான்றிதழ் தேவை (குறைந்தபட்சம் {min_a} வயது)",
            }.get(lang, f"Min age {min_a}"))

    if "max_age" in rules:
        max_a = rules["max_age"]
        if profile.age is not None:
            if profile.age > max_a:
                return "ineligible", f"Maximum age limit is {max_a} years", 0.0, []
            score += 0.10
        else:
            missing.append({
                "en": f"Age limit check (maximum {max_a} years)",
                "hi": f"आयु सीमा (अधिकतम {max_a} वर्ष) की जांच",
                "ta": f"அதிகபட்ச வயது வரம்பு ({max_a} வயது)",
            }.get(lang, f"Max age {max_a}"))

    # 4. Bank Account Check
    if "has_bank_account" in rules:
        req_bank = rules["has_bank_account"]
        if profile.has_bank_account is not None:
            if profile.has_bank_account == req_bank:
                reasons.append({
                    "en": "Bank account verified for direct cash transfer (DBT)",
                    "hi": "सीधे बैंक खाते में पैसा भेजने (DBT) के लिए खाता उपलब्ध",
                    "ta": "நேரடி பண பரிமாற்றத்திற்கு வங்கி கணக்கு சரிபார்க்கப்பட்டது",
                }.get(lang, "Bank account condition met"))
                score += 0.10
            else:
                if req_bank is True and profile.has_bank_account is False:
                    missing.append({
                        "en": "Need to open zero-balance Jan Dhan bank account at post office/bank",
                        "hi": "बैंक या डाकघर में जन-धन खाता खुलवाना होगा",
                        "ta": "வங்கி அல்லது தபால் நிலையத்தில் ஜன் தன் கணக்கு தொடங்க வேண்டும்",
                    }.get(lang, "Bank account required"))
        else:
            missing.append({
                "en": "Bank account passbook required for money transfer",
                "hi": "पैसा प्राप्त करने के लिए बैंक पासबुक आवश्यक",
                "ta": "பணம் பெற வங்கி பாஸ்புக் தேவை",
            }.get(lang, "Bank passbook"))

    # 5. Ration Card / BPL Check
    if "has_ration_card" in rules:
        req_rc = rules["has_ration_card"]
        if profile.has_ration_card is not None:
            if profile.has_ration_card == req_rc:
                reasons.append({
                    "en": "Ration card condition satisfied",
                    "hi": "राशन कार्ड पात्रता पूरी हुई",
                    "ta": "ரேஷன் அட்டை நிபந்தனை பூர்த்தியடைந்தது",
                }.get(lang, "Ration card verified"))
                score += 0.10
        else:
            missing.append({
                "en": "Confirm family ration card at local office for state top-up",
                "hi": "राज्य टॉप-अप के लिए कार्यालय में राशन कार्ड की पुष्टि करें",
                "ta": "கூடுதல் நிதி உதவிக்கு ரேஷன் அட்டையை உறுதிப்படுத்தவும்",
            }.get(lang, "Ration card confirmation"))

    # Categorize Outcome
    if missing and score < 0.80:
        reason_text = ". ".join(reasons) if reasons else {
            "en": "Likely eligible! Please confirm required documents at your local office.",
            "hi": "आप इसके लिए पात्र हो सकते हैं! कृपया कार्यालय में दस्तावेजों की पुष्टि करें।",
            "ta": "நீங்கள் தகுதி பெற வாய்ப்புள்ளது! ஆவணங்களை அலுவலகத்தில் உறுதிப்படுத்தவும்.",
        }.get(lang, "Likely eligible.")
        return "needs_more_info", reason_text, min(score, 0.75), missing
    else:
        reason_text = ". ".join(reasons) if reasons else {
            "en": "You meet all primary criteria for this scheme.",
            "hi": "आप इस योजना की सभी प्राथमिक शर्तें पूरी करते हैं।",
            "ta": "நீங்கள் இந்த திட்டத்தின் அனைத்து முதன்மை தகுதிகளையும் பெற்றுள்ளீர்கள்.",
        }.get(lang, "Matched successfully.")
        return "matched", reason_text, min(score + 0.15, 1.0), missing


def match_schemes_categorized(profile: Union[UserProfile, dict], language: str = "en") -> dict:
    """
    Evaluate user profile against all schemes in the catalogue.
    Prioritizes user's primary group first (e.g. farmer -> farmers, age>=60 -> elderly, female -> women).
    Returns dictionary with matched_schemes, needs_more_info_schemes, and explanation_audio_text.
    """
    if isinstance(profile, dict):
        profile = UserProfile(**profile)
    lang = language if language in ("en", "hi", "ta") else "en"
    matched = []
    needs_info = []

    # Determine primary user target groups for prioritization
    user_occ = (profile.occupation or "").lower()
    is_farmer = "farm" in user_occ or "kisan" in user_occ
    is_laborer = any(word in user_occ for word in ("labour", "labor", "worker", "unemployed", "mazdoor"))
    is_student = "student" in user_occ or (profile.age is not None and profile.age <= 22 and profile.age >= 5)
    is_senior = profile.age is not None and profile.age >= 60
    is_female = (profile.gender or "").lower() == "female"
    is_business = "business" in user_occ or "self" in user_occ or "shop" in user_occ
    is_custom_category = (profile.category or "").lower() == "other"

    for scheme in SCHEMES_CATALOGUE:
        status, reason, score, missing = _evaluate_scheme_eligibility(profile, scheme, language=lang)
        if status == "ineligible":
            continue

        # Priority boost for user's own demographic groups
        gid = scheme.get("group_id")
        group_boost = 0.0
        if is_farmer and gid == "farmers":
            group_boost += 0.35
        elif is_senior and gid == "elderly":
            group_boost += 0.35
        elif is_female and gid == "women":
            group_boost += 0.30
        elif is_student and gid == "girls_and_students":
            group_boost += 0.30
        elif is_laborer and gid == "daily_wage_workers":
            group_boost += 0.30
        elif is_business and gid == "loans_and_business":
            group_boost += 0.30
        if is_custom_category and scheme.get("source") == "updated_data.csv":
            group_boost += 0.20

        final_score = min(score + group_boost, 1.0)
        card = _format_scheme_card(
            scheme,
            language=lang,
            status=status,
            score=round(final_score, 2),
            reason=reason,
            missing=missing,
        )

        if status == "matched":
            matched.append(card)
        elif status == "needs_more_info":
            needs_info.append(card)

    # Sort descending by match score. For a typed custom category, prefer the
    # uploaded catalogue because it contains the user's own category wording.
    if is_custom_category:
        matched.sort(key=lambda x: (0 if x.scheme_id.startswith("dataset-") else 1, -x.match_score))
        needs_info.sort(key=lambda x: (0 if x.scheme_id.startswith("dataset-") else 1, -x.match_score))
    else:
        matched.sort(key=lambda x: x.match_score, reverse=True)
        needs_info.sort(key=lambda x: x.match_score, reverse=True)

    return matched, needs_info


def build_schemes_audio_summary(
    matched: list[SchemeCard],
    needs_info: list[SchemeCard] = None,
    language: str = "en",
) -> str:
    """
    Generate localized TTS summary paragraph in English, Hindi, or Tamil.
    """
    lang = language if language in ("en", "hi", "ta") else "en"
    total_matched = len(matched)
    top_3 = matched[:3]
    top_names = ", ".join(s.short_name or s.name for s in top_3)

    if lang == "hi":
        if total_matched > 0:
            return (
                f"बधाई हो! आपकी जानकारी के आधार पर {total_matched} सरकारी योजनाएं मिली हैं। "
                f"मुख्य योजनाएं हैं: {top_names}। "
                f"इनमें मिलने वाली राशि में राज्य सरकारें अतिरिक्त टॉप-अप देती हैं, इसलिए अंतिम राशि कार्यालय से पुष्टि करें। "
                f"किसी भी योजना का नाम बोलकर या कार्ड पर टैप करके पूरा विवरण सुनें।"
            )
        return "आपकी जानकारी के आधार पर अभी कोई सीधी योजना मैच नहीं हुई। कृपया नजदीकी सीएससी या ब्लॉक कार्यालय से संपर्क करें।"

    elif lang == "ta":
        if total_matched > 0:
            return (
                f"வாழ்த்துகள்! உங்கள் சுயவிவரத்தின்படி {total_matched} அரசு நலத்திட்டங்கள் கண்டறியப்பட்டுள்ளன. "
                f"முக்கிய திட்டங்கள்: {top_names}. "
                f"மாநில அரசுகள் கூடுதல் நிதி உதவி வழங்குவதால், சரியான தொகையை அரசு அலுவலகத்தில் உறுதிப்படுத்தவும். "
                f"ஒவ்வொரு திட்டத்தின் விவரங்களையும் நீங்கள் ஒலி வடிவில் கேட்கலாம்."
            )
        return "தங்கள் தகவல்களின் அடிப்படையில் திட்டங்கள் நேரடியாக பொருந்தவில்லை. கிராம சேவை மையத்தை அணுகவும்."

    # English default
    if total_matched > 0:
        return (
            f"Great news! I found {total_matched} government schemes matching your profile. "
            f"Top schemes include: {top_names}. "
            f"Please remember that state governments add extra top-ups, so confirm final amounts at your local office. "
            f"You can listen to full details for each scheme hands-free."
        )
    return "No exact schemes matched your current answers. Please consult your nearest Common Service Centre."


# Backward compatibility exports
SCHEMES = [
    {
        "id": s["id"],
        "name": s["translations"]["en"]["name"],
        "short_name": s.get("short_name"),
        "ministry": s.get("ministry"),
        "benefit_summary": s["translations"]["en"]["benefit_summary"],
        "eligibility_rules": s.get("eligibility_rules", {}),
        "application_steps": [s["translations"]["en"]["how_to_apply"]],
        "tags": [s.get("group_id", "all")],
    }
    for s in SCHEMES_CATALOGUE
]

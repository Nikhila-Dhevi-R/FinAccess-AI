"""Loader for the user-supplied government schemes CSV catalogue."""

import csv
import json
import os
import re
from pathlib import Path


DATASET_PATH = Path(
    os.getenv(
        "FINACCESS_SCHEMES_CSV",
        str(Path(__file__).resolve().parents[1] / "data" / "updated_data.csv"),
    )
)
TRANSLATIONS_PATH = DATASET_PATH.parent / "scheme_translations_ta.json"
TAMIL_CHAR_PATTERN = re.compile(r"[\u0B80-\u0BFF]")


def _usable_translation(value) -> bool:
    text = " ".join(value) if isinstance(value, list) else str(value or "")
    if not TAMIL_CHAR_PATTERN.search(text):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)

CATEGORY_TO_GROUP = {
    "agriculture": "farmers",
    "banking": "loans_and_business",
    "business & entrepreneurship": "loans_and_business",
    "education & learning": "girls_and_students",
    "financial services and insurance": "health_and_insurance",
    "health & wellness": "health_and_insurance",
    "housing & shelter": "subsidies",
    "it & communications": "subsidies",
    "law & justice": "subsidies",
    "public safety": "subsidies",
    "rural & environment": "subsidies",
    "science": "girls_and_students",
    "skills & employment": "daily_wage_workers",
    "social welfare & empowerment": "subsidies",
    "sports & culture": "girls_and_students",
    "transport & infrastructure": "subsidies",
    "travel & tourism": "subsidies",
    "utility & sanitation": "subsidies",
    "women and child": "women",
}

AUDIENCE_TERMS = {
    "farmer": ("farmer", "farmers", "farming", "agriculture", "agricultural", "kisan", "cultivator"),
    "worker": ("labour", "labor", "worker", "construction", "daily wage", "unorganised", "unorganized", "shramik", "mazdoor"),
    "student": ("student", "scholarship", "school", "college", "university", "education", "academic"),
    "woman": ("woman", "women", "girl", "girls", "mahila", "maternity", "pregnant", "mother"),
    "business": ("business", "entrepreneur", "enterprise", "msme", "industry", "artisan", "vendor", "shopkeeper", "trader"),
    "senior": ("senior citizen", "old age", "elderly", "aged person"),
    "poor_family": ("bpl", "ration card", "low income", "poor family", "poverty", "economically weaker"),
}

NEED_TERMS = {
    "pension": ("pension", "old age pension", "widow pension"),
    "loan": ("loan", "credit", "working capital", "finance"),
    "subsidy": ("subsidy", "subsidies", "grant", "incentive", "assistance"),
    "education": ("education", "school", "student", "scholarship", "training"),
    "health": ("health", "medical", "hospital", "treatment", "healthcare"),
    "insurance": ("insurance", "accident cover", "life cover"),
    "house": ("housing", "house", "shelter", "home"),
    "food": ("ration", "food", "nutrition", "meal"),
    "skills_jobs": ("employment", "job", "jobs", "skill", "vocational", "training"),
    "cash": ("cash", "financial assistance", "financial support", "payment", "benefit"),
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "scheme"


def _split_values(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;|]", _text(value)) if part.strip()]


def _split_documents(value: str) -> list[str]:
    raw = _text(value)
    if not raw:
        return []
    parts = re.split(r"\r?\n|(?<=[.!?])\s+(?=[A-Z0-9])", raw)
    cleaned = [re.sub(r"^[*•\-\s]+", "", part).strip() for part in parts]
    return [part for part in cleaned if part][:40]


def _group_for(categories: list[str]) -> str:
    for category in categories:
        group = CATEGORY_TO_GROUP.get(category.lower())
        if group:
            return group
    return "subsidies"


def _tags_for(text: str, table: dict[str, tuple[str, ...]]) -> list[str]:
    lower = text.lower()
    return [key for key, terms in table.items() if any(term in lower for term in terms)]


def _row_to_scheme(row: dict[str, str], index: int, seen_ids: dict[str, int]) -> dict:
    name = _text(row.get("scheme_name")) or f"Government Scheme {index}"
    source_slug = _text(row.get("slug")) or name
    base_id = f"dataset-{_slugify(source_slug)}"
    seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
    scheme_id = base_id if seen_ids[base_id] == 1 else f"{base_id}-{seen_ids[base_id]}"

    categories = _split_values(row.get("schemeCategory", ""))
    tags = _split_values(row.get("tags", ""))
    details = _text(row.get("details"))
    benefits = _text(row.get("benefits"))
    eligibility = _text(row.get("eligibility"))
    application = _text(row.get("application"))
    documents = _text(row.get("documents"))
    search_text = " ".join(
        value for value in (name, details, benefits, eligibility, application, documents, *categories, *tags) if value
    )
    audience_tags = _tags_for(search_text, AUDIENCE_TERMS)
    need_tags = _tags_for(search_text, NEED_TERMS)
    if not audience_tags:
        audience_tags = ["everyone"]
    if not need_tags:
        need_tags = ["cash"]

    ministry = f"{_text(row.get('level'))} Government" if _text(row.get("level")) else "Government Department"
    english_translation = {
        "name": name,
        "short_name": name[:120],
        "ministry": ministry,
        "benefit_summary": benefits or details or "See the official scheme details.",
        "who_can_get": eligibility or "See the scheme eligibility details.",
        "how_to_apply": application or "Visit the relevant government office or Common Service Centre (CSC).",
        "where_to_apply": "See the application instructions or contact the relevant government department.",
        "documents_required": _split_documents(documents) or ["Check the scheme application instructions."],
        "audio_text": f"{name}. {benefits or details or eligibility}",
    }

    tamil_translation = dict(english_translation)
    cached_translation = _TAMIL_TRANSLATIONS.get(scheme_id)
    if isinstance(cached_translation, dict):
        tamil_translation.update(
            {
                field: value
                for field, value in cached_translation.items()
                if not field.startswith("_") and _usable_translation(value)
            }
        )

    return {
        "id": scheme_id,
        "group_id": _group_for(categories),
        "name": name,
        "short_name": name[:120],
        "ministry": ministry,
        "helpline": "Contact the relevant department or Common Service Centre (CSC)",
        "website": "https://www.india.gov.in/",
        "source": "updated_data.csv",
        "source_category": categories,
        "source_level": _text(row.get("level")),
        "search_text": search_text,
        "eligibility_text": eligibility,
        "audience_tags": audience_tags,
        "need_tags": need_tags,
        "raw_tags": tags,
        "translations": {
            "en": english_translation,
            "hi": dict(english_translation),
            "ta": tamil_translation,
        },
    }


def load_uploaded_schemes(path: Path = DATASET_PATH) -> list[dict]:
    """Load and normalize the CSV without failing app startup when it is absent."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        seen_ids: dict[str, int] = {}
        return [_row_to_scheme(row, index, seen_ids) for index, row in enumerate(reader, start=1)]


def _load_tamil_translations(path: Path = TRANSLATIONS_PATH) -> dict:
    """Load generated Tamil text without making translation a runtime dependency."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


_TAMIL_TRANSLATIONS = _load_tamil_translations()
IMPORTED_SCHEMES_CATALOGUE = load_uploaded_schemes()

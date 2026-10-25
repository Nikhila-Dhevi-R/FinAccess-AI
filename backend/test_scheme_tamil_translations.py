import re
import csv
import json
import tempfile
from pathlib import Path

from services.imported_schemes import IMPORTED_SCHEMES_CATALOGUE
from services.scheme_service import _format_scheme_card


TAMIL = re.compile(r"[\u0B80-\u0BFF]")
TAMIL_FIELDS = (
    "name",
    "short_name",
    "ministry",
    "benefit_summary",
    "who_can_get",
    "how_to_apply",
    "where_to_apply",
    "documents_required",
    "audio_text",
)


def _as_text(value):
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def _has_tamil(value):
    return bool(TAMIL.search(_as_text(value)))


def test_every_imported_scheme_has_tamil_visible_fields():
    assert len(IMPORTED_SCHEMES_CATALOGUE) == 3400

    missing = []
    for scheme in IMPORTED_SCHEMES_CATALOGUE:
        tamil = scheme["translations"].get("ta", {})
        for field in TAMIL_FIELDS:
            value = tamil.get(field)
            if not value or not _has_tamil(value):
                missing.append((scheme["id"], field, value))

    assert not missing, f"Missing Tamil translation fields: {missing[:5]}"


def test_tamil_list_response_localizes_imported_scheme():
    raw_scheme = next(
        scheme for scheme in IMPORTED_SCHEMES_CATALOGUE
        if scheme["id"].startswith("dataset-")
    )

    english = _format_scheme_card(raw_scheme, language="en")
    tamil = _format_scheme_card(raw_scheme, language="ta")

    assert tamil.name != english.name
    assert tamil.benefit_summary != english.benefit_summary
    assert _has_tamil(tamil.name)
    assert _has_tamil(tamil.benefit_summary)
    assert _has_tamil(tamil.short_name)
    assert _has_tamil(tamil.ministry)


def test_tamil_match_response_localizes_imported_scheme(client):
    response = client.post(
        "/schemes/match?language=ta",
        json={
            "category": "other",
            "occupation": "fisher",
            "gender": "female",
            "age": 35,
            "has_bank_account": True,
            "has_ration_card": False,
        },
    )

    assert response.status_code == 200, response.text
    imported = [
        scheme for scheme in response.json()["matched_schemes"]
        if scheme["scheme_id"].startswith("dataset-")
    ]
    assert imported, "Expected the fisher profile to match imported schemes"
    assert any(
        _has_tamil(scheme["name"]) and _has_tamil(scheme["benefit_summary"])
        for scheme in imported
    )


def test_split_text_reassembles_long_text_without_loss():
    from scripts.generate_scheme_translations import split_text

    source = "First sentence has details. Second sentence has more details. Third sentence ends here."
    chunks = split_text(source, max_chars=28)

    assert chunks
    assert all(len(chunk) <= 28 for chunk in chunks)
    assert "".join(chunks) == source


def test_translation_preserves_official_tokens():
    from scripts.generate_scheme_translations import translate_text

    source = "BPL families receive ₹50,000. Apply at https://example.gov.in/PMAY-G."
    translated = translate_text(source, lambda _chunk: "தமிழ் உரை")

    assert "BPL" in translated
    assert "₹50,000" in translated
    assert "https://example.gov.in/PMAY-G" in translated


def test_generate_translations_preserves_duplicate_scheme_ids():
    from scripts.generate_scheme_translations import generate_scheme_translations

    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp_dir:
        tmp_path = Path(temp_dir)
        source = tmp_path / "schemes.csv"
        output = tmp_path / "scheme_translations_ta.json"
        fields = [
            "scheme_name", "slug", "details", "benefits", "eligibility",
            "application", "documents", "level", "schemeCategory", "tags",
        ]
        rows = [
            {
                "scheme_name": "Duplicate Scheme One",
                "slug": "duplicate-scheme",
                "details": "First details.",
                "benefits": "First benefit.",
                "eligibility": "First eligibility.",
                "application": "First application.",
                "documents": "Aadhaar Card",
                "level": "Central",
                "schemeCategory": "Agriculture",
                "tags": "farmer",
            },
            {
                "scheme_name": "Duplicate Scheme Two",
                "slug": "duplicate-scheme",
                "details": "Second details.",
                "benefits": "Second benefit.",
                "eligibility": "Second eligibility.",
                "application": "Second application.",
                "documents": "Bank account",
                "level": "State",
                "schemeCategory": "Education & Learning",
                "tags": "student",
            },
        ]
        with source.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        generate_scheme_translations(
            source,
            output,
            translate_fn=lambda text: re.sub(
                r"(__FINACCESS_TOKEN_\d+__)", r"\1 தமிழ் ", text
            ),
        )
        data = json.loads(output.read_text(encoding="utf-8"))

        assert set(data) == {"dataset-duplicate-scheme", "dataset-duplicate-scheme-2"}
        assert data["dataset-duplicate-scheme"]["name"]
        assert data["dataset-duplicate-scheme-2"]["name"]

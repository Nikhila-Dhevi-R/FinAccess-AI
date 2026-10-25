from services.imported_schemes import IMPORTED_SCHEMES_CATALOGUE


def test_uploaded_catalogue_is_loaded_and_normalized():
    assert len(IMPORTED_SCHEMES_CATALOGUE) == 3400
    ids = [scheme["id"] for scheme in IMPORTED_SCHEMES_CATALOGUE]
    assert len(ids) == len(set(ids))

    fisherman = next(
        scheme for scheme in IMPORTED_SCHEMES_CATALOGUE
        if "Fishermen" in scheme["name"] or "fishermen" in scheme["search_text"].lower()
    )
    assert fisherman["source"] == "updated_data.csv"
    assert fisherman["group_id"] in {
        "farmers",
        "daily_wage_workers",
        "girls_and_students",
        "elderly",
        "women",
        "loans_and_business",
        "subsidies",
        "health_and_insurance",
    }


def test_custom_category_uses_uploaded_scheme_text(client):
    response = client.post(
        "/schemes/match?language=en",
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
    names = [scheme["name"].lower() for scheme in response.json()["matched_schemes"]]
    assert "fisher" in names[0]
    assert any("fisher" in name for name in names)

def test_other_category_profile_is_accepted(client):
    response = client.post(
        "/schemes/match?language=en",
        json={
            "category": "other",
            "occupation": "street vendor",
            "gender": "female",
            "age": 35,
            "has_bank_account": False,
            "has_ration_card": False,
        },
    )

    assert response.status_code == 200, response.text
    profile = response.json()["profile"]
    assert profile["category"] == "other"
    assert profile["occupation"] == "street vendor"


"""
Finding schemes: search in English / Hindi / Tamil / Hinglish, 'who is it for' and 'what do you need' filters,
and ministry names in the customer's language.
"""

import pytest

from services.scheme_finder import search, filter_options, localize_ministry
from services.schemes_data import SCHEMES_CATALOGUE


def _top(query, n=5):
    return [sid for sid, _ in search(query)[:n]]


@pytest.mark.parametrize("query", ["old age pension", "बुढ़ापा पेंशन", "முதியோர் ஓய்வூதியம்", "budhapa pension"])
def test_pension_search_in_every_language(query):
    results = search(query)
    assert results, query
    top = [s for s in SCHEMES_CATALOGUE if s["id"] == results[0][0]][0]
    assert "pension" in (top["id"] + top.get("short_name", "") + top["translations"]["en"]["name"]).lower()


def test_typo_still_finds_scheme():
    assert search("pensoin")


def test_filters_have_labels_in_all_languages_and_counts():
    for lang in ("en", "hi", "ta"):
        opts = filter_options(lang)
        assert opts["audiences"] and opts["needs"]
        assert all(o["label"] and o["count"] >= 0 for o in opts["audiences"] + opts["needs"])
    hi = {o["id"]: o["label"] for o in filter_options("hi")["audiences"]}
    en = {o["id"]: o["label"] for o in filter_options("en")["audiences"]}
    assert hi["farmer"] != en["farmer"] and not hi["farmer"].isascii()


def test_ministry_is_localized():
    ministry = next(s["ministry"] for s in SCHEMES_CATALOGUE if s.get("ministry"))
    assert localize_ministry(ministry, "en") == ministry
    assert not localize_ministry(ministry, "hi").isascii()


def test_api_filters_and_search(client):
    r = client.get("/api/v1/schemes/filters", params={"language": "ta"})
    assert r.status_code == 200
    assert {"audiences", "needs"} <= set(r.json())

    farmers = client.get("/api/v1/schemes", params={"audience": "farmer", "language": "hi"}).json()
    assert farmers and all("farmer" in s["tags"] for s in farmers)

    both = client.get("/api/v1/schemes", params={"audience": "farmer", "need": "loan"}).json()
    assert all("farmer" in s["tags"] and "loan" in s["tags"] for s in both)

    found = client.get("/api/v1/schemes", params={"q": "पेंशन", "language": "hi"}).json()
    assert found and not found[0]["name"].isascii()

    # the plain category listing still works exactly as before
    groups = client.get("/api/v1/schemes/groups").json()
    assert client.get("/api/v1/schemes", params={"group": groups[0]["id"]}).json()

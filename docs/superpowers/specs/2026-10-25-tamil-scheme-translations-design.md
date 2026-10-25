# Tamil Government Scheme Translations Design

## Intent

When a user selects Tamil, every government scheme returned by the catalogue must display Tamil content instead of the English fallback. This applies to both the voice-match results and the browse/search results, including the scheme title, badge, ministry, benefit, eligibility, application guidance, documents, and spoken summary.

## Goals

- Provide stored Tamil translations for every imported scheme in `backend/data/updated_data.csv`.
- Keep runtime scheme responses local and deterministic after generation; the app must not depend on an online translation service for normal use.
- Preserve the existing English and curated Hindi/Tamil catalogue entries.
- Prevent a partial translation cache from silently returning English for Tamil requests.

## Non-goals

- Re-translate the existing curated schemes that already contain Tamil content.
- Change scheme matching, ranking, filtering, or the eight catalogue groups.
- Add a runtime translation API or expose source dataset text to the browser.

## Chosen approach

Use a one-time generation step to translate the imported dataset into a checked-in local cache keyed by each stable `dataset-*` scheme ID. The loader will merge the cached Tamil fields into each imported scheme before the existing localized response formatter runs. Runtime requests continue to use the existing `language=ta` contract and do not make network calls.

The generated cache will include the fields visible or spoken by the scheme UI: `name`, `short_name`, `ministry`, `benefit_summary`, `who_can_get`, `how_to_apply`, `where_to_apply`, `documents_required`, and `audio_text`. English text embedded in official names, acronyms, URLs, currencies, and identifiers may remain unchanged when that is the correct Tamil presentation.

## Alternatives considered

- Runtime online translation: rejected because it adds network latency, service availability, credentials/rate-limit concerns, and unpredictable results to a local accessibility flow.
- A Tamil glossary or transliteration-only fallback: rejected because it cannot translate the full descriptions and would leave many schemes visibly English.

## Validation

- Add a backend regression test that selects an imported scheme and requests Tamil through both the list and match paths, asserting that the returned visible text is not the English source fallback and contains Tamil script.
- Add a catalogue validation test covering every imported scheme and every required Tamil field, while allowing approved Latin tokens such as acronyms, URLs, currency symbols, and numeric values.
- Run the existing backend test suite and frontend scheme tests.

## Files expected to change

- `backend/scripts/generate_scheme_translations.py`: one-time generator for the local Tamil cache.
- `backend/data/scheme_translations_ta.json`: generated Tamil translations keyed by stable scheme ID.
- `backend/services/imported_schemes.py`: load and merge the generated Tamil cache.
- `backend/services/scheme_service.py`: use localized short name/ministry values where the response contract currently uses raw English metadata.
- `backend/test_uploaded_scheme_catalogue.py` or a focused new backend test: regression and completeness coverage.


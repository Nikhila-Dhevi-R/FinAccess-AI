# Tamil Government Scheme Translations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return Tamil text for every imported government scheme whenever the scheme language is `ta`, in both browse/search and profile-match results.

**Architecture:** Keep the existing English CSV as the source of truth and add a generated JSON translation cache keyed by the loader's stable `dataset-*` IDs. The backend merges that cache into imported scheme records before the existing localized `SchemeCard` formatter runs; normal application requests never call a translation service.

**Tech Stack:** Python 3.11, FastAPI, pytest, `urllib`/JSON for the one-time translation generator, React/Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-25-tamil-scheme-translations-design.md`

## Global Constraints

- Use `backend/data/updated_data.csv` as the source catalogue and preserve its scheme IDs, matching, ranking, and filters.
- Store generated Tamil translations in `backend/data/scheme_translations_ta.json`, keyed by stable `dataset-*` scheme IDs.
- Runtime requests must be offline-safe: no translation network calls from FastAPI request handlers or React code.
- Translate `name`, `short_name`, `ministry`, `benefit_summary`, `who_can_get`, `how_to_apply`, `where_to_apply`, `documents_required`, and `audio_text` for imported schemes.
- Preserve official acronyms, URLs, currency symbols, numeric amounts, and government identifiers when translating.
- Keep curated schemes and English/Hindi responses unchanged.

## Review Focus

- Long imported descriptions must be chunked and recombined without dropping text; test a multi-sentence field.
- Duplicate CSV slugs must map to distinct stable IDs and distinct cached translations; test the `-2` suffix case.
- Numeric amounts, ₹ values, acronyms, URLs, and identifiers must survive translation; test a source string containing all of them.
- Empty source fields and generated fallback text must still produce valid Tamil-visible content; test the loader's default field values.
- Both `/api/v1/schemes?language=ta` and `/api/v1/schemes/match?language=ta` must return Tamil for imported schemes while `language=en` remains English; cover both response paths.

---

### Task 1: Add the failing Tamil catalogue regression tests

**Files:**
- Create: `backend/test_scheme_tamil_translations.py`
- Reference: `backend/services/imported_schemes.py`, `backend/services/scheme_service.py`, `backend/routers/schemes.py`

**Interfaces:**
- Consumes: `load_uploaded_schemes`, `_format_scheme_card`, and the existing FastAPI test client.
- Produces: assertions that the generated cache must satisfy for every imported scheme and both API response paths.

- [ ] **Step 1: Write the failing completeness test**

  Add `test_every_imported_scheme_has_tamil_visible_fields()` that loads the imported catalogue, requires the expected 3,400-row dataset, checks the nine required translated fields, and asserts each non-empty Tamil field contains at least one Tamil Unicode character unless it is an approved URL/acronym-only value.

- [ ] **Step 2: Write the failing list-response test**

  Add `test_tamil_list_response_localizes_imported_scheme()` that formats a known `dataset-*` scheme in Tamil and English and asserts the Tamil name/benefit differ from the English source and contain Tamil script, while the English response remains unchanged.

- [ ] **Step 3: Write the failing match-response test**

  Add `test_tamil_match_response_localizes_imported_scheme()` using the existing `TestClient` and a profile that matches an imported scheme; request `language=ta` and assert at least one returned imported card has Tamil name and benefit text.

- [ ] **Step 4: Run the focused tests and verify the expected failure**

  Run from `backend`:

  ```text
  ..\.venv\Scripts\python.exe -m pytest test_scheme_tamil_translations.py -q
  ```

  Expected: FAIL because imported `ta` translations currently copy English.

### Task 2: Implement the translation-cache generator and generate Tamil data

**Files:**
- Create: `backend/scripts/generate_scheme_translations.py`
- Create: `backend/data/scheme_translations_ta.json`
- Test: `backend/test_scheme_tamil_translations.py`

**Interfaces:**
- Consumes: the CSV rows and stable `dataset-*` IDs produced by the existing loader.
- Produces: `generate_scheme_translations(source: Path, output: Path) -> None`, a resumable JSON cache, and complete Tamil field records.

- [ ] **Step 1: Add generator helper tests**

  Add tests for sentence-aware chunking below the provider limit, response assembly, duplicate-ID preservation, and preservation of URLs/numbers/acronyms in the generated record.

- [ ] **Step 2: Implement the one-time generator**

  Implement a command-line script using an injected translation request function and the public one-time Google Translate endpoint (`translate.googleapis.com`, `sl=en`, `tl=ta`). Cache source-text hashes so repeated placeholders are translated once, split long fields into sentence-aware chunks, retry transient failures with bounded backoff, and write atomically to `scheme_translations_ta.json`.

- [ ] **Step 3: Generate the complete cache**

  Run:

  ```text
  ..\.venv\Scripts\python.exe scripts\generate_scheme_translations.py --source data\updated_data.csv --output data\scheme_translations_ta.json
  ```

  Expected: one record for every imported `dataset-*` ID and all required fields present.

### Task 3: Merge cached Tamil fields into imported schemes

**Files:**
- Modify: `backend/services/imported_schemes.py`
- Modify: `backend/services/scheme_service.py`
- Test: `backend/test_scheme_tamil_translations.py`

**Interfaces:**
- Consumes: `scheme_translations_ta.json` keyed by `scheme_id`.
- Produces: imported scheme dictionaries whose `translations.ta` contains the generated fields; localized cards whose `short_name` and `ministry` are also Tamil when available.

- [ ] **Step 1: Load the cache without affecting English/Hindi**

  Add a read-only cache loader and merge only the `ta` translation record into each imported scheme after its stable ID is computed. Preserve the current English source and Hindi fallback behavior.

- [ ] **Step 2: Localize raw metadata used by cards**

  Update `_format_scheme_card` so `short_name` uses the selected translation when present and `ministry` uses the translated field before the existing curated ministry map fallback. Keep English and Hindi output unchanged for records without new Tamil data.

- [ ] **Step 3: Run the focused tests and verify they pass**

  Run:

  ```text
  ..\.venv\Scripts\python.exe -m pytest test_scheme_tamil_translations.py -q
  ```

  Expected: all focused tests pass, including the completeness check over every imported scheme.

### Task 4: Verify the full application behavior

**Files:**
- Modify: none unless verification exposes a regression.
- Test: existing backend and frontend test suites.

**Interfaces:**
- Consumes: the generated cache and localized API response contract.
- Produces: verified backend and frontend behavior with no regression in existing scheme matching.

- [ ] **Step 1: Run the full backend suite**

  Run from `backend`:

  ```text
  ..\.venv\Scripts\python.exe -m pytest -q
  ```

  Expected: no failures; report any pre-existing environmental failure separately.

- [ ] **Step 2: Run the frontend scheme tests**

  Run from `frontend`:

  ```text
  npm run test -- --run src/pages/Schemes.test.jsx
  ```

  Expected: all scheme UI tests pass.

- [ ] **Step 3: Build the frontend**

  Run:

  ```text
  npm run build
  ```

  Expected: Vite exits with code 0.

- [ ] **Step 4: Verify live API output**

  With the local backend running, request Tamil and English list/match results and confirm imported cards contain Tamil script only for `language=ta`, while English remains unchanged for `language=en`.


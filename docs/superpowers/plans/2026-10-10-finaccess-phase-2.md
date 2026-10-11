# FinAccess AI Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden browser speech and shared state, isolate backend artifacts, add focused frontend regression tests, and reduce bundle/lint debt without changing product behavior.

**Architecture:** Retain public component and hook APIs while introducing a root session context, guarded browser-speech lifecycle, small test harness, and route-level lazy imports. Backend tests redirect all generated files to pytest temporary storage; production paths and legacy artifacts remain untouched.

**Tech Stack:** React 19, Vite 8, Vitest, React Testing Library, FastAPI, pytest, SQLite

**Spec:** `docs/superpowers/specs/2026-10-10-finaccess-phase-2-design.md`

## Global Constraints

- Preserve every Phase 1 state-transition, nonce, skip, finalization, and anonymous-fraud invariant.
- Preserve English/Hindi/Tamil browser STT and TTS with existing locale mapping.
- Do not add authentication, LLM/RAG, external speech providers, data migration, or major redesigns.
- Never move, delete, overwrite, or inspect sensitive contents of legacy storage.
- Use test-first changes and keep refactors limited to responsibilities directly touched by Phase 2.

## Review Focus

- A delayed microphone permission result after Stop/unmount must not restart recognition or update state.
- Repeated nonce-submit clicks must create one API request and one success callback.
- A failed finalize response must never expose a PDF download link.
- Language changes must update multiple mounted consumers while backend synchronization is offline.
- Backend tests must leave canonical upload directory metadata unchanged.

---

### Task 1: Frontend Test Harness and Speech Lifecycle

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.js`
- Create: `frontend/src/test/setup.js`, `frontend/src/hooks/useSpeech.test.jsx`
- Modify: `frontend/src/hooks/useSpeech.js`

**Interfaces:**
- Consumes: current `useSpeech(language)` return object.
- Produces: the same public API with single-settlement and unmount-safe semantics.

- [ ] Add the minimal Vitest/jsdom/RTL dependencies and `npm test` script.
- [ ] Write failing hook tests for single resolution, Stop/onend deduplication, permission errors, rapid restart, unmount cleanup, and TTS cancellation.
- [ ] Run the focused test and confirm the new cases fail for the expected lifecycle gaps.
- [ ] Add mounted and operation guards without changing locale mapping or public return values.
- [ ] Run `npm test -- useSpeech` and confirm all hook tests pass.

### Task 2: Challenge and Form Flow Regression Tests

**Files:**
- Create: `frontend/src/components/ChallengePrompt.test.jsx`
- Create: `frontend/src/pages/FormFill.test.jsx`
- Modify as needed: `frontend/src/components/ChallengePrompt.jsx`, `frontend/src/pages/FormFill.jsx`
- Create if useful: `frontend/src/pages/formFillHelpers.js`

**Interfaces:**
- Consumes: Phase 1 API client functions and existing component props.
- Produces: unchanged user flow with explicit in-flight protection and testable pure helpers.

- [ ] Write failing tests for nonce mismatch, one successful callback, duplicate-submit suppression, invalid-answer rejection, skip advancement, finalize failure, and backend `pdf_url` usage.
- [ ] Run the two test files and record expected failures.
- [ ] Make only the minimal guard/helper changes required by the tests.
- [ ] Re-run the focused tests and confirm they pass.

### Task 3: Fraud and Scheme Contract Tests

**Files:**
- Create: `frontend/src/pages/FraudCheck.test.jsx`, `frontend/src/pages/Schemes.test.jsx`
- Modify as needed: `frontend/src/pages/FraudCheck.jsx`, `frontend/src/pages/Schemes.jsx`

**Interfaces:**
- Produces: fraud payloads with `session_id: null` when anonymous and scheme-match payloads using `has_ration_card`.

- [ ] Write failing interaction tests that assert the exact mocked API payload keys/values.
- [ ] Run focused tests and confirm contract failures where present.
- [ ] Apply minimal payload fixes while preserving UI and multilingual copy.
- [ ] Re-run focused tests and confirm they pass.

### Task 4: Shared Session Provider

**Files:**
- Modify: `frontend/src/hooks/useSession.js`, `frontend/src/main.jsx`
- Create: `frontend/src/hooks/useSession.test.jsx`
- Modify if required: `frontend/src/api/client.js`

**Interfaces:**
- Produces: `SessionProvider` and the existing `useSession()` values/actions.

- [ ] Write failing tests for refresh hydration, multi-consumer language propagation, session creation persistence, and resilient best-effort backend language update.
- [ ] Run the focused tests and confirm independent hook instances fail synchronization.
- [ ] Implement context ownership and wrap the application root.
- [ ] Re-run session and affected component tests.

### Task 5: Backend Upload/PDF Test Isolation

**Files:**
- Modify: `backend/conftest.py`
- Modify/add focused assertions in existing backend upload/finalization tests.

**Interfaces:**
- Produces: a pytest temporary upload directory available to all backend tests; production settings remain unchanged outside tests.

- [ ] Capture canonical upload metadata and write a failing isolation assertion.
- [ ] Patch every runtime settings reference used by upload and PDF paths via a session-scoped temporary directory fixture.
- [ ] Run upload/finalization tests, confirm outputs exist under pytest temp storage, and confirm canonical metadata is unchanged.
- [ ] Run the full backend suite.

### Task 6: Errors, Lint Cleanup, and Low-Risk Extraction

**Files:**
- Modify: `frontend/src/api/client.js`, `frontend/src/pages/Guidance.jsx`, `frontend/src/pages/FraudCheck.jsx`
- Modify warning locations in `frontend/src/components`, `frontend/src/hooks`, and `frontend/src/pages`
- Create only if reused: `frontend/src/components/StatusNotice.jsx` or `frontend/src/utils/apiError.js`

**Interfaces:**
- Produces: consistent user-safe error categories and explicitly labelled offline/local fallbacks.

- [ ] Add focused fallback/error assertions to existing frontend tests.
- [ ] Normalize timeout/network/4xx/5xx errors and label fallback results without representing them as backend success.
- [ ] Remove unused code and correct hook dependency/stability warnings individually.
- [ ] Run `npx oxlint src` and require 0 errors/0 warnings unless a documented safety exception remains.

### Task 7: Route Splitting and Documentation

**Files:**
- Modify: `frontend/src/App.jsx`, `frontend/README.md`

**Interfaces:**
- Produces: lazy page chunks behind an accessible route loading fallback.

- [ ] Replace eager page imports with `lazy()` while leaving routes unchanged; add one `Suspense` status fallback.
- [ ] Replace generic Vite documentation with practical FinAccess architecture, setup, storage, environment, voice, limitations, and test instructions.
- [ ] Run the production build and record every important emitted chunk size.

### Task 8: Storage Inventory and Full Verification

**Files:**
- No storage mutation; add a read-only diagnostic only if it provides value beyond existing configuration/tests.

**Interfaces:**
- Consumes: canonical paths from `backend/config.py`.
- Produces: metadata-only inventory for the final Codex report.

- [ ] Record canonical and legacy database/upload existence, sizes, and file counts without reading rows.
- [ ] Run `python -m pytest -q`, `npm test`, `npx oxlint src`, and `npm run build` from their correct directories.
- [ ] Compare production upload metadata before/after tests and confirm no Phase 1 regression.
- [ ] Review the final diff for scope, sensitive output, generated artifacts, and every requested final-report section.


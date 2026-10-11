# FinAccess AI Phase 2 Design

## Goal

Improve browser reliability, test isolation, cleanup, and maintainability without changing FinAccess AI's intended product behavior or weakening any Phase 1 correctness invariant.

## Constraints

- Preserve React + FastAPI + SQLite and English/Hindi/Tamil voice UX.
- Preserve Phase 1 nonce, skip, finalization, anonymous fraud, and storage-path behavior.
- Do not add authentication, external speech providers, LLM/RAG, data migration, deployment infrastructure, or a major redesign.
- Do not move, modify, or delete legacy databases and upload directories.

## Architecture

### Speech lifecycle

Keep the existing `useSpeech(language)` API. Add a mounted guard and operation identity checks around every asynchronous recognition and synthesis callback. A new recognition cancels active TTS, only one recognition promise may be active, Stop settles that operation once, and unmount invalidates callbacks, aborts recognition, resolves the pending promise once, cancels TTS, and performs no React state update.

### Frontend tests

Add Vitest, jsdom, React Testing Library, and jest-dom with one shared setup module. Mock browser speech APIs and API modules; test observable behavior rather than real microphone hardware. Focus only on `useSpeech`, `ChallengePrompt`, `FormFill`, `FraudCheck`, and `Schemes` requirements.

### Shared session state

Move session ownership into a root `SessionProvider`; retain `useSession()` for consumers. Initialize once from the existing session-storage keys, persist changes, and make language changes immediately visible to all consumers. Backend language synchronization is best-effort and must not roll back usable local state when unavailable.

### Backend test isolation

Use a session-scoped pytest temporary upload directory. Patch the settings objects used by forms and application tests before clients exercise upload/finalization paths. Production defaults remain unchanged, and pytest cleanup removes generated test artifacts.

### Page structure and errors

Extract only pure FormFill helpers/constants needed for focused tests and readability. Add a small normalized frontend API-error utility and a reusable status notice only where it reduces duplicated behavior. Guidance and Fraud local fallbacks remain available but are visibly labelled as local/offline guidance, never as successful backend responses.

### Delivery and loading

Lazy-load each page module with React `lazy` and wrap routes in one accessible `Suspense` fallback. Resolve lint warnings through unused-code removal, stable callbacks, and correct dependencies. Replace the generic frontend README with practical project setup documentation. Legacy storage inspection is metadata-only; a diagnostic script is unnecessary unless manual inspection proves otherwise.

## Verification

- Backend: `python -m pytest -q`
- Frontend: `npm test`
- Lint: `npx oxlint src`
- Build: `npm run build`
- Compare canonical production upload-directory metadata before and after backend tests.
- Confirm Phase 1 final nonce/finalize regression tests remain green.


# SMS OTP Form Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one Twilio Verify SMS authentication step before form upload while preserving the existing randomized phrase challenge throughout form filling.

**Architecture:** Add a session-bound backend OTP service and `/api/v1/auth` router. The server stores only a Twilio verification reference and a short-lived verified-session marker, and the form-upload endpoint rejects unverified sessions before saving or processing a file. Add a focused `PhoneVerify` UI phase inside `FormFill`; after verification the existing upload, question, and randomized challenge phases continue unchanged.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic Settings, Twilio Verify Python SDK, pytest, React 19, Axios, Vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-12-sms-otp-form-gate-design.md`

## Global Constraints

- SMS verification occurs once before the first form upload for the current session.
- No OTP after individual questions, for sensitive fields, or during final submission.
- The existing randomized phrase/digit challenge remains the authority for field confirmation and final submission.
- Only `channel="sms"` is supported; do not port the archive's voice fallback, trusted-device cookie, or `OtpConfirmationModal`.
- Real Twilio credentials are written only to ignored `backend/.env`; tracked environment files contain placeholders only.
- The server must reject an unverified upload before saving the file or starting OCR.
- OTPs, Twilio auth tokens, verification SIDs, and full phone numbers must not be returned to the browser or written to audit payloads.
- Tests must mock Twilio and must never send a real SMS.

## Review Focus

- Invalid or ambiguously formatted Indian phone numbers must be rejected before delivery; test in Task 2.
- An OTP ID or code from another session must not verify the current session; test in Task 3.
- Missing or malformed Twilio configuration must fail closed without exposing provider details; test in Task 2.
- Expired, replayed, and over-attempted challenges must remain rejected; test in Task 3.
- An unverified upload must fail before file persistence/OCR while a verified upload succeeds; test in Task 4.

---

### Task 1: Add OTP settings, persistence, and dependency boundaries

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/models.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Test: `backend/test_sms_auth.py`

**Interfaces:**
- Produces `Settings` values for `MFA_REQUIRED`, `OTP_PROVIDER`, OTP limits, `OTP_DEFAULT_COUNTRY_CODE`, `MFA_SESSION_TTL_MINUTES`, and the three Twilio credentials.
- Produces `OtpChannel.SMS`, `PhoneOtp`, and `EventType.OTP_SENT`, `OTP_VERIFIED`, and `OTP_REJECTED`.
- `PhoneOtp` stores `session_id`, normalized phone, `verification_sid`, issued/expiry timestamps, attempt count, and consumed state; it never stores the OTP.

- [ ] **Step 1: Write the failing persistence/config tests**

  Add tests that import the settings and model metadata, assert the SMS provider defaults are safe for tests, and assert the `PhoneOtp` columns and SMS audit event names exist.

- [ ] **Step 2: Run the focused tests to verify they fail**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py -q`

  Expected: FAIL because the OTP settings, enum values, and model are not yet defined.

- [ ] **Step 3: Implement the configuration and model additions**

  Add `OTP_PROVIDER="twilio"`, default `MFA_REQUIRED=False` for existing test/dev sessions, the explicit MFA limits, `twilio` to `backend/requirements.txt`, the new SQLAlchemy table and enum values, and placeholder keys to `.env.example`. The ignored runtime `.env` enables `MFA_REQUIRED=true`. Keep `Base.metadata.create_all` compatibility for local SQLite.

- [ ] **Step 4: Run the focused tests to verify they pass**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py -q`

  Expected: PASS for the configuration and metadata checks.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/config.py backend/models.py backend/requirements.txt backend/.env.example backend/test_sms_auth.py
  git commit -m "feat: add sms otp persistence settings"
  ```

### Task 2: Implement the Twilio Verify and OTP lifecycle services

**Files:**
- Create: `backend/services/twilio_verify_service.py`
- Create: `backend/services/otp_service.py`
- Modify: `backend/test_sms_auth.py`

**Interfaces:**
- `normalize_phone(raw: str, default_country_code: str | None = None) -> str | None`
- `mask_phone(phone: str) -> str`
- `send_verification(phone: str, channel: str = "sms") -> tuple[str, str]`
- `check_verification(code: str, verification_sid: str, phone: str | None = None) -> bool`
- `send_otp(db, session, raw_phone: str, language: str = "en") -> tuple[PhoneOtp, str]`
- `verify_otp(db, session, otp_id: str, code: str) -> User`
- `is_session_verified(session: UserSession | None) -> bool`
- `OtpError(code, message, status_code=400, retry_after=None)` for stable recoverable failures.

- [ ] **Step 1: Write failing service tests**

  Add a mock Twilio handler and tests for `+91` normalization, invalid numbers, fail-closed SID validation, exact Verify send/check parameters, masked phone output, no code/SID leakage, and successful session verification.

- [ ] **Step 2: Run the service tests to verify they fail**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py -q`

  Expected: FAIL because the service modules and interfaces do not exist.

- [ ] **Step 3: Implement the Twilio boundary**

  Build the client from settings, call `verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(to=phone, channel="sms")`, and call `verification_checks.create(code=code, verification_sid=verification_sid)`. Map provider failures to stable `OtpError` codes and expose a mock hook for tests.

- [ ] **Step 4: Implement the OTP lifecycle**

  Normalize the submitted phone, enforce resend/hourly/session limits, persist only the verification SID, and on successful verification consume the request, link/create the existing `User`, and write the short-lived session marker. Do not log the code, SID, or full phone.

- [ ] **Step 5: Run the service tests to verify they pass**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py -q`

  Expected: PASS for all service tests.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/services/twilio_verify_service.py backend/services/otp_service.py backend/test_sms_auth.py
  git commit -m "feat: add twilio verify sms service"
  ```

### Task 3: Expose session-bound SMS authentication endpoints

**Files:**
- Modify: `backend/schemas.py`
- Create: `backend/routers/auth.py`
- Modify: `backend/main.py`
- Modify: `backend/test_sms_auth.py`

**Interfaces:**
- `POST /api/v1/auth/otp/send` accepts `{session_id, phone, language}` and returns `{otp_id, masked_phone, code_length, expires_in_seconds, resend_after_seconds}`.
- `POST /api/v1/auth/otp/verify` accepts `{session_id, otp_id, code}` and returns `{session_id, verified, masked_phone}`.
- `GET /api/v1/auth/status/{session_id}` returns `{session_id, verified, masked_phone}`.

- [ ] **Step 1: Write failing API tests**

  Add tests for successful send/status/verify, wrong code, expired/replayed request, cross-session rejection, resend limits, and response inspection proving no OTP, Twilio SID, auth token, or full phone is returned.

- [ ] **Step 2: Run the API tests to verify they fail**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py -q`

  Expected: FAIL because the schemas and router are not registered.

- [ ] **Step 3: Implement schemas and router**

  Resolve sessions server-side, convert `OtpError` into structured `detail.code`, `detail.message`, and optional `retry_after`, and register the router under both `/api/v1` and the existing backward-compatible root routing convention.

- [ ] **Step 4: Run the API tests to verify they pass**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py -q`

  Expected: PASS for the complete endpoint contract.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/schemas.py backend/routers/auth.py backend/main.py backend/test_sms_auth.py
  git commit -m "feat: expose session sms otp api"
  ```

### Task 4: Enforce the verified-session gate at form upload

**Files:**
- Modify: `backend/routers/forms.py`
- Modify: `backend/conftest.py`
- Test: `backend/test_sms_auth.py`

**Interfaces:**
- `upload_form` checks `settings.MFA_REQUIRED` and `otp_service.is_session_verified(session)` before file creation or OCR.
- Unverified requests return HTTP 403 with `detail.code == "form_auth_required"`.

- [ ] **Step 1: Write failing upload-gate tests**

  Add one test proving an unverified session gets 403 and the upload directory has no new file, and one proving a mocked verified session can upload normally. Add a regression assertion that field answer handling still returns the randomized challenge nonce after a verified upload.

- [ ] **Step 2: Run the gate tests to verify they fail**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py -q`

  Expected: FAIL because uploads currently proceed without checking SMS verification.

- [ ] **Step 3: Add the pre-persistence guard**

  Resolve the session, reject before opening/saving the `UploadFile`, and leave OCR, form creation, field navigation, and challenge nonce logic unchanged. Add an autouse test fixture that sets the shared settings object's `MFA_REQUIRED=False` for unrelated legacy tests; the dedicated gate tests override it to `True`.

- [ ] **Step 4: Run the gate and regression tests**

  Run: `& '.\\.venv\\Scripts\\python.exe' -m pytest backend/test_sms_auth.py backend/test_form_navigation.py backend/test_phase1_regressions.py -q`

  Expected: PASS, including the existing randomized challenge behavior.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/routers/forms.py backend/conftest.py backend/test_sms_auth.py
  git commit -m "feat: require sms verification before form upload"
  ```

### Task 5: Add the frontend SMS verification component and API client

**Files:**
- Modify: `frontend/src/api/client.js`
- Create: `frontend/src/components/PhoneVerify.jsx`
- Create: `frontend/src/components/PhoneVerify.test.jsx`

**Interfaces:**
- `sendOtp(sessionId, phone, language) -> Promise<OtpSendResponse>`
- `verifyOtp(sessionId, otpId, code) -> Promise<MfaStatusResponse>`
- `getOtpStatus(sessionId) -> Promise<MfaStatusResponse>`
- `PhoneVerify({ sessionId, language, onVerified, onError })` renders phone entry, code entry, resend countdown, error, and verified states.

- [ ] **Step 1: Write failing component tests**

  Mock the API functions and speech hook. Test that the component requests SMS with the session ID, masks the destination, accepts numeric six-digit entry with `autocomplete="one-time-code"`, calls verify once, displays recoverable provider errors, and invokes `onVerified` only after a successful response.

- [ ] **Step 2: Run the component tests to verify they fail**

  Run: `npm test -- --run src/components/PhoneVerify.test.jsx`

  Expected: FAIL because the client functions and component do not exist.

- [ ] **Step 3: Implement the client functions and component**

  Keep provider details out of the browser. Use the stable error codes from the API, disable buttons during requests, enforce the server-provided code length, and keep resend/change-number behavior inside this component.

- [ ] **Step 4: Run the component tests to verify they pass**

  Run: `npm test -- --run src/components/PhoneVerify.test.jsx`

  Expected: PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/api/client.js frontend/src/components/PhoneVerify.jsx frontend/src/components/PhoneVerify.test.jsx
  git commit -m "feat: add sms phone verification ui"
  ```

### Task 6: Put the SMS gate before the FormFill upload phase

**Files:**
- Modify: `frontend/src/pages/FormFill.jsx`
- Create or modify: `frontend/src/pages/FormFill.test.jsx`

**Interfaces:**
- Add `verify-phone` to the existing phase state.
- Session preparation calls `getOtpStatus(sessionId)` before setting `phase="upload"`.
- Successful `PhoneVerify.onVerified` transitions to `upload`; `handleFile` remains the only upload entry point.

- [ ] **Step 1: Write failing FormFill phase tests**

  Mock session creation/status, render FormFill, assert an unverified session renders `PhoneVerify` and no form-upload controls, assert a verified session renders the upload phase, and assert the post-upload flow still renders the existing field challenge component rather than an OTP modal.

- [ ] **Step 2: Run the phase tests to verify they fail**

  Run: `npm test -- --run src/pages/FormFill.test.jsx`

  Expected: FAIL because FormFill currently transitions directly from session creation to upload.

- [ ] **Step 3: Integrate `PhoneVerify` without changing post-upload phases**

  Add the status check after session creation, render the verification phase before upload, require an effective verified session in `handleFile`, and leave `asking`, `confirming`, `field-challenge`, `final-challenge`, `ChallengePrompt`, and confirmation nonce calls unchanged. Do not import or render `OtpConfirmationModal`.

- [ ] **Step 4: Run the phase tests and existing frontend tests**

  Run: `npm test -- --run src/pages/FormFill.test.jsx src/components/ChallengePrompt.test.jsx`

  Expected: PASS, with the randomized phrase tests still green.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/pages/FormFill.jsx frontend/src/pages/FormFill.test.jsx
  git commit -m "feat: gate form fill behind sms verification"
  ```

### Task 7: Configure local credentials safely and run the full verification suite

**Files:**
- Modify local ignored file: `backend/.env`
- Verify tracked file: `backend/.env.example`
- Verify: all backend and frontend test/build/lint outputs

- [ ] **Step 1: Add the supplied credentials only to `backend/.env`**

  Set `MFA_REQUIRED=true`, `OTP_PROVIDER=twilio`, and the three supplied Twilio values. Confirm `git status --short` does not list `backend/.env`; never print the values.

- [ ] **Step 2: Run the full backend suite with Twilio mocked**

  Run: `$env:DEBUG='false'; & '.\\.venv\\Scripts\\python.exe' -m pytest backend -q`

  Expected: all backend tests pass; no test sends a real SMS.

- [ ] **Step 3: Run the full frontend suite, build, and lint**

  Run from `frontend`:

  ```bash
  npm test -- --run
  npm run build
  npm run lint
  ```

  Expected: tests and build exit 0; lint has no errors. Existing warnings may remain documented.

- [ ] **Step 4: Check the final diff and secret boundary**

  Run: `git diff --check`, `git status --short`, and `git diff --stat`.

  Expected: only intended tracked source/tests/docs are listed; `backend/.env` and OTP values are absent from the diff.

- [ ] **Step 5: Commit the final configuration/documentation adjustments**

  ```bash
  git add backend/.env.example
  git commit -m "chore: finalize sms otp environment defaults"
  ```

  If `.env.example` has no changes after Task 1, skip this commit. Never stage `backend/.env`.


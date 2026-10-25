# SMS OTP Gate Before Form Filling

## Problem

The form-filling workflow currently starts after session creation and allows the user to upload a form immediately. The attached previous FinAccess version contains a Twilio Verify phone-verification flow, but it also contains a separate OTP modal used after sensitive fields and during final submission. The requested behavior is narrower: verify the user's mobile number once before form filling, then keep the existing randomized phrase challenge for form answers and submission.

## Goals

- Verify a user's Indian mobile number by SMS through Twilio Verify before the first form upload.
- Keep the verification bound to the current server session and expire it after a configurable session lifetime.
- Prevent form uploads through the API until the session has passed SMS verification.
- Preserve the existing randomized phrase challenge for field confirmation and final submission.
- Keep all existing non-form workflows unchanged.
- Keep Twilio credentials in the ignored backend environment file; never return them, the OTP, or the Twilio verification SID to the browser.

## Non-goals

- No OTP after individual questions.
- No OTP for sensitive fields, field edits, or final submission.
- No replacement of the randomized phrase challenge.
- No voice-call OTP fallback, trusted-device cookie, or changes to the landing, schemes, guidance, or fraud workflows.
- No client-side-only authentication that could be bypassed by calling the upload API directly.

## Reference findings

The attached archive contains `services/twilio_verify_service.py`, `services/otp_service.py`, `routers/auth.py`, and `components/PhoneVerify.jsx`. Its Twilio Verify integration correctly sends through `verify.v2.services(VA...).verifications.create(to=..., channel="sms")` and checks with the server-held verification reference. The same archive also contains `OtpConfirmationModal.jsx` and `confirmation_otp_service.py`; those are intentionally excluded because they introduce the after-question OTP behavior the request forbids.

The current app creates sessions in `routers/sessions.py`, starts form filling in `pages/FormFill.jsx`, and uploads through `routers/forms.py`. The current randomized phrase flow is implemented by `routers/confirmations.py` and `components/ChallengePrompt.jsx` and will remain the authority for form answer confirmation.

## Design

### Backend configuration

Extend `backend/config.py` with settings for:

- `MFA_REQUIRED` (enabled in the local `.env`)
- `OTP_PROVIDER` (`twilio` for the configured runtime)
- OTP length, expiry, resend cooldown, maximum attempts, and session verification lifetime
- `OTP_DEFAULT_COUNTRY_CODE=91`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_VERIFY_SERVICE_SID`

Add the three supplied Twilio values only to `backend/.env`, which is ignored by Git. Add empty placeholders and safe development defaults to `backend/.env.example`; no real credential is stored in tracked files.

### Persistence and security

Add a `PhoneOtp` table containing the session ID, normalized E.164 phone, Twilio verification SID, issue and expiry timestamps, attempt count, and consumed state. The OTP itself is never stored. Add SMS sent, rejected, and verified audit events without logging the code or the full phone number.

Store the successful verification marker in the session state with the verified phone and timestamp. A helper checks its age and session ownership. On success, link or create the existing `User` record using the normalized verified phone; the unverified phone supplied by the client is never trusted for any later action.

### Twilio service

Create a small service based on the archive's Twilio Verify implementation:

- Validate the `AC` account SID and `VA` Verify service SID before making a request.
- Normalize accepted Indian phone formats to E.164.
- Send only `channel="sms"`.
- Check the exact server-held verification SID returned by Twilio.
- Map trial-recipient, cooldown/rate-limit, expired-code, delivery, and provider errors to stable API error codes.
- Expose a mock hook so tests never send real SMS.

### Auth API

Add an `/api/v1/auth` router with:

- `POST /otp/send`: accepts `session_id`, phone, and language; enforces phone validation, resend cooldown, and hourly/session limits; returns only an OTP request ID, masked phone, code length, expiry, and resend timing.
- `POST /otp/verify`: accepts `session_id`, OTP request ID, and the user-entered code; checks Twilio, consumes the request, marks the session verified, and returns verification status.
- `GET /status/{session_id}`: returns whether this session is currently verified and the masked phone; it never returns provider identifiers or code data.

The verify endpoint must reject unknown or cross-session OTP IDs, expired requests, replayed requests, wrong codes beyond the attempt limit, and verification attempts after the session marker expires.

### Form gate

In `routers/forms.py`, the upload endpoint checks the session verification helper before saving the uploaded file or starting OCR. If `MFA_REQUIRED` is enabled and the session is not verified, it returns a structured `form_auth_required` error. Existing form field answering and randomized phrase challenge endpoints remain unchanged.

In `FormFill.jsx`, session preparation becomes:

```text
starting → create/reuse session → check SMS verification
    unverified → verify-phone → verified → upload
    verified → upload
upload → processing → asking → confirming → field-challenge/final-challenge
```

Add a focused `PhoneVerify` component and matching API client functions. The form upload controls are rendered only in the `upload` phase, and the upload handler still relies on the backend gate. No other route imports or renders the OTP component.

### Existing challenge preservation

The current `ChallengePrompt` and confirmation nonce endpoints stay untouched. The form phases after upload continue to issue and validate the randomized phrase/digit challenge at their existing cadence. Tests will explicitly cover that SMS verification does not mark fields confirmed and that a field still requires its randomized challenge afterward.

## Error handling and user experience

- Show a short, translated phone-number instruction and a masked destination after SMS delivery.
- Use `autocomplete="one-time-code"` and numeric input for mobile autofill, while keeping manual entry available.
- Provide resend countdown and a clear “change number” action that starts a new request for the same session.
- Keep provider and network failures recoverable with user-facing messages; do not show raw Twilio responses or credentials.
- If a session cannot be verified, keep the user before the upload screen and do not save their form file.

## Testing

Backend tests will mock the Twilio service and cover:

- E.164 phone normalization and rejection of invalid numbers.
- Correct Twilio Verify send/check parameters and fail-closed configuration.
- Successful send/verify, wrong code, expiry, replay, rate limiting, and cross-session rejection.
- Unverified form upload rejection and verified upload success.
- Existing randomized phrase confirmation still required after SMS verification.
- No OTP or Twilio SID leakage in API responses or audit payloads.

Frontend tests will cover the verification component's send/enter/verify states and the FormFill phase gate. Existing frontend tests, backend tests, build, lint, and diff checks remain required.

## Risks and mitigations

- Real Twilio delivery can fail for trial accounts or unverified recipient numbers; map this to a clear recoverable error and rely on mocked tests for deterministic verification.
- Existing API tests upload forms without MFA. Keep the feature configurable and update test fixtures to disable the gate explicitly where they test unrelated workflows; add dedicated tests with the gate enabled.
- SQLite `create_all` can add new tables for local development, but production database migration should be added before deployment if a migration workflow is used.

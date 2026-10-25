# FinAccess AI Account Authentication Design

## Goal

Require a registered account before users can enter FinAccess AI while preserving the existing form-fill SMS verification and randomized phrase challenge.

## User flow

1. A visitor opens FinAccess AI and sees a dedicated authentication page.
2. Signup collects a username, email address, six-digit MPIN, and MPIN confirmation. It does not collect a phone number or trigger an SMS OTP.
3. The backend validates the fields, rejects duplicate username/email values, hashes the MPIN, and creates the account.
4. The user logs in with username and MPIN. A short-lived signed access token is returned.
5. The frontend stores the access token in `sessionStorage`, restores it on refresh through `/auth/me`, and sends it as a bearer token for account-aware requests.
6. Unauthenticated users remain on the authentication page. Authenticated users may enter the existing Home, Form Fill, Schemes, Guidance, and Fraud Check routes.
7. Form Fill still creates a fresh app session and runs the existing Twilio phone OTP gate before form upload. The randomized phrase challenge remains unchanged.
8. Logout clears the access token, current app session, and returns the user to the authentication page.

## Backend architecture

- Extend the existing `User` model with nullable `username`, `email`, and `mpin_hash` columns so legacy phone-only users and existing OTP tests remain readable. The existing `phone` column remains for the separate form-fill OTP flow and is not part of account signup.
- Add a small SQLite schema upgrade in `ensure_schema` for existing databases.
- Add Pydantic request and response models for signup, login, current-user, and auth-session responses.
- Add `/api/v1/auth/signup`, `/api/v1/auth/login`, and `/api/v1/auth/me` endpoints alongside the existing OTP endpoints.
- Validate username shape, normalize case-insensitive email and username comparisons, require a six-digit numeric MPIN, and return safe user-facing errors without exposing hashes.
- Hash MPINs with the installed password-hashing library and sign access tokens with the existing `SECRET_KEY`. Tokens expire after a configurable interval.
- Add a reusable bearer-token dependency for the frontend account gate. Existing domain endpoint behavior remains compatible while authenticated sessions carry the logged-in user identity.

## Frontend architecture

- Add an `AuthProvider`/hook that owns the token, current user, login, signup, and logout state in `sessionStorage`.
- Add an `AuthPage` with a login/signup toggle and accessible labels. The signup form has username, email, and separate MPIN and confirmation inputs; both MPIN fields are six-digit numeric fields with readable masking and validation messages.
- Add a route guard around the existing application routes. The guard shows a loading state while `/auth/me` is checked and redirects unauthenticated visitors to `/auth`.
- Keep the existing navbar and voice assistant available only inside the authenticated shell, adding a visible logout button with high-contrast styling.
- Add scoped auth-card styles using the established light glassmorphism direction: whitish translucent card, soft border/shadow, dark navy copy, white inputs, visible placeholders, and readable error/success text. Do not alter the existing PhoneVerify visual or behavioral contract beyond the new outer account gate.

## Compatibility and safety

- No phone number is collected during signup and no signup SMS is sent. The existing Twilio OTP is only the form-fill phone verification step.
- No randomized phrase challenge code is removed or bypassed.
- Existing anonymous backend tests remain compatible through the current test configuration; new auth tests cover account creation, duplicate handling, MPIN hashing, login failures, token expiry, and current-user lookup.
- Real `.env` files remain ignored and are never added to Git.
- This work is local-only; no GitHub push is part of the implementation.

## Verification

- Backend focused auth tests and the existing backend suite pass.
- Frontend auth component/route tests cover signup validation, login, logout, refresh restoration, and unauthenticated redirects.
- Frontend lint and production build pass.
- Browser verification confirms the auth page is legible, authenticated routes render after login, and logout returns to auth.

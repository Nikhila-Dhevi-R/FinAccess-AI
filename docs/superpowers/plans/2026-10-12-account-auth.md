# Account Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add username/email/MPIN account signup and login that gates every FinAccess route, while preserving the existing Form Fill SMS OTP and randomized phrase challenge.

**Architecture:** Add nullable account fields to the existing `User` model, hash six-digit MPINs with Passlib, and issue signed short-lived JWTs with the existing `SECRET_KEY`. A React auth provider restores the token from `sessionStorage`, `/auth/me` validates it, and a route shell renders the existing app only for authenticated users. Signup does not collect a phone number or send SMS; the existing phone column and Twilio flow remain form-fill-only.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite schema upgrade helper, Pydantic v2, Passlib `pbkdf2_sha256`, `python-jose`, Axios, React 19, React Router, Vitest, Testing Library, existing glassmorphism CSS.

**Spec:** `docs/superpowers/specs/2026-10-12-account-auth-design.md`

## Global Constraints

- Signup fields are username, email, six-digit MPIN, and re-enter MPIN; no phone number field and no signup OTP.
- Login accepts username and MPIN only.
- Unauthenticated visitors must remain on `/auth` and must not see the existing app shell.
- Existing Form Fill Twilio OTP runs before form upload and the randomized phrase challenge remains unchanged.
- Existing anonymous domain endpoint tests remain compatible; account auth is added as a route gate without rewriting the domain workflows.
- Real `.env` files are ignored and must not be staged or printed.
- Do not push to GitHub.

## Review Focus

- Duplicate username/email signup must return a safe conflict without revealing stored hashes; test in Task 2.
- MPINs must never be stored or returned in plaintext; test hash verification and response shape in Task 2.
- Malformed, expired, or tampered tokens must clear the frontend session and redirect to `/auth`; test in Tasks 3 and 6.
- Refreshing the browser must restore a valid account session but must not bypass the existing Form Fill SMS OTP; test in Tasks 3 and 6.
- Six-digit validation must reject non-digits, short values, mismatched confirmation, and accessible error states; test in Task 5.

### Task 1: Add account fields and configuration

**Files:**
- Modify: `backend/models.py: User`
- Modify: `backend/database.py: ensure_schema`
- Modify: `backend/config.py: Settings`
- Test: `backend/test_account_auth.py`

**Interfaces:**
- Produces `User.username`, `User.email`, and `User.mpin_hash` nullable columns for legacy records.
- Produces `Settings.AUTH_TOKEN_EXPIRE_MINUTES` with a 720-minute default.

- [ ] **Step 1: Write failing schema assertions**

  Add tests that create a user with the new account fields, confirm legacy phone-only users still persist, and confirm the auth expiry setting is available.

- [ ] **Step 2: Run the focused backend test to verify it fails**

  Run: `python -m pytest backend/test_account_auth.py -q`
  Expected: collection or assertion failures because the fields and setting do not exist yet.

- [ ] **Step 3: Add nullable account columns and SQLite upgrade logic**

  Add the three nullable `User` columns and extend `ensure_schema` to add any missing columns on an existing SQLite database without changing the existing `phone_otps` migration behavior. Add indexed columns where supported, but enforce normalized uniqueness in the signup transaction.

- [ ] **Step 4: Run the focused schema test**

  Run: `python -m pytest backend/test_account_auth.py -q`
  Expected: schema and configuration assertions pass; endpoint tests may still fail until Task 2.

### Task 2: Implement password hashing, JWTs, and account endpoints

**Files:**
- Create: `backend/services/account_auth.py`
- Modify: `backend/routers/auth.py`
- Modify: `backend/schemas.py`
- Modify: `backend/main.py` only if the auth dependency needs registration changes
- Test: `backend/test_account_auth.py`

**Interfaces:**
- `POST /api/v1/auth/signup` consumes `{username, email, mpin, mpin_confirmation}` and returns `201` plus a safe account response.
- `POST /api/v1/auth/login` consumes `{username, mpin}` and returns `{access_token, token_type: "bearer", user}`.
- `GET /api/v1/auth/me` consumes `Authorization: Bearer <token>` and returns the safe account response.
- `get_current_user(db, credentials)` decodes and validates the token, returning `User` or raising `401`.

- [ ] **Step 1: Write failing endpoint and crypto tests**

  Cover successful signup, normalized duplicate username/email conflicts, invalid field validation, non-plaintext MPIN storage, successful login, wrong MPIN rejection, missing/tampered/expired token rejection, and `/auth/me` response without sensitive fields.

- [ ] **Step 2: Run the focused backend tests to verify they fail**

  Run: `python -m pytest backend/test_account_auth.py -q`
  Expected: endpoint failures because the account schemas, service, and routes are not implemented.

- [ ] **Step 3: Implement `account_auth.py`**

  Use Passlib `pbkdf2_sha256` for `hash_mpin`/`verify_mpin`, `python-jose` HS256 tokens with `sub` and `exp` claims, normalized casefolded username/email helpers, and a bearer dependency that returns safe `401` errors. Keep all secret values in settings.

- [ ] **Step 4: Add Pydantic models and auth routes**

  Validate username length/characters, email shape, and exactly six numeric MPIN digits. Create accounts without a phone value or SMS call; return `409` for duplicate normalized identifiers. Keep the existing `/auth/otp/*` routes unchanged.

- [ ] **Step 5: Run focused and existing backend tests**

  Run: `python -m pytest backend/test_account_auth.py backend/test_sms_auth.py -q`
  Expected: all account and SMS tests pass.

### Task 3: Add frontend auth API and session provider

**Files:**
- Create: `frontend/src/auth/AuthContext.jsx`
- Create: `frontend/src/hooks/useAuth.js`
- Modify: `frontend/src/api/client.js`
- Test: `frontend/src/auth/AuthContext.test.jsx`

**Interfaces:**
- `signupAccount({ username, email, mpin, mpinConfirmation }) -> account`
- `loginAccount({ username, mpin }) -> { access_token, token_type, user }`
- `getCurrentAccount() -> user`
- `useAuth() -> { user, loading, error, signup, login, logout, isAuthenticated }`

- [ ] **Step 1: Write failing provider/API tests**

  Cover signup payload shape without a phone property, token persistence, `/auth/me` restoration, invalid-token cleanup, login error propagation, and logout clearing both account token and existing app session storage.

- [ ] **Step 2: Run the focused frontend tests to verify they fail**

  Run: `npm test -- --run src/auth/AuthContext.test.jsx`
  Expected: module or assertion failures because the provider and API helpers do not exist.

- [ ] **Step 3: Implement auth API helpers and Axios bearer injection**

  Add account calls to `client.js`, attach the `sessionStorage` bearer token on requests, and leave existing endpoint helpers unchanged. Do not store the MPIN.

- [ ] **Step 4: Implement `AuthContext` and `useAuth`**

  Restore the token once on mount through `/auth/me`, expose loading/error state, persist successful login tokens, switch to the login view after signup, and clear `finaccess_auth_token`, `finaccess_session_id`, and user state on logout.

- [ ] **Step 5: Run the provider tests**

  Run: `npm test -- --run src/auth/AuthContext.test.jsx`
  Expected: all provider tests pass.

### Task 4: Build the signup/login page and scoped visual system

**Files:**
- Create: `frontend/src/pages/AuthPage.jsx`
- Modify: `frontend/src/index.css`
- Test: `frontend/src/pages/AuthPage.test.jsx`

**Interfaces:**
- `AuthPage` consumes `useAuth()` and renders login/signup modes without changing existing page components.
- Accessible labels: `Username`, `Email`, `Create MPIN`, `Re-enter MPIN`, and `MPIN`.

- [ ] **Step 1: Write failing UI tests**

  Cover default login mode, signup toggle fields, six-digit input filtering, mismatch/short-MPIN errors, successful signup handoff, login submission, visible API error text, and the absence of a phone input.

- [ ] **Step 2: Run the focused UI tests to verify they fail**

  Run: `npm test -- --run src/pages/AuthPage.test.jsx`
  Expected: module or assertion failures because the page does not exist.

- [ ] **Step 3: Implement the accessible auth card**

  Use a single responsive card with clear login/signup tabs, readable dark navy copy, white inputs, visible placeholders, strong focus rings, six-digit MPIN masking, and concise safe error messages. Submit signup only after client validation, then switch to login with a success message; login calls the provider and navigates to `/`.

- [ ] **Step 4: Add scoped light glassmorphism styles**

  Add `.auth-page`, `.auth-card`, `.auth-input`, `.auth-primary-button`, and `.auth-secondary-button` rules at the end of `index.css` so global dark input overrides cannot reduce contrast. Keep existing PhoneVerify and other cards unchanged.

- [ ] **Step 5: Run the focused page tests**

  Run: `npm test -- --run src/pages/AuthPage.test.jsx`
  Expected: all auth page tests pass.

### Task 5: Gate the existing app shell and add logout

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Navbar.jsx`
- Create or modify: `frontend/src/components/AuthLoadingScreen.jsx` if a loading view is needed
- Test: `frontend/src/App.test.jsx` or an equivalent route-guard test

**Interfaces:**
- Unauthenticated paths render only `/auth`.
- Authenticated paths render the existing `Navbar`, route pages, `FloatingVoiceBot`, and `SiteFooter`.

- [ ] **Step 1: Write failing route-guard tests**

  Cover unauthenticated redirect from `/`, authenticated rendering of `/`, redirect from `/auth` after login, loading state while `/auth/me` resolves, and logout returning to `/auth`.

- [ ] **Step 2: Run the route tests to verify they fail**

  Run: `npm test -- --run src/App.test.jsx`
  Expected: unauthenticated users currently see the existing app shell.

- [ ] **Step 3: Add the provider, guard, and shell split**

  Wrap the router with `AuthProvider`, add `/auth`, and render the existing app shell only inside an authenticated route component. Keep the current route paths and page implementations intact.

- [ ] **Step 4: Add a visible logout control**

  Use `useAuth().logout` in the existing navbar with a readable label and scoped styling; do not remove language or repeat-audio controls.

- [ ] **Step 5: Run route and existing frontend tests**

  Run: `npm test -- --run`
  Expected: all auth tests and the existing frontend suite pass.

### Task 6: Full verification and local browser check

**Files:**
- Modify only files needed to resolve test or lint failures from Tasks 1-5.

- [ ] **Step 1: Run backend verification**

  Run: `python -m pytest backend -q`
  Expected: the existing backend suite and new account-auth tests pass.

- [ ] **Step 2: Run frontend verification**

  Run: `npm test -- --run`, `npm run lint`, and `npm run build` from `frontend`.
  Expected: tests and build pass; lint may report only pre-existing warnings.

- [ ] **Step 3: Check repository safety**

  Run: `git diff --check`, `git status --short`, and a tracked-file scan confirming `.env` files and real credentials are absent.

- [ ] **Step 4: Verify the live local UI**

  Open `http://localhost:5173/`, confirm the auth card is legible, create a local test account, log in, confirm the existing home shell renders, refresh to restore the login, and log out. Confirm Form Fill still presents its separate SMS verification card after account login.

- [ ] **Step 5: Stop without pushing**

  Report the local commit/status and verification evidence. Do not run `git push`.

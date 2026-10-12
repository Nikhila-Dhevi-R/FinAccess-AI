"""Account model and authentication contract tests."""

from models import User
from config import get_settings


def test_user_supports_account_identity_fields(db_session):
    user = User(
        id="account-user-1",
        username="nisha",
        email="nisha@example.com",
        mpin_hash="hashed-mpin",
    )
    db_session.add(user)
    db_session.commit()

    saved = db_session.query(User).filter_by(id="account-user-1").one()
    assert saved.username == "nisha"
    assert saved.email == "nisha@example.com"
    assert saved.mpin_hash == "hashed-mpin"


def test_auth_token_expiry_setting_is_available():
    assert get_settings().AUTH_TOKEN_EXPIRE_MINUTES == 720


def test_signup_creates_account_without_phone_and_never_returns_mpin(client, db_session):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "username": "nisha_account",
            "email": "nisha.account@example.com",
            "mpin": "123456",
            "mpin_confirmation": "123456",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "nisha_account"
    assert payload["email"] == "nisha.account@example.com"
    assert "phone" not in payload
    assert "mpin" not in payload
    assert "mpin_hash" not in payload

    saved = db_session.query(User).filter_by(username="nisha_account").one()
    assert saved.phone is None
    assert saved.mpin_hash != "123456"
    assert saved.mpin_hash


def test_signup_rejects_case_insensitive_duplicate_username_and_email(client):
    first = client.post(
        "/api/v1/auth/signup",
        json={
            "username": "duplicate_user",
            "email": "duplicate@example.com",
            "mpin": "123456",
            "mpin_confirmation": "123456",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/auth/signup",
        json={
            "username": "Duplicate_User",
            "email": "other@example.com",
            "mpin": "654321",
            "mpin_confirmation": "654321",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "username_taken"


def test_login_returns_token_and_me_returns_safe_account(client):
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "username": "login_user",
            "email": "login@example.com",
            "mpin": "234567",
            "mpin_confirmation": "234567",
        },
    )
    assert signup.status_code == 201

    login = client.post("/api/v1/auth/login", json={"username": "LOGIN_USER", "mpin": "234567"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert login.json()["token_type"] == "bearer"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "login_user"
    assert "mpin_hash" not in me.json()


def test_login_rejects_wrong_mpin_and_me_rejects_tampered_token(client):
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "username": "secure_user",
            "email": "secure@example.com",
            "mpin": "345678",
            "mpin_confirmation": "345678",
        },
    )
    assert signup.status_code == 201

    wrong = client.post("/api/v1/auth/login", json={"username": "secure_user", "mpin": "999999"})
    assert wrong.status_code == 401
    assert wrong.json()["detail"]["code"] == "invalid_credentials"

    tampered = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert tampered.status_code == 401

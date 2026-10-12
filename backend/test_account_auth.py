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

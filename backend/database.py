from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
)

# Enable WAL mode for SQLite for better concurrency
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def _rebuild_legacy_phone_otps(target_engine, columns):
    """Replace the pre-Twilio OTP table whose required code_hash blocks inserts."""

    verification_sid = (
        "COALESCE(NULLIF(verification_sid, ''), 'legacy')"
        if "verification_sid" in columns
        else "'legacy'"
    )
    with target_engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS phone_otps_migrating"))
        connection.execute(
            text(
                """
                CREATE TABLE phone_otps_migrating (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    session_id VARCHAR NOT NULL,
                    phone VARCHAR NOT NULL,
                    verification_sid VARCHAR NOT NULL,
                    channel VARCHAR(3) NOT NULL,
                    issued_at DATETIME,
                    expires_at DATETIME NOT NULL,
                    attempt_count INTEGER,
                    consumed BOOLEAN,
                    consumed_at DATETIME,
                    FOREIGN KEY(session_id) REFERENCES user_sessions (id)
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO phone_otps_migrating (
                    id, session_id, phone, verification_sid, channel, issued_at,
                    expires_at, attempt_count, consumed, consumed_at
                )
                SELECT id, session_id, phone, {verification_sid},
                    CASE WHEN lower(channel) = 'sms' THEN 'SMS' ELSE channel END,
                    issued_at, expires_at, attempt_count, consumed, consumed_at
                FROM phone_otps
                """
            )
        )
        connection.execute(text("DROP TABLE phone_otps"))
        connection.execute(text("ALTER TABLE phone_otps_migrating RENAME TO phone_otps"))
        connection.execute(text("CREATE INDEX ix_phone_otps_phone ON phone_otps (phone)"))


def ensure_schema(bind_engine=None):
    """Apply small SQLite upgrades that ``create_all`` cannot make in place."""

    target_engine = bind_engine or engine
    if target_engine.dialect.name != "sqlite":
        return

    inspector = inspect(target_engine)
    table_names = set(inspector.get_table_names())

    if "phone_otps" in table_names:
        columns = {column["name"] for column in inspector.get_columns("phone_otps")}
        if "code_hash" in columns:
            _rebuild_legacy_phone_otps(target_engine, columns)
        elif "verification_sid" not in columns:
            with target_engine.begin() as connection:
                connection.execute(text("ALTER TABLE phone_otps ADD COLUMN verification_sid VARCHAR"))

    if "users" not in table_names:
        return

    user_columns = {column["name"] for column in inspect(target_engine).get_columns("users")}
    additions = {
        "username": "VARCHAR",
        "email": "VARCHAR",
        "mpin_hash": "VARCHAR",
    }
    with target_engine.begin() as connection:
        for name, column_type in additions.items():
            if name not in user_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {column_type}"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_username_account "
                "ON users (username) WHERE username IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_account "
                "ON users (email) WHERE email IS NOT NULL"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

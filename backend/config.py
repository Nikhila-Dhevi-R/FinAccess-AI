from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "FinAccess AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'finaccess.db').as_posix()}"

    # Security for randomized voice/text confirmation challenges
    SECRET_KEY: str = "finaccess-dev-secret-change-in-production"
    NONCE_EXPIRY_SECONDS: int = 30

    # OCR
    OCR_BACKEND: str = "stub"  # "stub" | "tesseract" | "cloud"
    TESSERACT_CMD: str = "tesseract"

    # Speech
    STT_BACKEND: str = "stub"  # "stub" | "whisper" | "bhashini"
    TTS_BACKEND: str = "stub"  # "stub" | "google" | "bhashini"

    # Translation
    TRANSLATION_BACKEND: str = "stub"  # "stub" | "google" | "bhashini"

    # LLM
    LLM_BACKEND: str = "stub"  # "stub" | "openai" | "gemini"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Upload
    UPLOAD_DIR: str = str(BACKEND_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()

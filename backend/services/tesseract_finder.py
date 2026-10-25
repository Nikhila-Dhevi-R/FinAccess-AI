"""
Centralized Tesseract discovery and configuration service.
Provides consistent Tesseract executable location and configuration
across all OCR services (image OCR, cheque service, bank form service, message OCR).
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from config import get_settings

settings = get_settings()


def find_tesseract_cmd() -> Optional[str]:
    """
    Locates the tesseract executable across environment settings, PATH,
    and standard installation paths (including Windows Scoop, Program Files, LocalAppData).
    """
    # 1. Configured TESSERACT_CMD if explicitly set and valid
    if settings.TESSERACT_CMD and settings.TESSERACT_CMD != "tesseract":
        if os.path.isabs(settings.TESSERACT_CMD) and os.path.isfile(settings.TESSERACT_CMD):
            return settings.TESSERACT_CMD
        found = shutil.which(settings.TESSERACT_CMD)
        if found:
            return found

    # 2. Check standard PATH
    found = shutil.which("tesseract")
    if found:
        return found

    # 3. Known candidate locations on Windows and Unix
    user_home = Path.home()
    candidates = [
        # Scoop installations (current user)
        user_home / "scoop" / "shims" / "tesseract.exe",
        user_home / "scoop" / "apps" / "tesseract" / "current" / "tesseract.exe",
        # Standard Windows Program Files
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        # LocalAppData
        user_home / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        # Unix/Linux / macOS standards
        Path("/usr/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
        Path("/opt/homebrew/bin/tesseract"),
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def configure_tesseract() -> Optional[str]:
    """
    Configures pytesseract with the discovered executable path and
    ensures TESSDATA_PREFIX environment variable is configured if needed.
    Returns the executable path if available, or None.
    """
    cmd = find_tesseract_cmd()
    if not cmd:
        return None

    # Setup TESSDATA_PREFIX if not already set or invalid
    if not os.environ.get("TESSDATA_PREFIX"):
        cmd_path = Path(cmd)
        # Check adjacent tessdata folder
        potential_tessdata = [
            cmd_path.parent / "tessdata",
            cmd_path.parent.parent / "apps" / "tesseract" / "current" / "tessdata",
            Path.home() / "scoop" / "apps" / "tesseract" / "current" / "tessdata",
            Path.home() / "scoop" / "persist" / "tesseract" / "tessdata",
            Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
        ]
        for td in potential_tessdata:
            if td.is_dir() and any(td.glob("*.traineddata")):
                os.environ["TESSDATA_PREFIX"] = str(td)
                break

    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = cmd
    except ImportError:
        pass

    return cmd


def is_tesseract_available() -> bool:
    """Check if Tesseract executable is present and callable."""
    return find_tesseract_cmd() is not None

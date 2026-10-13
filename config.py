from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-development-secret-key")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Gemini 3.5 Flash is the stable production replacement for Gemini 2.5 Flash.
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    DATABASE_DIR = BASE_DIR / "database"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DATABASE_DIR / 'contracts.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
    CONTRACT_TEXT_LIMIT = 45_000

    LOG_DIR = BASE_DIR / "logs"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True

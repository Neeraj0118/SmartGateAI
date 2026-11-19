"""
Configuration management for SmartGateAI using environment variables.
Enforces strict security:
- Admin API key loaded from SMARTGATE_ADMIN_API_KEY with NO default.
- Server bound strictly to localhost (127.0.0.1).
- Loads .env file securely via python-dotenv.
"""

import os
from typing import List
from dotenv import load_dotenv

# Search and load .env from project root or backend directory
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
_root_dir = os.path.dirname(_backend_dir)

_env_candidates = [
    os.path.join(_backend_dir, ".env"),
    os.path.join(_root_dir, ".env"),
]

for _candidate in _env_candidates:
    if os.path.exists(_candidate):
        load_dotenv(_candidate, override=True)
        break


class Settings:
    PROJECT_NAME: str = "SmartGateAI - Smart Gate Monitoring System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Base directories
    APP_DIR: str = _current_dir
    BACKEND_DIR: str = _backend_dir
    STORAGE_DIR: str = os.path.join(_backend_dir, "storage")
    WEIGHTS_DIR: str = os.path.join(_backend_dir, "weights")
    STUDENT_PHOTOS_DIR: str = os.path.join(STORAGE_DIR, "student_photos")

    # Database URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(STORAGE_DIR, 'smartgate.db')}"
    )

    # Model Weights (OpenCV Zoo YuNet & SFace)
    YUNET_MODEL_PATH: str = os.path.join(WEIGHTS_DIR, "face_detection_yunet_2023mar.onnx")
    SFACE_MODEL_PATH: str = os.path.join(WEIGHTS_DIR, "face_recognition_sface_2021dec.onnx")

    # AI Thresholds
    FACE_SIMILARITY_THRESHOLD: float = 0.637
    MIN_ENROLLMENT_BLUR_SCORE: float = 50.0

    # Server Binding (Strictly localhost)
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

    # CORS Whitelist (Strictly restricted to localhost development origins, no wildcards)
    ALLOWED_ORIGINS: List[str] = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://localhost",
    ]
    # Regex restricting CORS origins strictly to localhost / 127.0.0.1 on any port
    ALLOWED_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$"

    @property
    def ADMIN_API_KEY(self) -> str:
        """
        Retrieve administrator API key from environment.
        Fails safely if missing or empty — NEVER provides an insecure default.
        """
        key = os.getenv("SMARTGATE_ADMIN_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: 'SMARTGATE_ADMIN_API_KEY' environment variable "
                "is missing or empty. The server will not start with insecure defaults. "
                "Please configure 'SMARTGATE_ADMIN_API_KEY' in your .env file or environment."
            )
        return key


settings = Settings()

# Ensure required storage directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(settings.STUDENT_PHOTOS_DIR, exist_ok=True)
os.makedirs(settings.WEIGHTS_DIR, exist_ok=True)

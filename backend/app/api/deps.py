"""
Dependency injection providers for FastAPI controllers.
Manages database sessions, singleton AI inference engines, and student services.
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from ..db.session import SessionLocal
from ..config import settings
from ..services.ai.base import FaceEngine
from ..services.ai.opencv_engine import OpenCVFaceEngine
from ..services.ai.vector_matcher import VectorMatcher
from ..services.storage_service import PhotoStorageService
from ..services.student_service import StudentService
from ..core.security import verify_admin_key


# Singleton holders for AI Vision components
_face_engine_instance: FaceEngine = None
_vector_matcher_instance: VectorMatcher = None
_photo_storage_instance: PhotoStorageService = None


def get_face_engine() -> FaceEngine:
    """Retrieve or initialize the singleton FaceEngine."""
    global _face_engine_instance
    if _face_engine_instance is None:
        _face_engine_instance = OpenCVFaceEngine(
            detector_path=settings.YUNET_MODEL_PATH,
            recognizer_path=settings.SFACE_MODEL_PATH
        )
    return _face_engine_instance


def get_vector_matcher() -> VectorMatcher:
    """Retrieve or initialize the singleton in-memory VectorMatcher."""
    global _vector_matcher_instance
    if _vector_matcher_instance is None:
        engine = get_face_engine()
        _vector_matcher_instance = VectorMatcher(
            engine=engine,
            similarity_threshold=settings.FACE_SIMILARITY_THRESHOLD
        )
    return _vector_matcher_instance


def get_photo_storage() -> PhotoStorageService:
    """Retrieve or initialize the PhotoStorageService."""
    global _photo_storage_instance
    if _photo_storage_instance is None:
        _photo_storage_instance = PhotoStorageService(
            base_storage_dir=settings.STUDENT_PHOTOS_DIR
        )
    return _photo_storage_instance


def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_student_service(
    db: Session = Depends(get_db_session),
    engine: FaceEngine = Depends(get_face_engine),
    matcher: VectorMatcher = Depends(get_vector_matcher),
    storage: PhotoStorageService = Depends(get_photo_storage)
) -> StudentService:
    """Provide initialized StudentService with synchronized caches."""
    return StudentService(
        db=db,
        engine=engine,
        matcher=matcher,
        storage=storage
    )


def require_admin(admin_key: str = Depends(verify_admin_key)) -> str:
    """Dependency that enforces admin authentication."""
    return admin_key

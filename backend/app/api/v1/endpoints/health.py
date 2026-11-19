"""
Health and diagnostic status endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.student import HealthResponse
from app.config import settings
from app.api.deps import get_db_session, get_vector_matcher, get_face_engine

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Diagnostic Status",
    description="Check database connectivity, AI model readiness, and in-memory cache status."
)
def check_health(
    db: Session = Depends(get_db_session),
    matcher = Depends(get_vector_matcher),
    engine = Depends(get_face_engine)
) -> HealthResponse:
    # Verify DB connectivity
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    models_ok = (engine.detector is not None and engine.recognizer is not None)
    cached_count = matcher.get_enrolled_count()

    return HealthResponse(
        status="healthy" if (db_ok and models_ok) else "degraded",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        database_connected=db_ok,
        cached_students_count=cached_count,
        models_ready=models_ok
    )

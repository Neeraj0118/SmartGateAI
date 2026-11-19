"""
FastAPI application entry point for SmartGateAI.
Configures lifespan events, CORS, database initialization, and in-memory cache rehydration.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.session import init_db, SessionLocal
from .api.deps import get_face_engine, get_vector_matcher, get_photo_storage
from .services.student_service import StudentService
from .api.v1.router import api_v1_router
from .schemas.student import HealthResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SmartGateAI.App")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager:
    - Runs schema migrations and table creation.
    - Loads pre-trained YuNet & SFace models.
    - Synchronizes in-memory VectorMatcher recognition cache from SQLite.
    """
    logger.info("Initializing SmartGateAI application...")

    # 1. Initialize SQLite database tables
    init_db()
    logger.info("Database schema initialized.")

    # 2. Warm up AI Vision Engine & In-Memory Vector Matcher
    engine = get_face_engine()
    matcher = get_vector_matcher()
    storage = get_photo_storage()
    logger.info(f"AI Vision Engine loaded (YuNet + SFace {engine.get_embedding_dimension()}-D).")

    # 3. Rehydrate in-memory recognition cache from database
    db = SessionLocal()
    try:
        service = StudentService(
            db=db,
            engine=engine,
            matcher=matcher,
            storage=storage
        )
        cached_count = service.sync_cache_from_db()
        logger.info(f"Rehydrated {cached_count} enrolled students into VectorMatcher cache.")
    finally:
        db.close()

    logger.info("SmartGateAI is ready to receive requests.")
    yield

    # Teardown logic
    logger.info("Shutting down SmartGateAI...")


def create_application() -> FastAPI:
    """Factory creating and configuring the FastAPI instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="High-Throughput AI Smart Gate Monitoring & Multi-Person Recognition API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        servers=[{"url": "/", "description": "Localhost Server"}],
        lifespan=lifespan
    )

    # CORS configuration - strictly restricted to localhost / 127.0.0.1 (no wildcards)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Mount API v1 router
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    # Compatibility endpoint for /api/v1/openapi.json
    @app.get(f"{settings.API_V1_STR}/openapi.json", include_in_schema=False)
    def get_v1_openapi():
        return app.openapi()

    # Expose root-level health probe
    @app.get("/health", response_model=HealthResponse, tags=["System Health"], include_in_schema=False)
    def root_health(
        engine = Depends(get_face_engine),
        matcher = Depends(get_vector_matcher)
    ):
        return HealthResponse(
            status="healthy",
            app_name=settings.PROJECT_NAME,
            version=settings.VERSION,
            database_connected=True,
            cached_students_count=matcher.get_enrolled_count(),
            models_ready=(engine.detector is not None and engine.recognizer is not None)
        )

    return app


app = create_application()

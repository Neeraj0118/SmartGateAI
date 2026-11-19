"""
SQLAlchemy Declarative Base for SmartGateAI.
Designed cleanly for SQLite in development and PostgreSQL in production.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# Import all models here so that Base.metadata is populated before create_all()
from app.models.student import Student, FaceEmbedding  # noqa: F401, E402
from app.models.recognition_event import RecognitionEvent  # noqa: F401, E402
from app.models.vehicle import VehicleRegistration  # noqa: F401, E402

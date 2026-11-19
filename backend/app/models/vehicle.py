"""
SQLAlchemy ORM model for Vehicle Registrations.
Tracks registered vehicles linked to students or standalone visitors.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base


class VehicleRegistration(Base):
    """A registered vehicle record (manual registration, no OCR required)."""
    __tablename__ = "vehicle_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(30), default="car", nullable=False)
    vehicle_make: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    vehicle_color: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    associated_student_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<VehicleRegistration(id={self.id}, number={self.vehicle_number!r}, owner={self.owner_name!r})>"

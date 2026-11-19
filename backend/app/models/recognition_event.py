"""
SQLAlchemy ORM model for Recognition/Attendance Events.
Logs every face recognition event detected by the camera service.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base


class RecognitionEvent(Base):
    """An attendance/recognition event captured by the gate camera."""
    __tablename__ = "recognition_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    event_type: Mapped[str] = mapped_column(String(10), default="entry", nullable=False)
    gate_id: Mapped[str] = mapped_column(String(20), default="main", nullable=False)
    similarity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_known: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="camera", nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<RecognitionEvent(id={self.id}, student_id={self.student_id!r}, event_type={self.event_type!r}, is_known={self.is_known}, captured_at={self.captured_at})>"

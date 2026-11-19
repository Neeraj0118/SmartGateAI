"""
Pydantic schemas for Recognition Event / Attendance API responses.
Timestamps are returned as UTC-aware ISO strings (+00:00) so browsers
parse them correctly and display in local/IST time.
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


class RecognitionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: Optional[str] = None
    full_name: Optional[str] = None
    event_type: str
    gate_id: str = "main"
    similarity: Optional[float] = None
    is_known: bool
    source: str
    captured_at: datetime
    created_at: datetime

    @field_validator('captured_at', 'created_at', mode='before')
    @classmethod
    def ensure_utc(cls, v):
        """Make naive datetimes UTC-aware so FastAPI serializes them with +00:00."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class AttendanceListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    items: List[RecognitionEventResponse]
    skip: int
    limit: int


class AttendanceStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_today: int
    known_today: int
    unknown_today: int
    unique_students_today: int
    entries_today: int
    exits_today: int

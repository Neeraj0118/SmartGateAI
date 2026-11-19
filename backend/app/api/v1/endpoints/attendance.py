"""
Attendance / Recognition Event API endpoints for SmartGateAI.
Provides paginated event listing, daily statistics, and CSV export (admin only).
Timestamps in CSV are converted to IST (Asia/Kolkata).
"""

import csv
import io
import logging
from datetime import datetime, date, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse as FastAPIStreaming
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import require_admin, get_db_session
from app.models.recognition_event import RecognitionEvent
from app.schemas.recognition_event import AttendanceListResponse, AttendanceStatsResponse, RecognitionEventResponse

logger = logging.getLogger("SmartGateAI.AttendanceEndpoints")

IST = timezone(timedelta(hours=5, minutes=30))

router = APIRouter()


def _to_ist_str(dt: Optional[datetime]) -> str:
    """Format a datetime as IST string for CSV export."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d %b %Y %I:%M:%S %p IST")


def _build_filtered_stmt(stmt, is_known, student_id_search, date_filter, event_type=None):
    if is_known is not None:
        stmt = stmt.where(RecognitionEvent.is_known == is_known)
    if student_id_search:
        stmt = stmt.where(RecognitionEvent.student_id.ilike(f"%{student_id_search}%"))
    if date_filter:
        try:
            day = datetime.strptime(date_filter, "%Y-%m-%d").date()
            stmt = stmt.where(func.date(RecognitionEvent.captured_at) == str(day))
        except ValueError:
            pass
    if event_type:
        stmt = stmt.where(RecognitionEvent.event_type == event_type)
    return stmt


@router.get("/", response_model=AttendanceListResponse)
def list_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_known: Optional[bool] = Query(None),
    student_id_search: Optional[str] = Query(None),
    date_filter: Optional[str] = Query(None, description="Format YYYY-MM-DD"),
    event_type: Optional[str] = Query(None, description="Filter by event type: 'entry' or 'exit'"),
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """List recognition events with optional filters (admin only)."""
    stmt = _build_filtered_stmt(select(RecognitionEvent), is_known, student_id_search, date_filter, event_type)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(total_stmt).scalar_one()

    stmt = stmt.order_by(RecognitionEvent.captured_at.desc()).offset(skip).limit(limit)
    rows = db.execute(stmt).scalars().all()

    return AttendanceListResponse(
        total=total,
        items=[RecognitionEventResponse.model_validate(r) for r in rows],
        skip=skip,
        limit=limit,
    )


@router.get("/export/csv")
def export_attendance_csv(
    is_known: Optional[bool] = Query(None),
    student_id_search: Optional[str] = Query(None),
    date_filter: Optional[str] = Query(None, description="Format YYYY-MM-DD"),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """Export attendance records to CSV with IST timestamps (admin only)."""
    stmt = _build_filtered_stmt(select(RecognitionEvent), is_known, student_id_search, date_filter, event_type)
    stmt = stmt.order_by(RecognitionEvent.captured_at.desc())
    rows = db.execute(stmt).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Student ID", "Name", "Event Type", "Gate", "Similarity", "Known", "Source", "Captured At (IST)"])
    for r in rows:
        sim = f"{r.similarity:.4f}" if r.similarity is not None else ""
        writer.writerow([
            r.id,
            r.student_id or "",
            r.full_name or "Unknown",
            r.event_type,
            r.gate_id,
            sim,
            "Yes" if r.is_known else "No",
            r.source,
            _to_ist_str(r.captured_at),
        ])

    output.seek(0)
    filename = f"attendance_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv"
    return FastAPIStreaming(
        iter([output.getvalue().encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/stats", response_model=AttendanceStatsResponse)
def attendance_stats(
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """Return recognition event statistics for today (IST date) (admin only)."""
    # Use IST date so records match what the user sees in the UI
    today_ist: date = datetime.now(IST).date()

    # Load all today's events using SQLite's date() on the stored UTC value
    # Note: stored values are UTC, so IST date = UTC date in most cases
    # We use func.date() which maps to SQLite's date() function
    today_events = db.execute(
        select(RecognitionEvent).where(func.date(RecognitionEvent.captured_at) == str(today_ist))
    ).scalars().all()

    total_today = len(today_events)
    known_today = sum(1 for e in today_events if e.is_known)
    unknown_today = sum(1 for e in today_events if not e.is_known)
    unique_students_today = len({e.student_id for e in today_events if e.student_id})
    entries_today = sum(1 for e in today_events if e.event_type == "entry")
    exits_today = sum(1 for e in today_events if e.event_type == "exit")

    return AttendanceStatsResponse(
        total_today=total_today,
        known_today=known_today,
        unknown_today=unknown_today,
        unique_students_today=unique_students_today,
        entries_today=entries_today,
        exits_today=exits_today,
    )

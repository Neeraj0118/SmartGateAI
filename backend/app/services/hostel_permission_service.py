"""
Service layer for managing Hostel Exit Permissions, Active Outings, and Security Alerts.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, or_, and_, update
from sqlalchemy.orm import Session

from ..models.student import Student
from ..models.hostel_permission import HostelPermission, ActiveOuting, SecurityAlert
from ..schemas.hostel_permission import (
    HostelPermissionCreate,
    HostelPermissionReject,
    HostelPermissionStatsResponse,
)

IST = timezone(timedelta(hours=5, minutes=30))


def _to_naive_utc(dt: datetime) -> datetime:
    """Convert any datetime to naive UTC for consistent SQLite comparisons."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse date (YYYY-MM-DD) and time (HH:MM or HH:MM:SS) strings into naive UTC datetime."""
    clean_date = date_str.strip()
    clean_time = time_str.strip()
    if len(clean_time) == 5:
        clean_time += ":00"

    dt_str = f"{clean_date} {clean_time}"
    try:
        naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        # Input is in IST, convert to naive UTC
        ist_dt = naive_dt.replace(tzinfo=IST)
        return ist_dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception as e:
        raise ValueError(f"Invalid date/time format '{dt_str}'. Expected YYYY-MM-DD and HH:MM(:SS). Error: {e}")


class HostelPermissionService:
    def __init__(self, db: Session):
        self.db = db

    def auto_expire_permissions(self) -> int:
        """Mark Approved permissions whose valid_until window has passed as Expired."""
        now_utc = datetime.utcnow()
        stmt = (
            update(HostelPermission)
            .where(
                and_(
                    HostelPermission.status == "Approved",
                    HostelPermission.valid_until < now_utc
                )
            )
            .values(status="Expired")
        )
        res = self.db.execute(stmt)
        if res.rowcount > 0:
            self.db.commit()
        return res.rowcount or 0

    def check_overdue_outings(self) -> int:
        """Check active outings whose expected_return_time has passed and mark as Late; create SecurityAlert."""
        now_utc = datetime.utcnow()
        overdue_outings = self.db.scalars(
            select(ActiveOuting).where(
                and_(
                    ActiveOuting.status == "Out",
                    ActiveOuting.expected_return_time < now_utc
                )
            )
        ).all()

        updated_count = 0
        for outing in overdue_outings:
            outing.status = "Late"
            updated_count += 1

            # Check if alert already exists for this outing
            existing_alert = self.db.scalar(
                select(SecurityAlert).where(
                    and_(
                        SecurityAlert.alert_type == "LATE_RETURN",
                        SecurityAlert.student_id == outing.student_id,
                        SecurityAlert.is_resolved == False
                    )
                )
            )
            if not existing_alert:
                exp_ist_str = (
                    outing.expected_return_time.replace(tzinfo=timezone.utc).astimezone(IST).strftime('%d %b %Y, %I:%M %p IST')
                    if outing.expected_return_time else "N/A"
                )
                alert = SecurityAlert(
                    alert_type="LATE_RETURN",
                    severity="HIGH",
                    student_id=outing.student_id,
                    student_name=outing.student_name,
                    gate_id="exit",
                    description=(
                        f"Student {outing.student_name} ({outing.student_id}) is overdue for return! "
                        f"Hostel: {outing.hostel_name or 'N/A'}, Room: {outing.room_number or 'N/A'}. "
                        f"Expected return was {exp_ist_str}."
                    ),
                    is_resolved=False
                )
                self.db.add(alert)

        if updated_count > 0:
            self.db.commit()
        return updated_count

    def create_permission(self, data: HostelPermissionCreate) -> HostelPermission:
        """Create a new exit permission request."""
        clean_student_id = data.student_id.strip()

        # Check student
        student = self.db.scalar(select(Student).where(Student.student_id == clean_student_id))
        if not student:
            raise ValueError(f"Student with ID '{clean_student_id}' does not exist.")

        student_name = data.student_name.strip() if data.student_name else student.full_name

        valid_from = _parse_datetime(data.departure_date, data.departure_time)
        valid_until = _parse_datetime(data.expected_return_date, data.expected_return_time)

        if valid_until <= valid_from:
            raise ValueError("Expected return date/time must be strictly after departure date/time.")

        permission = HostelPermission(
            student_id=clean_student_id,
            student_name=student_name,
            reason=data.reason.strip(),
            departure_date=data.departure_date.strip(),
            departure_time=data.departure_time.strip(),
            valid_from=valid_from,
            expected_return_date=data.expected_return_date.strip(),
            expected_return_time=data.expected_return_time.strip(),
            valid_until=valid_until,
            status="Pending"
        )
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def list_permissions(
        self,
        status: Optional[str] = None,
        student_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[int, List[HostelPermission]]:
        """List permission requests with filters."""
        # First trigger auto-expiration check
        self.auto_expire_permissions()

        stmt = select(HostelPermission)
        if status:
            stmt = stmt.where(HostelPermission.status == status)
        if student_id:
            stmt = stmt.where(HostelPermission.student_id == student_id)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    HostelPermission.student_id.ilike(term),
                    HostelPermission.student_name.ilike(term),
                    HostelPermission.reason.ilike(term)
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = stmt.order_by(HostelPermission.created_at.desc()).offset(skip).limit(limit)
        items = list(self.db.scalars(stmt).all())
        return total, items

    def get_permission_by_id(self, permission_id: int) -> Optional[HostelPermission]:
        return self.db.scalar(select(HostelPermission).where(HostelPermission.id == permission_id))

    def approve_permission(self, permission_id: int, admin_name: str = "Admin") -> HostelPermission:
        permission = self.get_permission_by_id(permission_id)
        if not permission:
            raise KeyError(f"Permission with ID {permission_id} not found.")

        if permission.status != "Pending":
            raise ValueError(f"Cannot approve permission in '{permission.status}' status. Only Pending requests can be approved.")

        now_utc = datetime.utcnow()
        valid_until_naive = _to_naive_utc(permission.valid_until)
        if valid_until_naive < now_utc:
            permission.status = "Expired"
            self.db.commit()
            raise ValueError("Cannot approve permission because its return time has already passed.")

        permission.status = "Approved"
        permission.approved_by = admin_name
        permission.approved_at = now_utc
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def reject_permission(self, permission_id: int, admin_name: str = "Admin", reason: str = "") -> HostelPermission:
        permission = self.get_permission_by_id(permission_id)
        if not permission:
            raise KeyError(f"Permission with ID {permission_id} not found.")

        if permission.status not in ("Pending", "Approved"):
            raise ValueError(f"Cannot reject permission in '{permission.status}' status.")

        permission.status = "Rejected"
        permission.rejection_reason = reason.strip() or "Rejected by administrator"
        permission.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def list_active_outings(self, status: Optional[str] = None, skip: int = 0, limit: int = 50) -> Tuple[int, List[ActiveOuting]]:
        # Update overdue outings first
        self.check_overdue_outings()

        stmt = select(ActiveOuting)
        if status:
            stmt = stmt.where(ActiveOuting.status == status)
        else:
            # By default, active outings are those not yet returned ('Out' or 'Late')
            stmt = stmt.where(ActiveOuting.status.in_(["Out", "Late"]))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = stmt.order_by(ActiveOuting.actual_exit_time.desc()).offset(skip).limit(limit)
        items = list(self.db.scalars(stmt).all())
        return total, items

    def list_security_alerts(self, unresolved_only: bool = False, skip: int = 0, limit: int = 50) -> Tuple[int, List[SecurityAlert]]:
        stmt = select(SecurityAlert)
        if unresolved_only:
            stmt = stmt.where(SecurityAlert.is_resolved == False)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = stmt.order_by(SecurityAlert.created_at.desc()).offset(skip).limit(limit)
        items = list(self.db.scalars(stmt).all())
        return total, items

    def resolve_alert(self, alert_id: int, admin_name: str = "Admin") -> SecurityAlert:
        alert = self.db.scalar(select(SecurityAlert).where(SecurityAlert.id == alert_id))
        if not alert:
            raise KeyError(f"Alert with ID {alert_id} not found.")
        alert.is_resolved = True
        alert.resolved_by = admin_name
        alert.resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_stats(self) -> HostelPermissionStatsResponse:
        """Calculate high-level dashboard and management metrics."""
        self.auto_expire_permissions()
        self.check_overdue_outings()

        total = self.db.scalar(select(func.count(HostelPermission.id))) or 0
        pending = self.db.scalar(select(func.count(HostelPermission.id)).where(HostelPermission.status == "Pending")) or 0
        approved = self.db.scalar(select(func.count(HostelPermission.id)).where(HostelPermission.status == "Approved")) or 0
        used = self.db.scalar(select(func.count(HostelPermission.id)).where(HostelPermission.status == "Used")) or 0
        rejected = self.db.scalar(select(func.count(HostelPermission.id)).where(HostelPermission.status == "Rejected")) or 0
        expired = self.db.scalar(select(func.count(HostelPermission.id)).where(HostelPermission.status == "Expired")) or 0

        active_outings = self.db.scalar(select(func.count(ActiveOuting.id)).where(ActiveOuting.status.in_(["Out", "Late"]))) or 0
        late_returns = self.db.scalar(select(func.count(ActiveOuting.id)).where(ActiveOuting.status == "Late")) or 0

        return HostelPermissionStatsResponse(
            total_permissions=total,
            pending_count=pending,
            approved_count=approved,
            used_count=used,
            rejected_count=rejected,
            expired_count=expired,
            active_outings_count=active_outings,
            late_returns_count=late_returns,
        )

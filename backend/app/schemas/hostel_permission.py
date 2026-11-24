"""
Pydantic Request & Response schemas for the Hostel Exit Permission System.
Timestamps serialize with timezone awareness (+00:00) so frontend converts accurately to IST.
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HostelPermissionCreate(BaseModel):
    """Payload to create a new exit permission request."""
    student_id: str = Field(..., description="Student registration ID")
    student_name: Optional[str] = Field(None, description="Optional name override; defaults to student's registered name")
    reason: str = Field(..., min_length=2, max_length=500, description="Reason for exit/outing")
    departure_date: str = Field(..., description="Departure date in YYYY-MM-DD")
    departure_time: str = Field(..., description="Departure time in HH:MM or HH:MM:SS")
    expected_return_date: str = Field(..., description="Expected return date in YYYY-MM-DD")
    expected_return_time: str = Field(..., description="Expected return time in HH:MM or HH:MM:SS")


class HostelPermissionReject(BaseModel):
    """Payload to reject a pending permission request."""
    rejection_reason: str = Field(..., min_length=2, max_length=500, description="Reason for rejection")


class HostelPermissionResponse(BaseModel):
    """Complete representation of a hostel exit permission."""
    id: int
    student_id: str
    student_name: str
    reason: str
    departure_date: str
    departure_time: str
    valid_from: datetime
    expected_return_date: str
    expected_return_time: str
    valid_until: datetime
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('valid_from', 'valid_until', 'approved_at', 'used_at', 'created_at', 'updated_at', mode='before')
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class HostelPermissionListResponse(BaseModel):
    """Paginated permission listing response."""
    total: int
    items: List[HostelPermissionResponse]
    skip: int
    limit: int


class ActiveOutingResponse(BaseModel):
    """Hosteller currently on active outing."""
    id: int
    permission_id: int
    student_id: str
    student_name: str
    hostel_name: Optional[str] = None
    hostel_block: Optional[str] = None
    room_number: Optional[str] = None
    actual_exit_time: datetime
    expected_return_time: datetime
    actual_return_time: Optional[datetime] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('actual_exit_time', 'expected_return_time', 'actual_return_time', 'created_at', mode='before')
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class ActiveOutingListResponse(BaseModel):
    total: int
    items: List[ActiveOutingResponse]


class SecurityAlertResponse(BaseModel):
    id: int
    alert_type: str
    severity: str
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    gate_id: str
    description: str
    is_resolved: bool
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('resolved_at', 'created_at', mode='before')
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class SecurityAlertListResponse(BaseModel):
    total: int
    items: List[SecurityAlertResponse]


class HostelPermissionStatsResponse(BaseModel):
    total_permissions: int
    pending_count: int
    approved_count: int
    used_count: int
    rejected_count: int
    expired_count: int
    active_outings_count: int
    late_returns_count: int

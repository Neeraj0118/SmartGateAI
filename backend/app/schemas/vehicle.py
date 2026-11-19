"""
Pydantic schemas for Vehicle Registration API.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator
import re


VEHICLE_TYPES = ["car", "motorcycle", "bicycle", "bus", "truck", "auto", "other"]


class VehicleCreateRequest(BaseModel):
    vehicle_number: str
    owner_name: str
    vehicle_type: str = "car"
    vehicle_make: Optional[str] = None
    vehicle_color: Optional[str] = None
    associated_student_id: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("vehicle_number")
    @classmethod
    def normalise_number(cls, v: str) -> str:
        v = v.strip().upper().replace(" ", "").replace("-", "")
        if not v:
            raise ValueError("Vehicle number cannot be empty")
        return v

    @field_validator("vehicle_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VEHICLE_TYPES:
            raise ValueError(f"vehicle_type must be one of: {VEHICLE_TYPES}")
        return v

    @field_validator("owner_name")
    @classmethod
    def validate_owner(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Owner name cannot be empty")
        return v


class VehicleUpdateRequest(BaseModel):
    owner_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_color: Optional[str] = None
    associated_student_id: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_number: str
    owner_name: str
    vehicle_type: str
    vehicle_make: Optional[str] = None
    vehicle_color: Optional[str] = None
    associated_student_id: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VehicleListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    items: List[VehicleResponse]
    skip: int
    limit: int

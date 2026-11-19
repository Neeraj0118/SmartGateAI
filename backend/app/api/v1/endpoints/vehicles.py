"""
Vehicle Registration API endpoints for SmartGateAI.
Provides CRUD for manually registered vehicles (admin only).
Automatic number-plate recognition is a planned future module.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import require_admin, get_db_session
from app.models.vehicle import VehicleRegistration
from app.schemas.vehicle import (
    VehicleCreateRequest,
    VehicleUpdateRequest,
    VehicleResponse,
    VehicleListResponse,
)

logger = logging.getLogger("SmartGateAI.VehicleEndpoints")
router = APIRouter()


@router.get("/", response_model=VehicleListResponse)
def list_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None, description="Search vehicle number or owner name"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """List registered vehicles with optional search/filter (admin only)."""
    stmt = select(VehicleRegistration)
    if active_only:
        stmt = stmt.where(VehicleRegistration.is_active == True)
    if search:
        q = f"%{search}%"
        stmt = stmt.where(
            VehicleRegistration.vehicle_number.ilike(q)
            | VehicleRegistration.owner_name.ilike(q)
        )

    total: int = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(VehicleRegistration.created_at.desc()).offset(skip).limit(limit)
    rows = db.execute(stmt).scalars().all()

    return VehicleListResponse(
        total=total,
        items=[VehicleResponse.model_validate(r) for r in rows],
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def register_vehicle(
    payload: VehicleCreateRequest,
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """Register a new vehicle (admin only)."""
    # Check for duplicate vehicle number
    existing = db.execute(
        select(VehicleRegistration).where(
            VehicleRegistration.vehicle_number == payload.vehicle_number
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle number '{payload.vehicle_number}' is already registered.",
        )

    vehicle = VehicleRegistration(
        vehicle_number=payload.vehicle_number,
        owner_name=payload.owner_name,
        vehicle_type=payload.vehicle_type,
        vehicle_make=payload.vehicle_make,
        vehicle_color=payload.vehicle_color,
        associated_student_id=payload.associated_student_id,
        notes=payload.notes,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    logger.info("Registered vehicle %s for %s", vehicle.vehicle_number, vehicle.owner_name)
    return VehicleResponse.model_validate(vehicle)


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """Get a single vehicle registration by ID (admin only)."""
    v = db.get(VehicleRegistration, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return VehicleResponse.model_validate(v)


@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdateRequest,
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """Update vehicle registration details (admin only)."""
    v = db.get(VehicleRegistration, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(v, field, value)
    db.commit()
    db.refresh(v)
    return VehicleResponse.model_validate(v)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db_session),
    _: str = Depends(require_admin),
):
    """Soft-delete a vehicle registration (sets is_active=False) (admin only)."""
    v = db.get(VehicleRegistration, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    v.is_active = False
    db.commit()
    logger.info("Soft-deleted vehicle %s (id=%d)", v.vehicle_number, v.id)

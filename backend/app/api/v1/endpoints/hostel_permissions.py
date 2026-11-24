"""
API endpoints for Hostel Exit Permission Management.
Protected by administrator authentication header ('X-Admin-API-Key').
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin, get_db_session
from app.schemas.student import MessageResponse
from app.schemas.hostel_permission import (
    HostelPermissionCreate,
    HostelPermissionReject,
    HostelPermissionResponse,
    HostelPermissionListResponse,
    ActiveOutingListResponse,
    ActiveOutingResponse,
    SecurityAlertListResponse,
    SecurityAlertResponse,
    HostelPermissionStatsResponse,
)
from app.services.hostel_permission_service import HostelPermissionService

router = APIRouter()


@router.post(
    "",
    response_model=HostelPermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Hostel Exit Permission Request"
)
def create_permission(
    payload: HostelPermissionCreate,
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    try:
        permission = service.create_permission(payload)
        return HostelPermissionResponse.model_validate(permission)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation failed: {e}")


@router.get(
    "",
    response_model=HostelPermissionListResponse,
    summary="List Hostel Exit Permissions"
)
def list_permissions(
    status: Optional[str] = Query(None, description="Filter by status: Pending, Approved, Rejected, Used, Expired"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    search: Optional[str] = Query(None, description="Search by ID, name, or reason"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    total, items = service.list_permissions(
        status=status,
        student_id=student_id,
        search=search,
        skip=skip,
        limit=limit
    )
    return HostelPermissionListResponse(
        total=total,
        items=[HostelPermissionResponse.model_validate(p) for p in items],
        skip=skip,
        limit=limit
    )


@router.get(
    "/stats",
    response_model=HostelPermissionStatsResponse,
    summary="Get Hostel Permission & Outing Statistics"
)
def get_permission_stats(
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    return service.get_stats()


@router.get(
    "/outings/active",
    response_model=ActiveOutingListResponse,
    summary="List Students Currently on Active Outing"
)
def list_active_outings(
    status: Optional[str] = Query(None, description="Filter by status: 'Out', 'Late', 'Returned'"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    total, items = service.list_active_outings(status=status, skip=skip, limit=limit)
    return ActiveOutingListResponse(
        total=total,
        items=[ActiveOutingResponse.model_validate(o) for o in items]
    )


@router.get(
    "/alerts",
    response_model=SecurityAlertListResponse,
    summary="List Hostel Security Alerts (Late Returns, Denied Exits)"
)
def list_security_alerts(
    unresolved_only: bool = Query(False, description="Filter for unresolved alerts only"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    total, items = service.list_security_alerts(unresolved_only=unresolved_only, skip=skip, limit=limit)
    return SecurityAlertListResponse(
        total=total,
        items=[SecurityAlertResponse.model_validate(a) for a in items]
    )


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=SecurityAlertResponse,
    summary="Mark a Security Alert as Resolved"
)
def resolve_security_alert(
    alert_id: int,
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    try:
        resolved = service.resolve_alert(alert_id, admin_name="Administrator")
        return SecurityAlertResponse.model_validate(resolved)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{permission_id}",
    response_model=HostelPermissionResponse,
    summary="Get Permission Request Details"
)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    permission = service.get_permission_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Permission {permission_id} not found.")
    return HostelPermissionResponse.model_validate(permission)


@router.post(
    "/{permission_id}/approve",
    response_model=HostelPermissionResponse,
    summary="Approve a Pending Permission Request"
)
def approve_permission(
    permission_id: int,
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    try:
        approved = service.approve_permission(permission_id, admin_name="Administrator")
        return HostelPermissionResponse.model_validate(approved)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{permission_id}/reject",
    response_model=HostelPermissionResponse,
    summary="Reject a Permission Request"
)
def reject_permission(
    permission_id: int,
    payload: HostelPermissionReject,
    db: Session = Depends(get_db_session),
    _admin: str = Depends(require_admin)
):
    service = HostelPermissionService(db)
    try:
        rejected = service.reject_permission(
            permission_id,
            admin_name="Administrator",
            reason=payload.rejection_reason
        )
        return HostelPermissionResponse.model_validate(rejected)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

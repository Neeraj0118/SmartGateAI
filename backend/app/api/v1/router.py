"""
Master API v1 Router consolidating all sub-routers.
"""

from fastapi import APIRouter
from .endpoints.health import router as health_router
from .endpoints.students import router as students_router
from .endpoints.camera import router as camera_router
from .endpoints.attendance import router as attendance_router
from .endpoints.vehicles import router as vehicles_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router, prefix="", tags=["System Health"])
api_v1_router.include_router(students_router, prefix="/students", tags=["Student Management"])
api_v1_router.include_router(camera_router, prefix="/camera", tags=["Camera"])
api_v1_router.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
api_v1_router.include_router(vehicles_router, prefix="/vehicles", tags=["Vehicles"])

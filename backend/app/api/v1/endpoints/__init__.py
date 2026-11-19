# SmartGateAI Endpoints Package
from .health import router as health_router
from .students import router as students_router

__all__ = ["health_router", "students_router"]

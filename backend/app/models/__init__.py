# SmartGateAI Models Package
from .student import Student, FaceEmbedding
from .recognition_event import RecognitionEvent
from .vehicle import VehicleRegistration
from .hostel_permission import HostelPermission, ActiveOuting, SecurityAlert

__all__ = [
    "Student",
    "FaceEmbedding",
    "RecognitionEvent",
    "VehicleRegistration",
    "HostelPermission",
    "ActiveOuting",
    "SecurityAlert",
]

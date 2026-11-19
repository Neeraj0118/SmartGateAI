# SmartGateAI AI Services Package
from .base import FaceEngine, FaceDetectionResult
from .opencv_engine import OpenCVFaceEngine
from .vector_matcher import VectorMatcher, EnrolledPerson, RecognitionResult
from .quality import validate_enrollment_image, compute_blur_score

__all__ = [
    "FaceEngine",
    "FaceDetectionResult",
    "OpenCVFaceEngine",
    "VectorMatcher",
    "EnrolledPerson",
    "RecognitionResult",
    "validate_enrollment_image",
    "compute_blur_score",
]

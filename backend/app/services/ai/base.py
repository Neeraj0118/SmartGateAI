"""
Abstract Base Class for Face Detection & Recognition Engines.
Allows seamless swapping between OpenCV Zoo (YuNet+SFace), InsightFace (SCRFD+ArcFace),
or other ONNX-based engines without modifying upstream business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np


@dataclass
class FaceDetectionResult:
    """Standardized face detection output."""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    landmarks: np.ndarray            # 5 keypoints: [(x, y), ...]
    confidence: float                # Detection score [0.0, 1.0]
    raw_face_data: Optional[np.ndarray] = None  # Underlying engine metadata if needed


class FaceEngine(ABC):
    """Abstract interface for all face detection and recognition engines."""

    @abstractmethod
    def load_models(self, detector_path: str, recognizer_path: str) -> None:
        """Initialize and load detection and recognition models into memory."""
        pass

    @abstractmethod
    def detect_faces(
        self,
        image: np.ndarray,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3
    ) -> List[FaceDetectionResult]:
        """
        Detect all faces in an input BGR image.
        Returns list of FaceDetectionResult objects.
        """
        pass

    @abstractmethod
    def align_crop(self, image: np.ndarray, detection: FaceDetectionResult) -> np.ndarray:
        """
        Align and crop face using 5 facial landmarks to canonical orientation (112x112).
        """
        pass

    @abstractmethod
    def extract_embedding(self, aligned_crop: np.ndarray) -> np.ndarray:
        """
        Extract normalized feature embedding vector from an aligned face crop.
        Returns 1D float32 array (e.g. 128-D for SFace, 512-D for ArcFace).
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Return the exact embedding dimensionality produced by the recognizer model.
        """
        pass

    @abstractmethod
    def compute_similarity(self, embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
        """
        Compute cosine similarity between two feature vectors: dot(a, b) / (||a|| * ||b||).
        Returns a float in [-1.0, 1.0].
        """
        pass

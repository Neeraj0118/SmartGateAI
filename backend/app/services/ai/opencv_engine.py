"""
Concrete FaceEngine implementation utilizing OpenCV Zoo models:
- YuNet: Efficient anchor-based face detection (Apache 2.0)
- SFace: 128-dimensional hyperspherical feature representation (Apache 2.0)
"""

import os
from typing import List, Tuple, Optional
import cv2
import numpy as np
from .base import FaceEngine, FaceDetectionResult


class OpenCVFaceEngine(FaceEngine):
    """
    OpenCV Zoo implementation using cv2.FaceDetectorYN and cv2.FaceRecognizerSF.
    """

    def __init__(
        self,
        detector_path: Optional[str] = None,
        recognizer_path: Optional[str] = None
    ) -> None:
        self.detector: Optional[cv2.FaceDetectorYN] = None
        self.recognizer: Optional[cv2.FaceRecognizerSF] = None
        self.detector_path = detector_path
        self.recognizer_path = recognizer_path
        self._embedding_dim = 128  # Default for SFace, updated dynamically on first inference

        if detector_path and recognizer_path:
            self.load_models(detector_path, recognizer_path)

    def load_models(self, detector_path: str, recognizer_path: str) -> None:
        if not os.path.exists(detector_path):
            raise FileNotFoundError(f"YuNet model file not found at: {detector_path}")
        if not os.path.exists(recognizer_path):
            raise FileNotFoundError(f"SFace model file not found at: {recognizer_path}")

        # Initialize YuNet detector with placeholder size (updated per image)
        self.detector = cv2.FaceDetectorYN.create(
            model=detector_path,
            config="",
            input_size=(320, 320),
            score_threshold=0.6,
            nms_threshold=0.3,
            top_k=5000
        )

        # Initialize SFace recognizer
        self.recognizer = cv2.FaceRecognizerSF.create(
            model=recognizer_path,
            config=""
        )

        self.detector_path = detector_path
        self.recognizer_path = recognizer_path

    def detect_faces(
        self,
        image: np.ndarray,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3
    ) -> List[FaceDetectionResult]:
        if self.detector is None:
            raise RuntimeError("Face detector model is not loaded. Call load_models() first.")

        ih, iw = image.shape[:2]
        self.detector.setInputSize((iw, ih))
        self.detector.setScoreThreshold(score_threshold)
        self.detector.setNMSThreshold(nms_threshold)

        _, raw_faces = self.detector.detect(image)

        results: List[FaceDetectionResult] = []
        if raw_faces is None or len(raw_faces) == 0:
            return results

        for face in raw_faces:
            x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            score = float(face[-1])

            # Extract 5 landmarks: right eye, left eye, nose, right mouth, left mouth
            landmarks = np.array([
                [face[4], face[5]],
                [face[6], face[7]],
                [face[8], face[9]],
                [face[10], face[11]],
                [face[12], face[13]]
            ], dtype=np.float32)

            results.append(
                FaceDetectionResult(
                    bbox=(x, y, w, h),
                    landmarks=landmarks,
                    confidence=score,
                    raw_face_data=face
                )
            )

        return results

    def align_crop(self, image: np.ndarray, detection: FaceDetectionResult) -> np.ndarray:
        if self.recognizer is None:
            raise RuntimeError("Face recognizer model is not loaded. Call load_models() first.")

        if detection.raw_face_data is None:
            # Reconstruct raw face row [x, y, w, h, lm0_x, lm0_y, ..., score]
            x, y, w, h = detection.bbox
            raw = [float(x), float(y), float(w), float(h)]
            for lm in detection.landmarks:
                raw.extend([float(lm[0]), float(lm[1])])
            raw.append(float(detection.confidence))
            face_row = np.array(raw, dtype=np.float32)
        else:
            face_row = detection.raw_face_data

        aligned_crop = self.recognizer.alignCrop(image, face_row)
        return aligned_crop

    def extract_embedding(self, aligned_crop: np.ndarray) -> np.ndarray:
        if self.recognizer is None:
            raise RuntimeError("Face recognizer model is not loaded. Call load_models() first.")

        # SFace produces 1x128 feature vector
        feature = self.recognizer.feature(aligned_crop)
        emb = feature.flatten().astype(np.float32)

        # L2-normalize vector to guarantee unit length
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        self._embedding_dim = int(emb.shape[0])
        return emb

    def get_embedding_dimension(self) -> int:
        return self._embedding_dim

    def compute_similarity(self, embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
        norm_a = np.linalg.norm(embedding_a)
        norm_b = np.linalg.norm(embedding_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        dot_product = float(np.dot(embedding_a, embedding_b))
        cosine_sim = dot_product / (norm_a * norm_b)
        return float(np.clip(cosine_sim, -1.0, 1.0))

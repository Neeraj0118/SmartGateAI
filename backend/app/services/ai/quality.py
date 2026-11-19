"""
Face image quality validation and enrollment sanity checks.
Ensures that registered photos meet minimum standards for blur, resolution, and pose.
"""

from typing import List, Tuple
import cv2
import numpy as np
from .base import FaceDetectionResult


def compute_blur_score(image: np.ndarray, bbox: Tuple[int, int, int, int] = None) -> float:
    """
    Compute blur metric using variance of the Laplacian.
    Higher values indicate a sharper image; low values indicate motion or focus blur.
    """
    if bbox is not None:
        x, y, w, h = bbox
        ih, iw = image.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(iw, x + w)
        y2 = min(ih, y + h)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        crop = image[y1:y2, x1:x2]
    else:
        crop = image

    if len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def check_pose_symmetry(landmarks: np.ndarray) -> Tuple[bool, float]:
    """
    Check horizontal face symmetry to reject extreme profile faces during enrollment.
    landmarks format: 5 points (re, le, nt, rcm, lcm).
    Returns (is_acceptable, asymmetry_ratio).
    """
    if landmarks is None or len(landmarks) < 5:
        return True, 0.0

    # Right eye, Left eye, Nose tip
    re_x = landmarks[0][0]
    le_x = landmarks[1][0]
    nt_x = landmarks[2][0]

    d_right = abs(nt_x - re_x)
    d_left = abs(le_x - nt_x)

    if d_right + d_left == 0:
        return False, 1.0

    # Ratio between the smaller and larger eye-to-nose horizontal distance
    ratio = min(d_right, d_left) / max(d_right, d_left)
    # If ratio is too small (< 0.25), face is turned sideways past ~40 degrees
    is_acceptable = ratio >= 0.20
    return is_acceptable, float(ratio)


def validate_enrollment_image(
    image: np.ndarray,
    detections: List[FaceDetectionResult],
    min_face_size: int = 60,
    min_blur_score: float = 60.0,
    min_confidence: float = 0.70
) -> Tuple[bool, str, float]:
    """
    Validate that an uploaded photograph is suitable for enrollment:
    1. Exactly one face must be present.
    2. Face must have high detection confidence.
    3. Face bounding box must meet minimum resolution requirements.
    4. Image must not be blurred.
    5. Face must not be at an extreme profile angle.

    Returns:
        (is_valid: bool, error_message: str, quality_score: float)
    """
    if image is None or image.size == 0:
        return False, "Image data is empty or corrupt.", 0.0

    num_faces = len(detections)
    if num_faces == 0:
        return False, "No face detected in the photograph. Ensure proper lighting and face visibility.", 0.0

    if num_faces > 1:
        return False, f"Enrollment photo must contain exactly 1 face, but {num_faces} faces were detected.", 0.0

    det = detections[0]
    if det.confidence < min_confidence:
        return False, f"Face detection confidence too low ({det.confidence:.2f} < {min_confidence:.2f}).", 0.0

    x, y, w, h = det.bbox
    if w < min_face_size or h < min_face_size:
        return False, f"Face resolution too small ({w}x{h} px; minimum required: {min_face_size}x{min_face_size} px).", 0.0

    # Blur validation
    blur_score = compute_blur_score(image, det.bbox)
    if blur_score < min_blur_score:
        return False, f"Image is blurry (sharpness score {blur_score:.1f} < {min_blur_score:.1f}). Please upload a clearer photo.", blur_score

    # Pose validation
    is_pose_ok, symmetry = check_pose_symmetry(det.landmarks)
    if not is_pose_ok:
        return False, f"Face is turned at an extreme profile angle. Please look directly towards the camera.", blur_score

    return True, "Valid enrollment photo", blur_score

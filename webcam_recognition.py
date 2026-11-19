"""
SmartGateAI – Phase 4: Live Webcam Face Recognition
=====================================================
Standalone script.  Reuses the existing AI engine (YuNet + SFace), VectorMatcher,
and SQLite student database without duplicating any pipeline logic.

Controls
--------
  Q  or  ESC  — stop camera and exit
  R           — reload student embeddings from DB (live enrollment sync)
  P           — pause / unpause recognition overlay

Usage
-----
  cd C:\\Users\\neera\\OneDrive\\Desktop\\SmartGateAI
  .\\venv\\Scripts\\python.exe webcam_recognition.py

Optional args
  --camera  INT        webcam device index (default: 0)
  --width   INT        capture width in px   (default: 640)
  --height  INT        capture height in px  (default: 480)
  --fps     INT        target FPS throttle   (default: 30)
  --threshold FLOAT    similarity threshold override (default: from config 0.637)
"""

import sys
import os
import time
import argparse
import logging
from collections import deque
from typing import List, Optional

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Bootstrap: add backend/ to Python path so existing app modules import cleanly
# ---------------------------------------------------------------------------
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_SCRIPT_DIR, "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.config import settings
from app.db.session import get_engine
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import select

from app.models.student import Student
from app.services.ai.opencv_engine import OpenCVFaceEngine
from app.services.ai.vector_matcher import VectorMatcher, RecognitionResult

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("SmartGateAI.Webcam")


# ---------------------------------------------------------------------------
# Colour palette  (BGR)
# ---------------------------------------------------------------------------
COL_KNOWN    = (0, 220, 60)     # green   – recognised student
COL_UNKNOWN  = (0, 50, 230)     # red     – unknown / rejected
COL_LABEL_BG = (10, 10, 10)     # near-black background strip
COL_WHITE    = (255, 255, 255)
COL_YELLOW   = (0, 215, 255)
COL_GRAY     = (160, 160, 160)

_FONT       = cv2.FONT_HERSHEY_DUPLEX
_FONT_SMALL = cv2.FONT_HERSHEY_SIMPLEX


# ---------------------------------------------------------------------------
# DB → VectorMatcher cache loader
# Replicates StudentService.sync_cache_from_db but standalone (no FastAPI deps).
# Uses joinedload to avoid DetachedInstanceError with lazy relationships.
# ---------------------------------------------------------------------------
def load_students_into_matcher(matcher: VectorMatcher) -> int:
    """
    Pull every active student + their embeddings from SQLite and populate
    the in-memory VectorMatcher registry.  Clears stale data first.
    Returns count of enrolled identities now in cache.
    """
    engine_db = get_engine(settings.DATABASE_URL)
    Session   = sessionmaker(bind=engine_db)
    db        = Session()

    try:
        students = db.scalars(
            select(Student)
            .options(joinedload(Student.embeddings))   # eager-load embeddings in one query
            .where(Student.is_active == True)
        ).unique().all()

        # Wipe registry before reload to avoid stale data
        matcher.registry.clear()

        for student in students:
            if not student.embeddings:
                continue

            person = matcher.enroll_person(
                person_id  = student.student_id,
                name       = student.full_name,
                department = student.department,
            )
            person.embeddings.clear()   # prevent duplicate accumulation on reload

            for emb_record in student.embeddings:
                emb_vec = emb_record.to_numpy()
                person.add_embedding(emb_vec)

        count = matcher.get_enrolled_count()
        log.info("Loaded %d active student(s) into recognition cache.", count)
        return count

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def _text_size(text: str, font, scale: float, thickness: int):
    (w, h), baseline = cv2.getTextSize(text, font, scale, thickness)
    return w, h, baseline


def draw_face_box(frame: np.ndarray, result: RecognitionResult) -> None:
    """Draw bounding box, 5 landmarks, and an informative label strip."""
    x, y, w, h = result.bbox
    colour = COL_KNOWN if result.is_recognised else COL_UNKNOWN

    # Bounding box
    cv2.rectangle(frame, (x, y), (x + w, y + h), colour, 2)

    # 5 facial landmarks
    if result.landmarks is not None:
        for lm in result.landmarks:
            cv2.circle(frame, (int(lm[0]), int(lm[1])), 2, colour, -1)

    # Build label text
    if result.is_recognised:
        line1 = result.assigned_name
        line2 = f"ID: {result.assigned_person_id}  |  sim: {result.similarity_score:.2f}"
    else:
        line1 = "UNKNOWN"
        line2 = f"best sim: {result.similarity_score:.2f}"

    tw1, th1, _ = _text_size(line1, _FONT,       0.52, 1)
    tw2, th2, _ = _text_size(line2, _FONT_SMALL, 0.38, 1)
    strip_w = max(tw1, tw2) + 14
    strip_h = th1 + th2 + 18
    strip_y = max(0, y - strip_h)

    # Dark label background
    cv2.rectangle(frame, (x, strip_y), (x + strip_w, strip_y + strip_h), COL_LABEL_BG, -1)

    # Name line
    cv2.putText(frame, line1, (x + 5, strip_y + th1 + 4),
                _FONT, 0.52, colour, 1, cv2.LINE_AA)

    # Secondary detail line
    cv2.putText(frame, line2, (x + 5, strip_y + th1 + th2 + 12),
                _FONT_SMALL, 0.38, COL_GRAY, 1, cv2.LINE_AA)


def draw_hud(
    frame: np.ndarray,
    fps: float,
    enrolled: int,
    faces_detected: int,
    recognised: int,
    paused: bool,
) -> None:
    """Overlay top-left status HUD and bottom control hint bar."""
    h_frame = frame.shape[0]

    lines = [
        f"FPS: {fps:5.1f}",
        f"Enrolled students: {enrolled}",
        f"Faces in frame:    {faces_detected}  |  Known: {recognised}",
    ]
    if paused:
        lines.insert(0, "** PAUSED — press P to resume **")

    for i, txt in enumerate(lines):
        y_pos  = 24 + i * 22
        colour = COL_YELLOW if (paused and i == 0) else COL_WHITE
        cv2.putText(frame, txt, (10, y_pos), _FONT_SMALL, 0.52, colour, 1, cv2.LINE_AA)

    hint = "Q / ESC = quit    R = reload DB    P = pause"
    cv2.putText(frame, hint, (10, h_frame - 10), _FONT_SMALL, 0.40, COL_GRAY, 1, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Rolling FPS meter
# ---------------------------------------------------------------------------
class FPSMeter:
    def __init__(self, window: int = 30):
        self._times: deque = deque(maxlen=window)
        self._last  = time.perf_counter()

    def tick(self) -> float:
        now = time.perf_counter()
        self._times.append(now - self._last)
        self._last = now
        avg = sum(self._times) / len(self._times) if self._times else 1.0
        return 1.0 / avg if avg > 0 else 0.0


# ---------------------------------------------------------------------------
# Main recognition loop
# ---------------------------------------------------------------------------
def run_webcam(
    camera_index       : int            = 0,
    capture_w          : int            = 640,
    capture_h          : int            = 480,
    target_fps         : int            = 30,
    threshold_override : Optional[float]= None,
) -> None:

    threshold = threshold_override if threshold_override is not None \
                else settings.FACE_SIMILARITY_THRESHOLD

    log.info("=" * 60)
    log.info("  SmartGateAI – Phase 4: Live Webcam Face Recognition")
    log.info("  Models  : YuNet (detection) + SFace 128-D (recognition)")
    log.info("  Threshold: %.3f", threshold)
    log.info("=" * 60)

    # --- Load AI engine (existing, unmodified) ---
    log.info("Loading YuNet + SFace models …")
    engine  = OpenCVFaceEngine(settings.YUNET_MODEL_PATH, settings.SFACE_MODEL_PATH)
    matcher = VectorMatcher(engine, similarity_threshold=threshold)
    log.info("Engine ready. Embedding dim: %d", engine.get_embedding_dimension())

    # --- Populate recognition cache from SQLite ---
    enrolled_count = load_students_into_matcher(matcher)
    if enrolled_count == 0:
        log.warning("No enrolled students found. Recognition will show UNKNOWN for all faces.")
        log.warning("Enroll students via the FastAPI admin API first, then press R to reload.")

    # --- Open webcam ---
    log.info("Opening webcam (device index %d) …", camera_index)
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)   # DirectShow = lower latency on Windows
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)               # generic fallback
    if not cap.isOpened():
        log.error("Cannot open webcam device %d.  Exiting.", camera_index)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  capture_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, capture_h)
    cap.set(cv2.CAP_PROP_FPS,          target_fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)                 # minimise capture latency

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    log.info("Webcam open: %dx%d", actual_w, actual_h)
    log.info("Controls: Q/ESC = quit | R = reload DB | P = pause")

    win_title = "SmartGateAI – Live Face Recognition (Q to quit)"
    cv2.namedWindow(win_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_title, actual_w, actual_h)

    fps_meter    = FPSMeter(window=30)
    paused       = False
    last_results : List[RecognitionResult] = []
    frame_interval = 1.0 / target_fps if target_fps > 0 else 0.0

    while True:
        t0 = time.perf_counter()

        ret, frame = cap.read()
        if not ret or frame is None:
            log.warning("Frame capture failed — retrying …")
            time.sleep(0.05)
            continue

        fps = fps_meter.tick()

        # --- Key handling (1 ms poll = non-blocking) ---
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):       # Q or ESC → quit
            log.info("Exit requested by user.")
            break
        elif key in (ord('p'), ord('P')):          # P → pause/resume
            paused = not paused
            log.info("Recognition %s.", "paused" if paused else "resumed")
        elif key in (ord('r'), ord('R')):          # R → reload from DB
            log.info("Reloading student embeddings from database …")
            enrolled_count = load_students_into_matcher(matcher)
            log.info("Reload complete: %d student(s) in cache.", enrolled_count)

        # --- Face detection + recognition (skipped when paused) ---
        if not paused:
            detections = engine.detect_faces(frame, score_threshold=0.60, nms_threshold=0.30)
            last_results = matcher.recognise_frame_faces(frame, detections) if detections else []

        # --- Compose display frame ---
        display = frame.copy()

        recognised_count = sum(1 for r in last_results if r.is_recognised)
        for result in last_results:
            draw_face_box(display, result)

        draw_hud(
            display,
            fps            = fps,
            enrolled       = enrolled_count,
            faces_detected = len(last_results),
            recognised     = recognised_count,
            paused         = paused,
        )

        cv2.imshow(win_title, display)

        # Throttle loop to target FPS
        elapsed = time.perf_counter() - t0
        sleep_t = frame_interval - elapsed
        if sleep_t > 0.001:
            time.sleep(sleep_t)

    # --- Clean shutdown ---
    cap.release()
    cv2.destroyAllWindows()
    log.info("Webcam released. SmartGateAI Phase 4 shut down cleanly.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="SmartGateAI Phase 4 – Live Webcam Face Recognition"
    )
    p.add_argument("--camera",    type=int,   default=0,
                   help="Webcam device index (default: 0)")
    p.add_argument("--width",     type=int,   default=640,
                   help="Capture width in pixels (default: 640)")
    p.add_argument("--height",    type=int,   default=480,
                   help="Capture height in pixels (default: 480)")
    p.add_argument("--fps",       type=int,   default=30,
                   help="Target FPS cap (default: 30)")
    p.add_argument("--threshold", type=float, default=None,
                   help="Cosine similarity threshold override (default: 0.637 from config)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_webcam(
        camera_index       = args.camera,
        capture_w          = args.width,
        capture_h          = args.height,
        target_fps         = args.fps,
        threshold_override = args.threshold,
    )

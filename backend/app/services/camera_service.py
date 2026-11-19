"""
Singleton Camera Service for SmartGateAI.
Manages a background thread that reads from the webcam, runs YuNet face detection
and SFace recognition, annotates frames, and logs recognition events to the DB.

Bug fixes applied:
- recognise_frame_faces() returns List[RecognitionResult] dataclass objects, NOT dicts.
  All .get() calls replaced with direct attribute access.
- Thread crash no longer silently leaves _running=True; thread monitors itself.
- is_running() now also checks thread liveness, not just the _running flag.
- Webcam open failure properly resets _running=False.
- Added thread_alive property for status endpoint accuracy.
- Phase 2: gate_mode support (entry/exit), unknown face logging, explicit captured_at UTC.
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

import cv2
import numpy as np

from ..db.session import SessionLocal
from ..models.recognition_event import RecognitionEvent

logger = logging.getLogger("SmartGateAI.CameraService")


class CameraService:
    """Thread-safe singleton camera manager with face recognition overlay."""

    def __init__(self):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Latest state protected by _lock
        self._latest_frame: Optional[bytes] = None
        self._latest_results: List[dict] = []
        self._fps: float = 0.0
        self._faces_detected: int = 0
        self._known_count: int = 0
        self._unknown_count: int = 0
        self._running: bool = False
        self._thread_error: Optional[str] = None  # last crash message

        # Gate mode (entry/exit)
        self._gate_mode: str = "entry"

        # DB throttling: student_id / "__UNKNOWN__" -> last logged datetime
        self._last_logged: Dict[str, datetime] = {}

        # AI components (set at start)
        self._face_engine = None
        self._matcher = None
        self._cap: Optional[cv2.VideoCapture] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, face_engine, matcher, gate_mode: str = "entry") -> bool:
        """Open webcam and start background processing thread."""
        with self._lock:
            if self._running:
                logger.warning("CameraService already running.")
                return False

        self._face_engine = face_engine
        self._matcher = matcher
        self._thread_error = None
        self._gate_mode = gate_mode

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            logger.error("Failed to open webcam (index 0, CAP_DSHOW).")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        self._cap = cap
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(cap,),
            daemon=True,
            name="CameraServiceThread"
        )
        with self._lock:
            self._running = True
        self._thread.start()
        logger.info("CameraService started (gate_mode=%s).", gate_mode)
        return True

    def stop(self) -> bool:
        """Signal the background thread to stop and release the webcam."""
        with self._lock:
            if not self._running:
                return False

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._release_cap()

        with self._lock:
            self._running = False
            self._latest_frame = None
            self._latest_results = []
            self._fps = 0.0
            self._faces_detected = 0
            self._known_count = 0
            self._unknown_count = 0

        logger.info("CameraService stopped.")
        return True

    def _release_cap(self):
        try:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
        except Exception:
            pass

    def get_jpeg_frame(self) -> Optional[bytes]:
        """Return the latest annotated JPEG frame bytes, or None if unavailable."""
        with self._lock:
            return self._latest_frame

    def get_gate_mode(self) -> str:
        """Return current gate mode ('entry' or 'exit')."""
        return self._gate_mode

    def set_gate_mode(self, mode: str):
        """Set gate mode while camera may be running."""
        with self._lock:
            self._gate_mode = mode
        logger.info("Gate mode changed to: %s", mode)

    def get_status(self) -> dict:
        """Return current camera service status snapshot."""
        thread_alive = self._thread is not None and self._thread.is_alive()
        with self._lock:
            # If _running is True but thread has died, reflect actual state
            actually_running = self._running and thread_alive
            return {
                "running": actually_running,
                "thread_alive": thread_alive,
                "fps": round(self._fps, 1),
                "faces_detected": self._faces_detected,
                "known_count": self._known_count,
                "unknown_count": self._unknown_count,
                "gate_mode": self._gate_mode,
                "results": list(self._latest_results),
                "error": self._thread_error,
            }

    def is_running(self) -> bool:
        """Return True only if the capture thread is actually alive."""
        thread_alive = self._thread is not None and self._thread.is_alive()
        with self._lock:
            return self._running and thread_alive

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _capture_loop(self, cap: cv2.VideoCapture):
        """Main capture-and-annotate loop running in a daemon thread."""
        fps_deque: deque = deque(maxlen=30)
        last_time = time.monotonic()
        consecutive_failures = 0

        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    logger.warning("Failed to read frame from webcam (attempt %d).", consecutive_failures)
                    if consecutive_failures > 30:
                        logger.error("Too many consecutive frame read failures. Stopping camera.")
                        break
                    time.sleep(0.05)
                    continue
                consecutive_failures = 0

                now_mono = time.monotonic()
                interval = now_mono - last_time
                last_time = now_mono
                if interval > 0:
                    fps_deque.append(1.0 / interval)
                fps = float(sum(fps_deque) / len(fps_deque)) if fps_deque else 0.0

                # --- Face detection ---
                try:
                    dets = self._face_engine.detect_faces(frame, score_threshold=0.55)
                except Exception as exc:
                    logger.error("detect_faces error: %s", exc)
                    dets = []

                # --- Recognition (returns List[RecognitionResult] dataclass objects) ---
                rec_results = []
                if dets:
                    try:
                        rec_results = self._matcher.recognise_frame_faces(frame, dets)
                    except Exception as exc:
                        logger.error("recognise_frame_faces error: %s", exc)
                        rec_results = []

                # --- Annotate frame ---
                annotated = frame.copy()
                known_count = 0
                unknown_count = 0

                for r in rec_results:
                    # RecognitionResult attributes: bbox, is_recognised, assigned_name,
                    # assigned_person_id, similarity_score, confidence
                    bbox = r.bbox  # Tuple[int,int,int,int] = (x, y, w, h)
                    is_known = bool(r.is_recognised)
                    name = r.assigned_name if is_known else "Unknown"
                    person_id = r.assigned_person_id if is_known else None
                    similarity = r.similarity_score

                    if is_known:
                        color = (34, 139, 34)   # Forest green BGR
                        known_count += 1
                    else:
                        color = (0, 50, 200)    # Red BGR
                        unknown_count += 1

                    if bbox:
                        try:
                            x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)

                            # Name label above box
                            display = name
                            if person_id:
                                display = f"{name} [{person_id}]"

                            # Background for text readability
                            (tw, th), _ = cv2.getTextSize(display, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                            ty = max(y - 8, th + 4)
                            cv2.rectangle(annotated, (x, ty - th - 4), (x + tw + 4, ty + 2),
                                          color, cv2.FILLED)
                            cv2.putText(
                                annotated, display,
                                (x + 2, ty - 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA
                            )
                            # Similarity score below box
                            if is_known:
                                sim_txt = f"{similarity:.2f}"
                                cv2.putText(annotated, sim_txt, (x, y + h + 16),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
                        except Exception as draw_err:
                            logger.debug("Drawing error: %s", draw_err)

                # HUD overlay — dark background strip for readability
                hud = f"SmartGateAI  FPS:{fps:.1f}  Faces:{len(rec_results)}  Known:{known_count}  Unknown:{unknown_count}  Mode:{self._gate_mode}"
                cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 28), (20, 20, 20), cv2.FILLED)
                cv2.putText(annotated, hud, (8, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

                # Encode to JPEG
                ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
                jpeg_bytes = buf.tobytes() if ok else None

                # Build serialisable result list from RecognitionResult attributes
                serialisable_results = []
                for r in rec_results:
                    bbox_list = []
                    if r.bbox:
                        try:
                            bbox_list = [int(r.bbox[0]), int(r.bbox[1]),
                                         int(r.bbox[2]), int(r.bbox[3])]
                        except Exception:
                            bbox_list = []
                    serialisable_results.append({
                        "person_id": r.assigned_person_id,
                        "name": r.assigned_name,
                        "bbox": bbox_list,
                        "similarity": float(r.similarity_score),
                        "is_known": bool(r.is_recognised),
                    })

                # Update shared state under lock
                with self._lock:
                    self._latest_frame = jpeg_bytes
                    self._latest_results = serialisable_results
                    self._fps = fps
                    self._faces_detected = len(rec_results)
                    self._known_count = known_count
                    self._unknown_count = unknown_count

                # DB logging for all faces (throttled to 1 event/30s per key)
                self._log_faces(rec_results)

        except Exception as fatal:
            err_msg = f"Camera thread fatal error: {fatal}"
            logger.exception(err_msg)
            with self._lock:
                self._thread_error = err_msg
        finally:
            # Always reset running flag when thread exits for any reason
            with self._lock:
                self._running = False
            self._release_cap()
            logger.info("Capture loop exited.")

    def _log_faces(self, rec_results: list):
        """Insert RecognitionEvent rows for newly seen faces (throttled 30s/key).
        Known faces keyed by student_id; unknown faces share '__UNKNOWN__' key.
        """
        now_utc = datetime.now(timezone.utc)
        to_log = []

        for r in rec_results:
            if r.is_recognised:
                key = r.assigned_person_id
            else:
                key = "__UNKNOWN__"
            last = self._last_logged.get(key)
            if last is None or (now_utc - last) > timedelta(seconds=30):
                to_log.append(r)
                self._last_logged[key] = now_utc

        if not to_log:
            return

        try:
            db = SessionLocal()
            try:
                for r in to_log:
                    event = RecognitionEvent(
                        student_id=r.assigned_person_id if r.is_recognised else None,
                        full_name=r.assigned_name if r.is_recognised else None,
                        event_type=self._gate_mode,
                        gate_id=self._gate_mode,
                        similarity=float(r.similarity_score),
                        is_known=bool(r.is_recognised),
                        source="camera",
                        captured_at=datetime.now(timezone.utc),
                    )
                    db.add(event)
                db.commit()
                logger.info("Logged %d recognition event(s) to DB.", len(to_log))
            finally:
                db.close()
        except Exception as exc:
            logger.error("Failed to log recognition event to DB: %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_camera_service_instance: Optional[CameraService] = None
_singleton_lock = threading.Lock()


def get_camera_service() -> CameraService:
    """Return (or create) the global CameraService singleton."""
    global _camera_service_instance
    if _camera_service_instance is None:
        with _singleton_lock:
            if _camera_service_instance is None:
                _camera_service_instance = CameraService()
    return _camera_service_instance

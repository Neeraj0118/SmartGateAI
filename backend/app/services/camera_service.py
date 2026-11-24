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
from typing import Optional, List, Dict, Any

import cv2
import numpy as np
from sqlalchemy import select, and_

from ..db.session import SessionLocal
from ..models.recognition_event import RecognitionEvent
from ..models.student import Student
from ..models.hostel_permission import HostelPermission, ActiveOuting, SecurityAlert

logger = logging.getLogger("SmartGateAI.CameraService")


class CameraService:
    """Thread-safe singleton camera manager with face recognition and hostel exit permission overlay."""

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
        self._active_alert: Optional[dict] = None  # Live alert for frontend HUD/cards

        # Gate mode (entry/exit)
        self._gate_mode: str = "entry"

        # DB throttling: student_id / "__UNKNOWN__" -> last logged datetime
        self._last_logged: Dict[str, datetime] = {}

        # Permission check cache: student_id -> {status, category, message, pass_id, room, hostel}
        self._perm_cache: Dict[str, dict] = {}
        self._last_overdue_check: datetime = datetime.min.replace(tzinfo=timezone.utc)

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
            self._active_alert = None

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
                "active_alert": self._active_alert,
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

                # Process DB logging & permissions for newly seen / throttled faces
                self._process_faces(rec_results)

                # --- Annotate frame ---
                annotated = frame.copy()
                known_count = 0
                unknown_count = 0
                has_denied_exit = False
                denied_student_summary = ""

                for r in rec_results:
                    bbox = r.bbox  # Tuple[int,int,int,int] = (x, y, w, h)
                    is_known = bool(r.is_recognised)
                    name = r.assigned_name if is_known else "Unknown"
                    person_id = r.assigned_person_id if is_known else None
                    similarity = r.similarity_score

                    perm_info = self._perm_cache.get(person_id, {}) if is_known else {}
                    is_exit_denied = (self._gate_mode == "exit" and perm_info.get("status") == "denied")

                    if is_exit_denied:
                        has_denied_exit = True
                        denied_student_summary = f"{name} ({person_id})"

                    if not is_known:
                        color = (0, 0, 220)     # Bright Red BGR
                        unknown_count += 1
                        display_name = "UNKNOWN DETECTED"
                        sub_text = "! NOT ENROLLED !"
                    elif is_exit_denied:
                        color = (0, 0, 220)     # Bright Red for exit denial
                        known_count += 1
                        display_name = f"EXIT DENIED: {name}"
                        sub_text = perm_info.get("message", "NO PASS GENERATED")
                    else:
                        color = (34, 139, 34)   # Forest green BGR
                        known_count += 1
                        if self._gate_mode == "exit":
                            if perm_info.get("category") == "Hosteller":
                                display_name = f"{name} [EXIT GRANTED]"
                                sub_text = f"PASS #{perm_info.get('pass_id', '')} PERMITTED - Room {perm_info.get('room') or 'N/A'}"
                            else:
                                display_name = f"{name} [Day Scholar]"
                                sub_text = "EXIT ALLOWED"
                        else:
                            if perm_info.get("status") == "returned":
                                display_name = f"{name} [ENTERED]"
                                sub_text = "Outing Closed - Pass is now invalid"
                            else:
                                display_name = f"{name} [{person_id}]"
                                sub_text = f"Sim: {similarity:.2f}"

                    if bbox:
                        try:
                            x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)

                            # Name label above box
                            display = display_name
                            (tw, th), _ = cv2.getTextSize(display, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
                            ty = max(y - 8, th + 4)
                            cv2.rectangle(annotated, (x, ty - th - 4), (x + tw + 6, ty + 2),
                                          color, cv2.FILLED)
                            cv2.putText(
                                annotated, display,
                                (x + 3, ty - 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2, cv2.LINE_AA
                            )

                            # Sub-text below box
                            (sw, sh), _ = cv2.getTextSize(sub_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
                            by = y + h + sh + 6
                            cv2.rectangle(annotated, (x, y + h + 2), (x + sw + 6, by + 4),
                                          (20, 20, 20), cv2.FILLED)
                            cv2.putText(annotated, sub_text, (x + 3, by),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255) if is_known and not is_exit_denied else (0, 100, 255), 1, cv2.LINE_AA)
                        except Exception as draw_err:
                            logger.debug("Drawing error: %s", draw_err)

                # HUD overlay — dark background strip for readability
                hud = f"SmartGateAI  FPS:{fps:.1f}  Faces:{len(rec_results)}  Known:{known_count}  Unknown:{unknown_count}  Mode:{self._gate_mode.upper()}"
                cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 28), (20, 20, 20), cv2.FILLED)
                cv2.putText(annotated, hud, (8, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

                # Top alert banners
                if has_denied_exit:
                    banner_text = f"SECURITY ALERT: HOSTEL EXIT DENIED - {denied_student_summary}"
                    cv2.rectangle(annotated, (0, 28), (annotated.shape[1], 56), (0, 0, 200), cv2.FILLED)
                    cv2.putText(annotated, banner_text, (8, 48),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
                elif unknown_count > 0:
                    alert_text = f"ALERT: UNKNOWN PERSON DETECTED ({unknown_count})"
                    cv2.rectangle(annotated, (0, 28), (annotated.shape[1], 56), (0, 0, 220), cv2.FILLED)
                    cv2.putText(annotated, alert_text, (8, 48),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)

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
                    p_info = self._perm_cache.get(r.assigned_person_id, {}) if r.is_recognised else {}
                    serialisable_results.append({
                        "person_id": r.assigned_person_id,
                        "name": r.assigned_name,
                        "bbox": bbox_list,
                        "similarity": float(r.similarity_score),
                        "is_known": bool(r.is_recognised),
                        "category": p_info.get("category"),
                        "permission_status": p_info.get("status"),
                        "permission_id": p_info.get("pass_id"),
                        "status_message": p_info.get("message"),
                        "room_number": p_info.get("room"),
                        "hostel_name": p_info.get("hostel"),
                    })

                # Update shared state under lock
                with self._lock:
                    self._latest_frame = jpeg_bytes
                    self._latest_results = serialisable_results
                    self._fps = fps
                    self._faces_detected = len(rec_results)
                    self._known_count = known_count
                    self._unknown_count = unknown_count

        except Exception as fatal:
            err_msg = f"Camera thread fatal error: {fatal}"
            logger.exception(err_msg)
            with self._lock:
                self._thread_error = err_msg
        finally:
            with self._lock:
                self._running = False
            self._release_cap()
            logger.info("Capture loop exited.")

    def _process_faces(self, rec_results: list):
        """Handle database transactions for recognized and unknown faces with 30s throttling.
        - On EXIT: verifies hostel permissions for Hostellers, logs Day Scholar exit, generates alerts.
        - On ENTRY: tracks active outing returns for Hostellers, logs normal entry, resolves alerts.
        """
        now_utc = datetime.now(timezone.utc)
        to_process = []

        for r in rec_results:
            key = r.assigned_person_id if r.is_recognised else "__UNKNOWN__"
            last = self._last_logged.get(key)
            if last is None or (now_utc - last) > timedelta(seconds=30):
                to_process.append(r)
                self._last_logged[key] = now_utc

        if not to_process:
            return

        try:
            db = SessionLocal()
            try:
                # Periodic auto-expiration and late return check (every 60s)
                if (now_utc - self._last_overdue_check) > timedelta(seconds=60):
                    self._last_overdue_check = now_utc
                    try:
                        from ..services.hostel_permission_service import HostelPermissionService
                        HostelPermissionService(db).auto_expire_permissions()
                        HostelPermissionService(db).check_overdue_outings()
                    except Exception as overdue_err:
                        logger.debug("Overdue check error: %s", overdue_err)

                for r in to_process:
                    if not r.is_recognised:
                        # Unknown face detected
                        event = RecognitionEvent(
                            student_id=None,
                            full_name=None,
                            event_type=self._gate_mode,
                            gate_id=self._gate_mode,
                            similarity=float(r.similarity_score),
                            is_known=False,
                            source="camera",
                            captured_at=now_utc,
                        )
                        db.add(event)
                        with self._lock:
                            self._active_alert = {
                                "type": "UNKNOWN_FACE",
                                "message": f"Unknown Person detected at {self._gate_mode.upper()} gate",
                                "time": now_utc.isoformat(),
                            }
                        continue

                    # Known face recognized
                    person_id = r.assigned_person_id
                    student = db.scalar(select(Student).where(Student.student_id == person_id))
                    student_name = student.full_name if student else r.assigned_name
                    category = student.category if student else "Day Scholar"
                    hostel_name = student.hostel_name if student else None
                    hostel_block = student.hostel_block if student else None
                    room_number = student.room_number if student else None

                    now_naive = datetime.utcnow()

                    if self._gate_mode == "exit":
                        # ==========================================
                        # EXIT CAMERA: Hostel Permission Verification
                        # ==========================================
                        if category == "Hosteller":
                            # Check all passes for this student
                            approved_perms = db.scalars(
                                select(HostelPermission).where(
                                    and_(
                                        HostelPermission.student_id == person_id,
                                        HostelPermission.status == "Approved"
                                    )
                                ).order_by(HostelPermission.valid_until.asc())
                            ).all()

                            valid_perm = None
                            timing_issue = None

                            for p in approved_perms:
                                valid_from_naive = p.valid_from.replace(tzinfo=None) if p.valid_from.tzinfo else p.valid_from
                                valid_until_naive = p.valid_until.replace(tzinfo=None) if p.valid_until.tzinfo else p.valid_until

                                if valid_from_naive <= now_naive <= valid_until_naive:
                                    valid_perm = p
                                    break
                                elif now_naive < valid_from_naive:
                                    timing_issue = f"OUTSIDE PASS TIMING (Departure is at {p.departure_time})"
                                elif now_naive > valid_until_naive:
                                    p.status = "Expired"
                                    timing_issue = f"PASS #{p.id} EXPIRED (Return time was {p.expected_return_time})"

                            if valid_perm:
                                # ATOMIC EXIT AUTHORIZATION
                                valid_perm.status = "Used"
                                valid_perm.used_at = now_naive

                                outing = ActiveOuting(
                                    permission_id=valid_perm.id,
                                    student_id=person_id,
                                    student_name=student_name,
                                    hostel_name=hostel_name,
                                    hostel_block=hostel_block,
                                    room_number=room_number,
                                    actual_exit_time=now_naive,
                                    expected_return_time=valid_perm.valid_until,
                                    status="Out",
                                )
                                db.add(outing)

                                event = RecognitionEvent(
                                    student_id=person_id,
                                    full_name=student_name,
                                    event_type="exit",
                                    gate_id="exit",
                                    similarity=float(r.similarity_score),
                                    is_known=True,
                                    source="camera",
                                    captured_at=now_utc,
                                )
                                db.add(event)

                                self._perm_cache[person_id] = {
                                    "status": "granted",
                                    "category": "Hosteller",
                                    "message": f"EXIT GRANTED - PASS #{valid_perm.id} PERMITTED",
                                    "pass_id": valid_perm.id,
                                    "room": room_number,
                                    "hostel": hostel_name,
                                }
                                with self._lock:
                                    self._active_alert = {
                                        "type": "HOSTEL_EXIT_GRANTED",
                                        "student_name": student_name,
                                        "student_id": person_id,
                                        "pass_id": valid_perm.id,
                                        "message": f"EXIT GRANTED - PASS #{valid_perm.id} PERMITTED",
                                        "time": now_utc.isoformat(),
                                    }
                                logger.info("Exit GRANTED for Hosteller %s (%s) with pass #%d.", student_name, person_id, valid_perm.id)
                            else:
                                # DENIAL DIAGNOSIS
                                if timing_issue:
                                    denial_reason = timing_issue
                                else:
                                    any_perm = db.scalar(
                                        select(HostelPermission).where(HostelPermission.student_id == person_id).order_by(HostelPermission.created_at.desc())
                                    )
                                    if not any_perm:
                                        denial_reason = "NO PASS GENERATED - HOSTEL EXIT FORBIDDEN"
                                    elif any_perm.status == "Pending":
                                        denial_reason = f"PASS #{any_perm.id} PENDING APPROVAL - EXIT NOT PERMITTED"
                                    elif any_perm.status == "Rejected":
                                        denial_reason = f"PASS #{any_perm.id} WAS REJECTED BY WARDEN"
                                    elif any_perm.status == "Expired":
                                        denial_reason = f"PASS #{any_perm.id} EXPIRED - TIMING WINDOW CLOSED"
                                    elif any_perm.status == "Used":
                                        denial_reason = f"PASS #{any_perm.id} ALREADY USED - SINGLE USE EXHAUSTED"
                                    else:
                                        denial_reason = "NO VALID EXIT PASS"

                                # Create SecurityAlert
                                alert = SecurityAlert(
                                    alert_type="HOSTEL_EXIT_DENIED",
                                    severity="HIGH",
                                    student_id=person_id,
                                    student_name=student_name,
                                    gate_id="exit",
                                    description=(
                                        f"HOSTEL EXIT DENIED: Student {student_name} ({person_id}) "
                                        f"attempted exit without an approved valid pass ({denial_reason}). "
                                        f"Hostel: {hostel_name or 'N/A'}, Room: {room_number or 'N/A'}."
                                    ),
                                    is_resolved=False,
                                )
                                db.add(alert)

                                # Log recognition event
                                event = RecognitionEvent(
                                    student_id=person_id,
                                    full_name=student_name,
                                    event_type="exit",
                                    gate_id="exit",
                                    similarity=float(r.similarity_score),
                                    is_known=True,
                                    source="camera",
                                    captured_at=now_utc,
                                )
                                db.add(event)

                                self._perm_cache[person_id] = {
                                    "status": "denied",
                                    "category": "Hosteller",
                                    "message": denial_reason,
                                    "pass_id": any_perm.id if any_perm else None,
                                    "room": room_number,
                                    "hostel": hostel_name,
                                }
                                with self._lock:
                                    self._active_alert = {
                                        "type": "HOSTEL_EXIT_DENIED",
                                        "student_name": student_name,
                                        "student_id": person_id,
                                        "message": f"EXIT DENIED: {denial_reason}",
                                        "room": room_number,
                                        "hostel": hostel_name,
                                        "time": now_utc.isoformat(),
                                    }
                                logger.warning("Exit DENIED for Hosteller %s (%s): %s", student_name, person_id, denial_reason)
                        else:
                            # Day Scholar: Normal Exit Allowed
                            event = RecognitionEvent(
                                student_id=person_id,
                                full_name=student_name,
                                event_type="exit",
                                gate_id="exit",
                                similarity=float(r.similarity_score),
                                is_known=True,
                                source="camera",
                                captured_at=now_utc,
                            )
                            db.add(event)

                            self._perm_cache[person_id] = {
                                "status": "granted",
                                "category": "Day Scholar",
                                "message": "Day Scholar - Exit Allowed",
                                "pass_id": None,
                                "room": None,
                                "hostel": None,
                            }
                            logger.info("Exit recorded for Day Scholar %s (%s).", student_name, person_id)

                    else:
                        # ==========================================
                        # ENTRY CAMERA: Normal Entry & Auto-Return Tracking
                        # ==========================================
                        is_returned = False
                        if category == "Hosteller":
                            # Check if student is returning from an active outing
                            active_outing = db.scalar(
                                select(ActiveOuting).where(
                                    and_(
                                        ActiveOuting.student_id == person_id,
                                        ActiveOuting.status.in_(["Out", "Late"]),
                                    )
                                ).order_by(ActiveOuting.actual_exit_time.desc())
                            )
                            if active_outing:
                                active_outing.status = "Returned"
                                active_outing.actual_return_time = now_naive
                                is_returned = True

                                # Auto-resolve any late return alert for this student
                                late_alerts = db.scalars(
                                    select(SecurityAlert).where(
                                        and_(
                                            SecurityAlert.student_id == person_id,
                                            SecurityAlert.alert_type == "LATE_RETURN",
                                            SecurityAlert.is_resolved == False,
                                        )
                                    )
                                ).all()
                                for la in late_alerts:
                                    la.is_resolved = True
                                    la.resolved_by = "Auto-Gate Entry"
                                    la.resolved_at = now_naive

                                self._perm_cache[person_id] = {
                                    "status": "returned",
                                    "category": "Hosteller",
                                    "message": "Hostel student entered - Pass is now invalid",
                                    "pass_id": active_outing.permission_id,
                                    "room": room_number,
                                    "hostel": hostel_name,
                                }
                                with self._lock:
                                    self._active_alert = {
                                        "type": "HOSTEL_OUTING_RETURNED",
                                        "student_name": student_name,
                                        "student_id": person_id,
                                        "pass_id": active_outing.permission_id,
                                        "message": f"Hostel student {student_name} entered - Outing closed & pass is now invalid",
                                        "time": now_utc.isoformat(),
                                    }
                                logger.info("Hosteller %s (%s) entered. Outing closed and pass #%d is now invalid.", student_name, person_id, active_outing.permission_id)
                            else:
                                self._perm_cache[person_id] = {
                                    "status": "normal",
                                    "category": "Hosteller",
                                    "message": "Hosteller Entry",
                                    "pass_id": None,
                                    "room": room_number,
                                    "hostel": hostel_name,
                                }
                        else:
                            self._perm_cache[person_id] = {
                                "status": "normal",
                                "category": "Day Scholar",
                                "message": "Day Scholar Entry",
                                "pass_id": None,
                                "room": None,
                                "hostel": None,
                            }

                        # Normal entry attendance event
                        event = RecognitionEvent(
                            student_id=person_id,
                            full_name=student_name,
                            event_type="entry",
                            gate_id="entry",
                            similarity=float(r.similarity_score),
                            is_known=True,
                            source="camera",
                            captured_at=now_utc,
                        )
                        db.add(event)
                        logger.info("Entry recorded for student %s (%s).", student_name, person_id)

                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.error("Failed to process faces in camera service: %s", exc)


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

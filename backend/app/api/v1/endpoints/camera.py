"""
Camera management API endpoints for SmartGateAI.
Provides start/stop controls (admin-only) and a public MJPEG stream.
Phase 2: Added gate_mode param to /start, and /mode GET/POST endpoints.
"""

import asyncio
import logging
from typing import Optional

import numpy as np
import cv2
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.deps import require_admin, get_face_engine, get_vector_matcher
from app.schemas.student import MessageResponse
from app.services.camera_service import get_camera_service

logger = logging.getLogger("SmartGateAI.CameraEndpoints")

router = APIRouter()


@router.post("/start", response_model=MessageResponse)
def start_camera(
    gate_mode: str = Query("entry", description="'entry' or 'exit'"),
    _: str = Depends(require_admin),
    face_engine=Depends(get_face_engine),
    matcher=Depends(get_vector_matcher),
):
    """Start the background camera capture thread (admin only)."""
    if gate_mode not in {"entry", "exit"}:
        raise HTTPException(400, "gate_mode must be 'entry' or 'exit'")
    svc = get_camera_service()
    if svc.is_running():
        if svc.get_gate_mode() != gate_mode:
            svc.set_gate_mode(gate_mode)
            return MessageResponse(message=f"Switched camera mode to '{gate_mode}'.")
        return MessageResponse(message="Camera is already running.")
    success = svc.start(face_engine, matcher, gate_mode=gate_mode)
    if success:
        return MessageResponse(message=f"Camera started successfully (gate_mode='{gate_mode}').")
    return MessageResponse(message="Failed to start camera. Check webcam connection.")


@router.post("/stop", response_model=MessageResponse)
def stop_camera(_: str = Depends(require_admin)):
    """Stop the background camera capture thread (admin only)."""
    svc = get_camera_service()
    if not svc.is_running():
        return MessageResponse(message="Camera is not running.")
    svc.stop()
    return MessageResponse(message="Camera stopped successfully.")


@router.get("/mode")
def get_camera_mode():
    """Return current gate mode and running state (no auth required)."""
    svc = get_camera_service()
    return JSONResponse({"gate_mode": svc.get_gate_mode(), "running": svc.is_running()})


@router.post("/mode", response_model=MessageResponse)
def set_camera_mode(
    gate_mode: str = Query(..., description="'entry' or 'exit'"),
    _: str = Depends(require_admin),
):
    """Change gate mode while camera is running (admin only)."""
    if gate_mode not in {"entry", "exit"}:
        raise HTTPException(400, "gate_mode must be 'entry' or 'exit'")
    get_camera_service().set_gate_mode(gate_mode)
    return MessageResponse(message=f"Gate mode set to '{gate_mode}'.")


@router.post("/reload-embeddings", response_model=MessageResponse)
def reload_embeddings(
    _: str = Depends(require_admin),
    matcher=Depends(get_vector_matcher),
):
    """Reload student embeddings into VectorMatcher from the database without restarting the server."""
    from app.db.session import SessionLocal
    from app.models.student import Student
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import joinedload
    import numpy as np

    db = SessionLocal()
    try:
        students = db.execute(
            sa_select(Student)
            .options(joinedload(Student.embeddings))
            .where(Student.is_active == True)
        ).unique().scalars().all()

        # Clear and rebuild registry
        matcher.registry.clear()
        count = 0
        for s in students:
            if not s.embeddings:
                continue
            matcher.enroll_person(s.student_id, s.full_name, s.department)
            for emb_record in s.embeddings:
                vec = emb_record.to_numpy()
                matcher.add_photo_embedding(s.student_id, vec)
                count += 1
        return MessageResponse(message=f"Reloaded {len(students)} students ({count} embeddings) into recognition cache.")
    except Exception as exc:
        logger.error("reload_embeddings error: %s", exc)
        return MessageResponse(message=f"Reload failed: {exc}")
    finally:
        db.close()


@router.get("/status")
def camera_status():
    """Return current camera status (no auth required)."""
    return JSONResponse(content=get_camera_service().get_status())


@router.get("/stream")
async def camera_stream():
    """Serve a live MJPEG stream from the camera (no auth required)."""

    async def generate():
        try:
            while True:
                jpeg = get_camera_service().get_jpeg_frame()
                if jpeg is None:
                    # Generate a placeholder offline frame
                    placeholder = np.zeros((240, 320, 3), dtype=np.uint8)
                    cv2.putText(
                        placeholder,
                        "Camera Offline",
                        (60, 125),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (200, 200, 200),
                        2,
                        cv2.LINE_AA,
                    )
                    ok, buf = cv2.imencode(".jpg", placeholder)
                    jpeg = buf.tobytes() if ok else b""

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpeg
                    + b"\r\n"
                )
                await asyncio.sleep(0.033)
        except GeneratorExit:
            logger.info("MJPEG stream: client disconnected.")

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

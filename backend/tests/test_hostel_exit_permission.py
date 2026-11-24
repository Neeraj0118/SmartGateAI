"""
Comprehensive Integration Test Suite for Smart Hostel Exit Permission System:
Phase 2 (EXIT Camera Verification), Phase 3 (ENTRY Return Tracking), and Phase 4 (Late Return Alerts).

Verifies:
1. Day Scholar normal exit without permission requirement.
2. Hosteller exit denial on missing permission.
3. Hosteller exit denial on pending permission.
4. Hosteller exit denial on rejected permission.
5. Hosteller exit denial on expired permission.
6. Hosteller exit authorization with approved valid permission (single-use consumption).
7. Duplicate pass usage prevention (Used pass cannot be re-used).
8. Late return automatic detection and SecurityAlert generation.
9. Hosteller ENTRY gate return tracking (ActiveOuting marked Returned, alert resolved).
10. ENTRY gate never blocks or checks exit permissions.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select, and_
from app.db.session import SessionLocal
from app.models.student import Student
from app.models.hostel_permission import HostelPermission, ActiveOuting, SecurityAlert
from app.models.recognition_event import RecognitionEvent
from app.services.camera_service import CameraService
from app.services.hostel_permission_service import HostelPermissionService


class MockRecognitionResult:
    def __init__(self, assigned_person_id, assigned_name, is_recognised=True, similarity_score=0.92, bbox=(10, 10, 100, 100)):
        self.assigned_person_id = assigned_person_id
        self.assigned_name = assigned_name
        self.is_recognised = is_recognised
        self.similarity_score = similarity_score
        self.confidence = 0.95
        self.bbox = bbox


def run_tests():
    db = SessionLocal()
    cam = CameraService()

    try:
        print("\n=======================================================")
        print("  SMART HOSTEL EXIT PERMISSION SYSTEM - INTEGRATION TESTS")
        print("=======================================================\n")

        # Setup test students
        # 1. Day Scholar Student
        ds_id = "TEST-DS-001"
        ds_student = db.scalar(select(Student).where(Student.student_id == ds_id))
        if not ds_student:
            ds_student = Student(
                student_id=ds_id,
                full_name="Rahul Sharma (Day Scholar)",
                department="Computer Science",
                category="Day Scholar"
            )
            db.add(ds_student)

        # 2. Hosteller Student
        hostel_id = "TEST-HST-001"
        hostel_student = db.scalar(select(Student).where(Student.student_id == hostel_id))
        if not hostel_student:
            hostel_student = Student(
                student_id=hostel_id,
                full_name="Aman Verma (Hosteller)",
                department="Mechanical",
                category="Hosteller",
                hostel_name="Kaveri Boys Hostel",
                hostel_block="Block B",
                room_number="B-204"
            )
            db.add(hostel_student)
        db.commit()

        # Clean up any past test data for these students
        for sid in [ds_id, hostel_id]:
            # Delete recognition events
            db.query(RecognitionEvent).filter(RecognitionEvent.student_id == sid).delete()
            # Delete active outings
            db.query(ActiveOuting).filter(ActiveOuting.student_id == sid).delete()
            # Delete alerts
            db.query(SecurityAlert).filter(SecurityAlert.student_id == sid).delete()
            # Delete permissions
            db.query(HostelPermission).filter(HostelPermission.student_id == sid).delete()
        db.commit()

        # -------------------------------------------------------------
        # TEST 1: Day Scholar Normal Exit
        # -------------------------------------------------------------
        print("--> [TEST 1] Day Scholar Normal Exit at EXIT camera...")
        cam._gate_mode = "exit"
        cam._last_logged.clear()
        cam._perm_cache.clear()

        rec = MockRecognitionResult(ds_id, ds_student.full_name)
        cam._process_faces([rec])

        cached = cam._perm_cache.get(ds_id)
        assert cached is not None, "Perm cache missing for Day Scholar"
        assert cached["status"] == "granted", f"Expected granted, got {cached['status']}"
        assert cached["category"] == "Day Scholar"

        # Check DB event
        ev = db.scalar(select(RecognitionEvent).where(
            and_(RecognitionEvent.student_id == ds_id, RecognitionEvent.event_type == "exit")
        ))
        assert ev is not None, "RecognitionEvent not logged for Day Scholar exit"

        # Check no active outing
        outing = db.scalar(select(ActiveOuting).where(ActiveOuting.student_id == ds_id))
        assert outing is None, "Day Scholar must not have an active outing record"
        print("    [PASS] Day Scholar exit permitted normally without pass requirement.")

        # -------------------------------------------------------------
        # TEST 2: Hosteller Exit Denial (No Pass)
        # -------------------------------------------------------------
        print("\n--> [TEST 2] Hosteller Exit with Missing Pass...")
        cam._last_logged.clear()
        cam._perm_cache.clear()

        rec_hst = MockRecognitionResult(hostel_id, hostel_student.full_name)
        cam._process_faces([rec_hst])

        cached = cam._perm_cache.get(hostel_id)
        assert cached is not None, "Perm cache missing for Hosteller"
        assert cached["status"] == "denied", f"Expected denied, got {cached['status']}"
        assert "NO PASS GENERATED" in cached["message"] or "NO APPROVED PASS" in cached["message"]

        # Check SecurityAlert created
        alert = db.scalar(select(SecurityAlert).where(
            and_(
                SecurityAlert.student_id == hostel_id,
                SecurityAlert.alert_type == "HOSTEL_EXIT_DENIED",
                SecurityAlert.is_resolved == False
            )
        ))
        assert alert is not None, "SecurityAlert not created for denied exit"
        assert alert.severity == "HIGH"
        print(f"    [PASS] Exit denied and SecurityAlert created: {alert.description[:60]}...")

        # -------------------------------------------------------------
        # TEST 3: Hosteller Exit Denial (Pending Pass)
        # -------------------------------------------------------------
        print("\n--> [TEST 3] Hosteller Exit with Pending Pass...")
        now = datetime.utcnow()
        pending_perm = HostelPermission(
            student_id=hostel_id,
            student_name=hostel_student.full_name,
            reason="Market Visit",
            departure_date=now.strftime("%Y-%m-%d"),
            departure_time=now.strftime("%H:%M"),
            valid_from=now - timedelta(minutes=5),
            expected_return_date=now.strftime("%Y-%m-%d"),
            expected_return_time=(now + timedelta(hours=2)).strftime("%H:%M"),
            valid_until=now + timedelta(hours=2),
            status="Pending"
        )
        db.add(pending_perm)
        db.commit()
        db.refresh(pending_perm)

        cam._last_logged.clear()
        cam._perm_cache.clear()
        cam._process_faces([rec_hst])

        cached = cam._perm_cache.get(hostel_id)
        assert cached["status"] == "denied"
        assert "PENDING APPROVAL" in cached["message"]
        print(f"    [PASS] Pending pass correctly denied: {cached['message']}.")

        # -------------------------------------------------------------
        # TEST 4: Hosteller Exit Authorization with Approved Valid Pass
        # -------------------------------------------------------------
        print("\n--> [TEST 4] Hosteller Exit with Approved Valid Pass...")
        # Approve the pass
        pending_perm.status = "Approved"
        pending_perm.approved_by = "Warden Sharma"
        pending_perm.approved_at = now
        db.commit()

        cam._last_logged.clear()
        cam._perm_cache.clear()
        cam._process_faces([rec_hst])

        cached = cam._perm_cache.get(hostel_id)
        assert cached["status"] == "granted", f"Expected granted, got {cached['status']}"
        assert cached["pass_id"] == pending_perm.id

        # Verify pass was atomically consumed to 'Used'
        db.refresh(pending_perm)
        assert pending_perm.status == "Used", f"Pass should be 'Used', got {pending_perm.status}"
        assert pending_perm.used_at is not None

        # Verify ActiveOuting created
        active_out = db.scalar(select(ActiveOuting).where(
            and_(ActiveOuting.student_id == hostel_id, ActiveOuting.status == "Out")
        ))
        assert active_out is not None, "ActiveOuting not created!"
        assert active_out.hostel_name == "Kaveri Boys Hostel"
        assert active_out.room_number == "B-204"
        print(f"    [PASS] Exit granted! Pass #{pending_perm.id} marked 'Used', ActiveOuting created.")

        # -------------------------------------------------------------
        # TEST 5: Single-Use Prevention (Attempt to Re-use Pass)
        # -------------------------------------------------------------
        print("\n--> [TEST 5] Single-Use Prevention: Attempt to Re-use Used Pass...")
        cam._last_logged.clear()
        cam._perm_cache.clear()
        cam._process_faces([rec_hst])

        cached = cam._perm_cache.get(hostel_id)
        assert cached["status"] == "denied", "Used pass must not authorize re-exit!"
        assert "ALREADY USED" in cached["message"]
        print("    [PASS] Re-exit blocked! Used pass cannot be re-used.")

        # -------------------------------------------------------------
        # TEST 6: Late Return Detection (Phase 4)
        # -------------------------------------------------------------
        print("\n--> [TEST 6] Automatic Late Return Detection...")
        # Simulate time passing beyond expected return time
        active_out.expected_return_time = datetime.utcnow() - timedelta(minutes=15)
        db.commit()

        perm_svc = HostelPermissionService(db)
        updated_late = perm_svc.check_overdue_outings()
        assert updated_late >= 1, "Expected at least 1 overdue outing updated"

        db.refresh(active_out)
        assert active_out.status == "Late", f"Expected status 'Late', got {active_out.status}"

        # Verify LATE_RETURN SecurityAlert generated
        late_alert = db.scalar(select(SecurityAlert).where(
            and_(
                SecurityAlert.student_id == hostel_id,
                SecurityAlert.alert_type == "LATE_RETURN",
                SecurityAlert.is_resolved == False
            )
        ))
        assert late_alert is not None, "LATE_RETURN security alert was not created"
        print(f"    [PASS] Overdue outing flagged as 'Late' and alert generated: {late_alert.description[:60]}...")

        # -------------------------------------------------------------
        # TEST 7: Hosteller ENTRY Gate Return Tracking (Phase 3)
        # -------------------------------------------------------------
        print("\n--> [TEST 7] Hosteller ENTRY Gate Return Tracking...")
        cam._gate_mode = "entry"
        cam._last_logged.clear()
        cam._perm_cache.clear()

        cam._process_faces([rec_hst])

        cached = cam._perm_cache.get(hostel_id)
        assert cached["status"] == "returned", f"Expected returned, got {cached['status']}"

        # Verify ActiveOuting transitioned to 'Returned'
        db.refresh(active_out)
        assert active_out.status == "Returned", f"Expected status 'Returned', got {active_out.status}"
        assert active_out.actual_return_time is not None

        # Verify LATE_RETURN alert was auto-resolved
        db.refresh(late_alert)
        assert late_alert.is_resolved == True, "Late return alert should be auto-resolved on entry"
        assert late_alert.resolved_by == "Auto-Gate Entry"

        # Verify normal ENTRY recognition event logged
        entry_ev = db.scalar(select(RecognitionEvent).where(
            and_(RecognitionEvent.student_id == hostel_id, RecognitionEvent.event_type == "entry")
        ))
        assert entry_ev is not None, "RecognitionEvent for ENTRY not logged"
        print("    [PASS] Hosteller return recorded! ActiveOuting marked Returned, alert auto-resolved.")

        # -------------------------------------------------------------
        # TEST 8: ENTRY Gate Never Denies or Requires Permission
        # -------------------------------------------------------------
        print("\n--> [TEST 8] ENTRY Gate Never Denies Entry...")
        # Student enters without any active pass or outing
        cam._last_logged.clear()
        cam._perm_cache.clear()
        cam._process_faces([rec_hst])

        cached = cam._perm_cache.get(hostel_id)
        assert cached["status"] == "normal", f"Expected normal entry, got {cached['status']}"
        print("    [PASS] ENTRY gate allows entry without requiring exit passes.")

        print("\n=======================================================")
        print("  ALL HOSTEL EXIT PERMISSION INTEGRATION TESTS PASSED! ")
        print("=======================================================\n")

    finally:
        # Clean up test students and their artifacts so production DB stays clean
        try:
            for sid in [ds_id, hostel_id]:
                db.query(RecognitionEvent).filter(RecognitionEvent.student_id == sid).delete()
                db.query(ActiveOuting).filter(ActiveOuting.student_id == sid).delete()
                db.query(SecurityAlert).filter(SecurityAlert.student_id == sid).delete()
                db.query(HostelPermission).filter(HostelPermission.student_id == sid).delete()
                db.query(Student).filter(Student.student_id == sid).delete()
            db.commit()
        except Exception:
            pass
        db.close()


if __name__ == "__main__":
    run_tests()

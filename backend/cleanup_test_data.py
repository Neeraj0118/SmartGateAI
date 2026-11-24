import os
import sys
import shutil
from datetime import datetime

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

sys.path = [p for p in sys.path if "GateMonitoringSystem" not in p]

from app.config import settings
from app.db.session import SessionLocal
from app.models.student import Student, FaceEmbedding
from app.models.hostel_permission import HostelPermission, ActiveOuting, SecurityAlert
from app.models.recognition_event import RecognitionEvent

# 1. Create a safe backup before cleanup
db_file = os.path.join(settings.STORAGE_DIR, "smartgate.db")
backup_dir = os.path.join(settings.STORAGE_DIR, "backups")
os.makedirs(backup_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = os.path.join(backup_dir, f"smartgate_backup_before_cleanup_{timestamp}.db")
shutil.copy2(db_file, backup_file)
print(f"[OK] Safety backup created at: {backup_file}")

db = SessionLocal()

NEERAJ_ID = "230111472"

# 2. Clean test students (non-Neeraj)
test_students = db.query(Student).filter(Student.student_id != NEERAJ_ID).all()
for s in test_students:
    print(f"Removing test student: {s.student_id} ({s.full_name})")
    db.delete(s)

# 3. Clean face embeddings not belonging to Neeraj
neeraj_student = db.query(Student).filter(Student.student_id == NEERAJ_ID).first()
if neeraj_student:
    orphan_embeddings = db.query(FaceEmbedding).filter(FaceEmbedding.student_id != neeraj_student.id).all()
    for emb in orphan_embeddings:
        print(f"Removing non-Neeraj embedding ID: {emb.id}")
        db.delete(emb)

# 4. Clean test permissions (all permissions were created by automated test scripts)
test_perms = db.query(HostelPermission).all()
for p in test_perms:
    print(f"Removing test permission ID {p.id} for {p.student_id} ({p.student_name})")
    db.delete(p)

# 5. Clean test active outings
test_outings = db.query(ActiveOuting).all()
for o in test_outings:
    print(f"Removing test active outing ID {o.id} for {o.student_id}")
    db.delete(o)

# 6. Clean test security alerts
test_alerts = db.query(SecurityAlert).all()
for a in test_alerts:
    print(f"Removing test security alert ID {a.id}: {a.alert_type}")
    db.delete(a)

# 7. Clean test recognition events
test_events = db.query(RecognitionEvent).filter(
    RecognitionEvent.student_id.in_(["TEST-DS-001", "TEST-HST-001"])
).all()
for ev in test_events:
    db.delete(ev)
print(f"Removed {len(test_events)} test recognition events.")

db.commit()
print("\n[SUCCESS] Cleanup committed successfully!")

# Summary of remaining data
remaining_students = db.query(Student).all()
print("\n--- REMAINING STUDENTS ---")
for s in remaining_students:
    print(f"Student: {s.student_id} - {s.full_name} | Dept: {s.department} | Category: {s.category} | Embeddings: {len(s.embeddings)}")

remaining_events = db.query(RecognitionEvent).count()
print(f"\nRemaining Recognition Events (Attendance logs): {remaining_events}")

db.close()

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

sys.path = [p for p in sys.path if "GateMonitoringSystem" not in p]

from app.db.session import SessionLocal
from app.models.student import Student, FaceEmbedding
from app.models.hostel_permission import HostelPermission, ActiveOuting, SecurityAlert
from app.models.recognition_event import RecognitionEvent
from app.config import settings

print(f"DATABASE URL: {settings.DATABASE_URL}")
print(f"STORAGE DIR: {settings.STORAGE_DIR}")
print(f"STUDENT PHOTOS DIR: {settings.STUDENT_PHOTOS_DIR}")

db = SessionLocal()

print("\n--- STUDENTS ---")
students = db.query(Student).all()
for s in students:
    print(f"ID: {s.student_id}, Name: {s.full_name}, Dept: {s.department}, Category: {s.category}, Embeddings: {len(s.embeddings)}")

print("\n--- FACE EMBEDDINGS ---")
embeddings = db.query(FaceEmbedding).all()
for e in embeddings:
    print(f"ID: {e.id}, Student ID: {e.student_id}, Photo Path: {e.photo_path}")

print("\n--- PERMISSIONS ---")
permissions = db.query(HostelPermission).all()
for p in permissions:
    print(f"ID: {p.id}, Student: {p.student_id} ({p.student_name}), Status: {p.status}")

print("\n--- ACTIVE OUTINGS ---")
outings = db.query(ActiveOuting).all()
for o in outings:
    print(f"ID: {o.id}, Student: {o.student_id} ({o.student_name}), Status: {o.status}")

print("\n--- SECURITY ALERTS ---")
alerts = db.query(SecurityAlert).all()
for a in alerts:
    print(f"ID: {a.id}, Student: {a.student_id}, Type: {a.alert_type}, Desc: {a.description[:50]}")

print("\n--- RECOGNITION EVENTS ---")
total_events = db.query(RecognitionEvent).count()
print(f"Total Recognition Events: {total_events}")
for ev in db.query(RecognitionEvent).all():
    print(f"Event ID: {ev.id}, Student: {ev.student_id}, Name: {ev.full_name}, Gate: {ev.gate_id}, Type: {ev.event_type}, Time: {ev.captured_at}")

db.close()

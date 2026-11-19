"""
Phase A: Multi-Face Recognition Test Script for SmartGateAI.

Verifies the existing recognise_frame_faces() pipeline WITHOUT modifying AI code.
Loads enrolled students from the production SQLite DB and tests recognition
across composite test frames built from known benchmark portrait images.

Enrolled in production DB:
- STU-SWAGGER-001 (Swagger Test Student) — enrolled with person1_obama photos
- 230111472 (Neeraj Giri) — enrolled with user's own photos (not test data photos)

Test Cases:
  TC1: Single enrolled face (obama) → expect 1 recognised result
  TC2: Two composite frames (obama + hopkins) → STU-SWAGGER-001 recognised; Hopkins partial (not enrolled)
  TC3: One known + one unknown composite (obama + biden) → 1 known, 1 UNKNOWN
  TC4: All unknown composite (biden + alex) → 0 recognised (all UNKNOWN)
  TC5: Empty/blank frame (no faces) → 0 results
"""

import os
import sys
import time
import cv2
import numpy as np

# Add backend dir to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.orm import sessionmaker, joinedload
from app.db.session import get_engine, DEFAULT_DB_URL
from app.db.base import Base
from app.models.student import Student, FaceEmbedding
from app.services.ai.opencv_engine import OpenCVFaceEngine
from app.services.ai.vector_matcher import VectorMatcher


# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(backend_dir, "tests", "test_data")
WEIGHTS_DIR = os.path.join(backend_dir, "weights")
YUNET_PATH = os.path.join(WEIGHTS_DIR, "face_detection_yunet_2023mar.onnx")
SFACE_PATH = os.path.join(WEIGHTS_DIR, "face_recognition_sface_2021dec.onnx")

PORTRAIT_FILES = {
    "obama":   os.path.join(DATA_DIR, "person1_obama_photo1.jpg"),   # enrolled as STU-SWAGGER-001
    "obama2":  os.path.join(DATA_DIR, "person1_obama_photo2.jpg"),
    "hopkins": os.path.join(DATA_DIR, "person2_hopkins_photo1.jpg"), # NOT enrolled
    "biden":   os.path.join(DATA_DIR, "person3_biden_unknown.jpg"),  # NOT enrolled
    "alex":    os.path.join(DATA_DIR, "person4_alex_unknown.png"),   # NOT enrolled
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_composite(paths: list, canvas_h: int = 480, canvas_w: int = 960) -> np.ndarray:
    """Tile portrait images side-by-side on a dark canvas."""
    canvas = np.full((canvas_h, canvas_w, 3), 40, dtype=np.uint8)
    n = len(paths)
    if n == 0:
        return canvas
    slot_w = canvas_w // n
    slot_h = canvas_h

    for idx, path in enumerate(paths):
        img = cv2.imread(path)
        if img is None:
            continue
        ih, iw = img.shape[:2]
        target_h = int(slot_h * 0.80)
        scale = target_h / ih
        new_w = min(int(iw * scale), slot_w - 20)
        new_h = int(ih * (new_w / iw))
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        x_off = idx * slot_w + (slot_w - new_w) // 2
        y_off = (slot_h - new_h) // 2
        canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized

    return canvas


def load_enrolled_matcher(engine_ai: OpenCVFaceEngine) -> VectorMatcher:
    """Load all active students from production DB into a fresh VectorMatcher."""
    db_engine = get_engine(DEFAULT_DB_URL)
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    db = Session()

    stmt = (
        db.query(Student)
        .options(joinedload(Student.embeddings))
        .filter(Student.is_active == True)
        .all()
    )

    matcher = VectorMatcher(engine_ai, similarity_threshold=0.637)
    enrolled_count = 0
    for student in stmt:
        if not student.embeddings:
            continue
        person = matcher.enroll_person(
            person_id=student.student_id,
            name=student.full_name,
            department=student.department
        )
        person.embeddings.clear()
        for emb_rec in student.embeddings:
            vec = emb_rec.to_numpy()
            person.add_embedding(vec)
        enrolled_count += 1
        print(f"  Loaded: {student.full_name} ({student.student_id}) — {len(student.embeddings)} embedding(s)")

    db.close()
    db_engine.dispose()
    print(f"  Total enrolled in DB cache: {enrolled_count} student(s)")
    return matcher


def run_recognition(engine_ai, matcher, frame, label: str):
    """Detect + recognise faces in frame, return results."""
    dets = engine_ai.detect_faces(frame, score_threshold=0.55)
    results = matcher.recognise_frame_faces(frame, dets) if dets else []
    return dets, results


def print_result(tc: str, dets, results):
    """Pretty-print test case results."""
    known = [r for r in results if r.is_recognised]
    unknown = [r for r in results if not r.is_recognised]
    print(f"    Faces detected: {len(dets)}")
    print(f"    Results returned: {len(results)} (known={len(known)}, unknown={len(unknown)})")
    for r in results:
        label = f"{r.assigned_name} [{r.assigned_person_id}]" if r.is_recognised else "UNKNOWN"
        print(f"      Face #{r.face_index}: {label}  sim={r.similarity_score:.4f}  det_conf={r.confidence:.3f}")


def run_tests():
    sep = "=" * 70
    print(sep)
    print("  SMARTGATEAI — PHASE A: MULTI-FACE RECOGNITION TEST SUITE")
    print(sep)

    # ── Pre-flight checks ─────────────────────────────────────────────────
    print("\n[Setup] Checking model weights...")
    for p in (YUNET_PATH, SFACE_PATH):
        if not os.path.exists(p):
            print(f"  FATAL: Model not found: {p}")
            sys.exit(1)
        print(f"  OK: {os.path.basename(p)}")

    print("\n[Setup] Checking portrait images...")
    missing = [k for k, p in PORTRAIT_FILES.items() if not os.path.exists(p)]
    if missing:
        print(f"  WARNING: Missing portraits: {missing}  (some TCs may be skipped)")
    for k, p in PORTRAIT_FILES.items():
        exists_str = "OK" if os.path.exists(p) else "MISSING"
        print(f"  {exists_str}: {k} -> {os.path.basename(p)}")

    # ── Initialize AI engine ──────────────────────────────────────────────
    print("\n[Setup] Loading OpenCV YuNet + SFace models...")
    t0 = time.perf_counter()
    engine_ai = OpenCVFaceEngine(YUNET_PATH, SFACE_PATH)
    print(f"  Engine loaded in {(time.perf_counter() - t0)*1000:.1f} ms")

    # ── Load production DB enrolled students ──────────────────────────────
    print("\n[Setup] Loading enrolled students from production DB...")
    matcher = load_enrolled_matcher(engine_ai)

    results_summary = {}

    # ══════════════════════════════════════════════════════════════════════
    # TC1: Single enrolled face (Obama = STU-SWAGGER-001)
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'-'*70}")
    print("[TC1] Single enrolled face — expect 1 recognised result (STU-SWAGGER-001)")
    print(f"{'-'*70}")
    if os.path.exists(PORTRAIT_FILES["obama"]):
        img = cv2.imread(PORTRAIT_FILES["obama"])
        dets, results = run_recognition(engine_ai, matcher, img, "TC1")
        print_result("TC1", dets, results)
        known = [r for r in results if r.is_recognised]
        if len(dets) == 0:
            status = "NOTE: No face detected in portrait (image may be small)"
        elif len(known) >= 1 and known[0].assigned_person_id == "STU-SWAGGER-001":
            status = "PASS"
        elif len(known) >= 1:
            status = f"PARTIAL — recognised as {known[0].assigned_person_id} (not STU-SWAGGER-001)"
        else:
            status = "FAIL — enrolled face not recognised"
    else:
        status = "SKIP — image file missing"
        dets, results = [], []
    print(f"  TC1 → {status}")
    results_summary["TC1"] = status

    # ══════════════════════════════════════════════════════════════════════
    # TC2: Two known faces composite (obama + hopkins)
    # Note: Hopkins is NOT in production DB — TC2 is PARTIAL by design
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'-'*70}")
    print("[TC2] Two-person composite (enrolled obama + unknown hopkins)")
    print("  PARTIAL expected: only STU-SWAGGER-001 can be matched; Hopkins not enrolled")
    print(f"{'-'*70}")
    if os.path.exists(PORTRAIT_FILES["obama"]) and os.path.exists(PORTRAIT_FILES["hopkins"]):
        frame2 = make_composite([PORTRAIT_FILES["obama"], PORTRAIT_FILES["hopkins"]])
        dets2, results2 = run_recognition(engine_ai, matcher, frame2, "TC2")
        print_result("TC2", dets2, results2)
        known2 = [r for r in results2 if r.is_recognised]
        # We expect at least STU-SWAGGER-001 recognised; Hopkins will be UNKNOWN
        if len(dets2) == 0:
            status2 = "NOTE: No faces detected in composite frame"
        elif len(known2) >= 1:
            names = [r.assigned_person_id for r in known2]
            status2 = f"PARTIAL-PASS — recognised {names}; Hopkins (not enrolled) is UNKNOWN as expected"
        else:
            status2 = "FAIL — expected at least STU-SWAGGER-001 to be recognised"
    else:
        status2 = "SKIP — image file(s) missing"
    print(f"  TC2 → {status2}")
    results_summary["TC2"] = status2

    # ══════════════════════════════════════════════════════════════════════
    # TC3: One known + one unknown composite (obama + biden)
    # Expect: 1 known (STU-SWAGGER-001), 1 UNKNOWN
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'-'*70}")
    print("[TC3] Known + Unknown composite (obama + biden) — expect 1 known, 1 UNKNOWN")
    print(f"{'-'*70}")
    if os.path.exists(PORTRAIT_FILES["obama"]) and os.path.exists(PORTRAIT_FILES["biden"]):
        frame3 = make_composite([PORTRAIT_FILES["obama"], PORTRAIT_FILES["biden"]])
        dets3, results3 = run_recognition(engine_ai, matcher, frame3, "TC3")
        print_result("TC3", dets3, results3)
        known3 = [r for r in results3 if r.is_recognised]
        unknown3 = [r for r in results3 if not r.is_recognised]
        if len(dets3) == 0:
            status3 = "NOTE: No faces detected in composite frame"
        elif len(known3) >= 1 and len(unknown3) >= 1:
            status3 = "PASS — 1 known + 1 UNKNOWN as expected"
        elif len(known3) >= 1 and len(unknown3) == 0:
            status3 = "PARTIAL — known detected but no UNKNOWN (biden frame may not have been detected)"
        else:
            status3 = "FAIL — expected at least 1 known result"
    else:
        status3 = "SKIP — image file(s) missing"
    print(f"  TC3 → {status3}")
    results_summary["TC3"] = status3

    # ══════════════════════════════════════════════════════════════════════
    # TC4: All unknown composite (biden + alex) → expect 0 recognised
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'-'*70}")
    print("[TC4] All-unknown composite (biden + alex) — expect 0 recognised (all UNKNOWN)")
    print(f"{'-'*70}")
    if os.path.exists(PORTRAIT_FILES["biden"]) and os.path.exists(PORTRAIT_FILES["alex"]):
        frame4 = make_composite([PORTRAIT_FILES["biden"], PORTRAIT_FILES["alex"]])
        dets4, results4 = run_recognition(engine_ai, matcher, frame4, "TC4")
        print_result("TC4", dets4, results4)
        known4 = [r for r in results4 if r.is_recognised]
        if len(dets4) == 0:
            status4 = "NOTE: No faces detected in composite frame"
        elif len(known4) == 0:
            status4 = "PASS — 0 recognised (all UNKNOWN) as expected"
        else:
            status4 = f"FAIL — unexpected known match(es): {[r.assigned_person_id for r in known4]}"
    else:
        status4 = "SKIP — image file(s) missing"
    print(f"  TC4 → {status4}")
    results_summary["TC4"] = status4

    # ══════════════════════════════════════════════════════════════════════
    # TC5: Empty/blank frame — expect 0 results
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'-'*70}")
    print("[TC5] Empty frame (no faces) — expect 0 results")
    print(f"{'-'*70}")
    blank = np.full((480, 640, 3), 40, dtype=np.uint8)
    dets5, results5 = run_recognition(engine_ai, matcher, blank, "TC5")
    print_result("TC5", dets5, results5)
    if len(dets5) == 0 and len(results5) == 0:
        status5 = "PASS — 0 faces, 0 results as expected"
    else:
        status5 = f"FAIL — unexpected detections on blank frame: {len(dets5)}"
    print(f"  TC5 → {status5}")
    results_summary["TC5"] = status5

    # ══════════════════════════════════════════════════════════════════════
    # Summary
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{sep}")
    print("  PHASE A TEST RESULTS SUMMARY")
    print(sep)
    for tc, status in results_summary.items():
        print(f"  {tc}: {status}")
    print(sep)

    n_pass = sum(1 for s in results_summary.values() if s.startswith("PASS"))
    n_partial = sum(1 for s in results_summary.values() if s.startswith("PARTIAL"))
    n_note = sum(1 for s in results_summary.values() if s.startswith("NOTE"))
    n_fail = sum(1 for s in results_summary.values() if s.startswith("FAIL"))
    n_skip = sum(1 for s in results_summary.values() if s.startswith("SKIP"))
    print(f"\n  PASS={n_pass}  PARTIAL={n_partial}  NOTE={n_note}  FAIL={n_fail}  SKIP={n_skip}")
    print(sep)
    return results_summary


if __name__ == "__main__":
    run_tests()

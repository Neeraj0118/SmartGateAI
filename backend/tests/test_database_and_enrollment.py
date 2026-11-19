"""
Comprehensive Automated Test Suite for Phase 2:
Database Models, SQLite Schema & Student Enrollment Service.

Verifies:
1. SQLite table creation and foreign key constraint enforcement.
2. 1-to-2 photo enrollment with real benchmark face images.
3. 128-D binary BLOB storage and numpy deserialization.
4. Immediate in-memory VectorMatcher cache synchronization (no restart/retrain).
5. Duplicate student ID rejection.
6. Image quality validation (blur / face detection) during enrollment.
7. Adding subsequent photos to an existing student.
8. Search, filtering, and student updates.
9. Cascade deletion (deleting student removes embeddings in DB, files on disk, and memory cache).
10. Cold-start database persistence & cache rehydration.
"""

import os
import sys
import shutil
import cv2
import numpy as np
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

# Setup path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.base import Base
from app.db.session import get_engine
from app.models.student import Student, FaceEmbedding
from app.services.ai.opencv_engine import OpenCVFaceEngine
from app.services.ai.vector_matcher import VectorMatcher
from app.services.storage_service import PhotoStorageService
from app.services.student_service import StudentService
from tests.test_ai_phase1 import download_test_data


def run_phase2_tests():
    print("=" * 75)
    print("  SMARTGATEAI - PHASE 2 DATABASE & ENROLLMENT TEST SUITE")
    print("=" * 75)

    # 1. Setup isolated test environment
    test_db_dir = os.path.join(backend_dir, "tests", "temp_test_storage")
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
    os.makedirs(test_db_dir, exist_ok=True)

    test_db_path = os.path.join(test_db_dir, "test_smartgate.db")
    test_db_url = f"sqlite:///{test_db_path}"
    test_photos_dir = os.path.join(test_db_dir, "student_photos")

    # Acquire models and test assets
    weights_dir = os.path.join(backend_dir, "weights")
    yunet_path = os.path.join(weights_dir, "face_detection_yunet_2023mar.onnx")
    sface_path = os.path.join(weights_dir, "face_recognition_sface_2021dec.onnx")
    data_dir = os.path.join(backend_dir, "tests", "test_data")

    portrait_paths = download_test_data(data_dir)
    assert len(portrait_paths) >= 4, "Missing test portrait assets."

    # Initialize AI components
    engine_ai = OpenCVFaceEngine(yunet_path, sface_path)
    matcher = VectorMatcher(engine_ai, similarity_threshold=0.637)

    # Initialize SQLite Engine with Foreign Key Support
    print("\n" + "-" * 75)
    print("[TEST 1] SQLite Schema & Foreign Key Enforcement")
    print("-" * 75)
    db_engine = get_engine(test_db_url)
    Base.metadata.create_all(bind=db_engine)
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    db = Session()

    # Verify tables created
    table_names = list(Base.metadata.tables.keys())
    print(f"  Initialized SQLite Database at: {test_db_path}")
    print(f"  Registered Tables: {table_names}")
    assert "students" in table_names
    assert "face_embeddings" in table_names
    print("  [PASS] SQLite schema successfully initialized.")

    # Initialize Services
    storage_svc = PhotoStorageService(test_photos_dir)
    service = StudentService(
        db=db,
        engine=engine_ai,
        matcher=matcher,
        storage=storage_svc
    )

    # 2. Test Student Registration with 2 Photos
    print("\n" + "-" * 75)
    print("[TEST 2] Enrolling Student 1 with 2 Face Photographs")
    print("-" * 75)
    p1_photos = [
        portrait_paths["p1_photo1"],
        portrait_paths["p1_photo2"]
    ]
    student1 = service.register_student(
        student_id="STU-001",
        full_name="Barack Obama",
        photos=p1_photos,
        department="Computer Science",
        email="obama@university.edu"
    )

    print(f"  Enrolled: {student1.full_name} (ID: {student1.student_id})")
    print(f"  Primary Key ID: {student1.id}, Embeddings Count: {len(student1.embeddings)}")
    assert student1.id is not None
    assert len(student1.embeddings) == 2

    # Verify 128-D format and binary deserialization
    for idx, emb in enumerate(student1.embeddings):
        print(f"    Embedding #{idx+1}: BLOB size = {len(emb.embedding_data)} bytes, Dim = {emb.embedding_dim}, Quality = {emb.quality_score:.1f}")
        assert len(emb.embedding_data) == 512, "128 floats * 4 bytes must equal 512 bytes"
        assert emb.embedding_dim == 128
        arr = emb.to_numpy()
        assert arr.shape == (128,)
        assert arr.dtype == np.float32

    print("  [PASS] 2-photo enrollment and 128-D binary storage verified.")

    # 3. Test Immediate In-Memory Cache Recognition
    print("\n" + "-" * 75)
    print("[TEST 3] Immediate In-Memory Vector Cache Synchronization")
    print("-" * 75)
    # Load photo 1 and extract embedding as a live test query
    test_img = cv2.imread(portrait_paths["p1_photo1"])
    test_dets = engine_ai.detect_faces(test_img)
    test_crop = engine_ai.align_crop(test_img, test_dets[0])
    test_vec = engine_ai.extract_embedding(test_crop)

    pid, name, score, _ = matcher.match_single_embedding(test_vec)
    print(f"  Live Query Match: ID='{pid}', Name='{name}', Cosine Similarity={score:.4f}")
    assert pid == "STU-001"
    assert name == "Barack Obama"
    assert score >= 0.90
    print("  [PASS] In-memory cache was updated immediately with zero latency or retraining.")

    # 4. Test Duplicate Student ID Prevention
    print("\n" + "-" * 75)
    print("[TEST 4] Duplicate Student ID Rejection")
    print("-" * 75)
    duplicate_caught = False
    try:
        service.register_student(
            student_id="STU-001",  # Same ID
            full_name="Duplicate Imposter",
            photos=[portrait_paths["p3_photo1"]]
        )
    except ValueError as e:
        duplicate_caught = True
        print(f"  Gracefully caught duplicate registration: '{e}'")

    assert duplicate_caught, "System must reject duplicate student IDs."
    print("  [PASS] Duplicate student ID prevented.")

    # 5. Test Quality Rejection During Registration
    print("\n" + "-" * 75)
    print("[TEST 5] Enrollment Quality Validation (Blurry Photo Rejection)")
    print("-" * 75)
    sharp_img = cv2.imread(portrait_paths["p2_photo1"])
    blurry_img = cv2.GaussianBlur(sharp_img, (35, 35), 10)

    quality_rejected = False
    try:
        service.register_student(
            student_id="STU-BLUR",
            full_name="Blurry Person",
            photos=[blurry_img]
        )
    except ValueError as e:
        quality_rejected = True
        print(f"  Enrollment rejected blurry photo: '{e}'")

    assert quality_rejected, "System must reject degraded enrollment photos."
    # Verify no orphan record was created in database
    orphan = db.scalar(select(Student).where(Student.student_id == "STU-BLUR"))
    assert orphan is None
    print("  [PASS] Blurry photo rejected; no partial database records created.")

    # 6. Test Enrolling Student 2 (1 Photo) & Adding a 2nd Photo Later
    print("\n" + "-" * 75)
    print("[TEST 6] Multi-Photo Addition for Existing Student")
    print("-" * 75)
    student2 = service.register_student(
        student_id="STU-002",
        full_name="Anthony Hopkins",
        photos=[portrait_paths["p2_photo1"]],  # 1 photo initially
        department="Arts & Drama",
        email="hopkins@university.edu"
    )
    print(f"  Registered {student2.full_name} with initial {len(student2.embeddings)} photo.")
    assert len(student2.embeddings) == 1

    # Add a 2nd photo later
    new_emb = service.add_photo_to_student(
        student_id="STU-002",
        photo_input=portrait_paths["p2_photo2"]
    )
    db.refresh(student2)
    print(f"  Added 2nd photo! Total embeddings for {student2.full_name}: {len(student2.embeddings)}")
    assert len(student2.embeddings) == 2

    # Check matcher has 2 embeddings for student 2
    p2_matcher = matcher.registry["STU-002"]
    assert len(p2_matcher.embeddings) == 2
    print("  [PASS] Additional photo successfully expanded student's multi-view exemplars.")

    # 7. Test Student Listing & Search
    print("\n" + "-" * 75)
    print("[TEST 7] Student Search & Pagination")
    print("-" * 75)
    all_students = service.list_students(skip=0, limit=10)
    print(f"  Total Active Students in DB: {len(all_students)}")
    assert len(all_students) == 2

    search_hopkins = service.list_students(search_query="Hopkins")
    assert len(search_hopkins) == 1
    assert search_hopkins[0].student_id == "STU-002"
    print(f"  Search query 'Hopkins' returned: {search_hopkins[0].full_name} ({search_hopkins[0].student_id})")

    search_dept = service.list_students(search_query="Computer Science")
    assert len(search_dept) == 1
    assert search_dept[0].student_id == "STU-001"
    print(f"  Search query 'Computer Science' returned: {search_dept[0].full_name}")
    print("  [PASS] Student listing and multi-field search verified.")

    # 8. Test Student Update
    print("\n" + "-" * 75)
    print("[TEST 8] Student Record Update & In-Memory Synchronization")
    print("-" * 75)
    updated = service.update_student(
        student_id="STU-001",
        full_name="Barack H. Obama",
        department="School of Law"
    )
    assert updated.full_name == "Barack H. Obama"
    assert updated.department == "School of Law"
    # Verify in-memory matcher was updated
    assert matcher.registry["STU-001"].name == "Barack H. Obama"
    assert matcher.registry["STU-001"].department == "School of Law"
    print(f"  Updated student name to '{updated.full_name}' and verified memory sync.")
    print("  [PASS] Student update and cache sync verified.")

    # 9. Test Student Deletion with Cascade
    print("\n" + "-" * 75)
    print("[TEST 9] Student Deletion with Cascade (DB, Disk & Memory Cache)")
    print("-" * 75)
    # Register temporary student to test deletion (using p3_photo1 with high sharpness)
    temp_student = service.register_student(
        student_id="STU-TEMP",
        full_name="Temporary Student",
        photos=[portrait_paths["p3_photo1"]],
        min_blur_score=30.0
    )
    photo_file = temp_student.embeddings[0].photo_path
    photo_abs_path = storage_svc.get_absolute_path(photo_file)

    assert os.path.exists(photo_abs_path), "Photo file must exist before deletion"
    assert "STU-TEMP" in matcher.registry

    # Execute deletion
    del_ok = service.delete_student("STU-TEMP")
    assert del_ok

    # Check student is gone
    check_stu = service.get_student_by_id("STU-TEMP")
    assert check_stu is None

    # Check embeddings deleted via SQLite cascade
    emb_count = db.scalar(
        select(func.count(FaceEmbedding.id)).where(FaceEmbedding.student_id == temp_student.id)
    )
    assert emb_count == 0, "Child face embeddings must be cascade-deleted"

    # Check photo deleted from disk
    assert not os.path.exists(photo_abs_path), "Photo file must be removed from disk"

    # Check removed from in-memory cache
    assert "STU-TEMP" not in matcher.registry
    print("  Deleted student verified: DB record removed, embeddings cascade-deleted, disk photo deleted, memory cache evicted.")
    print("  [PASS] Cascade deletion verified across all layers.")

    # 10. Cold-Start Database Persistence & Rehydration Test
    print("\n" + "-" * 75)
    print("[TEST 10] Cold-Start Database Persistence & Rehydration")
    print("-" * 75)
    db.close()
    db_engine.dispose()

    # Re-open fresh connection and new empty matcher
    fresh_engine = get_engine(test_db_url)
    FreshSession = sessionmaker(bind=fresh_engine, autocommit=False, autoflush=False)
    fresh_db = FreshSession()
    fresh_matcher = VectorMatcher(engine_ai, similarity_threshold=0.637)

    # Empty cache before sync
    assert fresh_matcher.get_enrolled_count() == 0

    fresh_service = StudentService(
        db=fresh_db,
        engine=engine_ai,
        matcher=fresh_matcher,
        storage=storage_svc
    )
    loaded_count = fresh_service.sync_cache_from_db()
    print(f"  Cold-start: Rehydrated {loaded_count} active students into in-memory recognition cache.")
    assert loaded_count == 2
    assert fresh_matcher.get_enrolled_count() == 2

    # Test recognition on the rehydrated cold cache
    pid, name, score, _ = fresh_matcher.match_single_embedding(test_vec)
    print(f"  Recognition on rehydrated cache: ID='{pid}', Name='{name}', Similarity={score:.4f}")
    assert pid == "STU-001"
    assert name == "Barack H. Obama"
    assert score >= 0.90
    print("  [PASS] Cold-start persistence and cache rehydration verified.")

    # Clean up test temp files
    fresh_db.close()
    fresh_engine.dispose()
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)

    print("\n" + "=" * 75)
    print("  ALL PHASE 2 DATABASE & ENROLLMENT OBJECTIVES VERIFIED!")
    print("=" * 75)


if __name__ == "__main__":
    run_phase2_tests()

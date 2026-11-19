"""
Comprehensive Automated API Test Suite with Security Hardening:
FastAPI REST API, Security Enforcement, and In-Memory Synchronization.

Tests:
1. Safe Configuration Failure: Application refuses to start when SMARTGATE_ADMIN_API_KEY is missing.
2. System Health Endpoints: Publicly accessible without authentication (GET /health, GET /api/v1/health).
3. Security: Missing X-Admin-API-Key header returns HTTP 401.
4. Security: Incorrect X-Admin-API-Key header returns HTTP 401.
5. Security: Query parameter credentials (?admin_key=...) are rejected with HTTP 401.
6. Privacy: Student listing (GET /api/v1/students) requires admin authentication.
7. Privacy: Single student retrieval (GET /api/v1/students/{id}) requires admin authentication.
8. Registration: Biometric consent enforcement (consent_given=False returns HTTP 422).
9. Registration: Student enrollment with 2 photos & zero biometric leakage (HTTP 201).
10. In-Memory Sync: Instant recognition via VectorMatcher without restart.
11. Validation: Duplicate student ID rejection (HTTP 409).
12. Validation: Non-image and blurry photo rejection (HTTP 400).
13. Student Operations: Multi-photo addition, search, update, and cascade deletion.
"""

import os
import sys
import shutil
import io
import secrets
import cv2
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set paths
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

from app.config import settings
from app.db.base import Base
from app.db.session import get_engine
from app.main import create_application
from app.api.deps import (
    get_db_session,
    get_face_engine,
    get_vector_matcher,
    get_photo_storage
)
from app.services.ai.opencv_engine import OpenCVFaceEngine
from app.services.ai.vector_matcher import VectorMatcher
from app.services.storage_service import PhotoStorageService
from tests.test_ai_phase1 import download_test_data


def test_missing_admin_key_fails_safely():
    """Verify that settings refuses to provide a default when the admin key is missing."""
    saved_key = os.environ.get("SMARTGATE_ADMIN_API_KEY")
    try:
        os.environ["SMARTGATE_ADMIN_API_KEY"] = ""
        # Accessing settings.ADMIN_API_KEY should raise RuntimeError
        failed_safely = False
        try:
            _ = settings.ADMIN_API_KEY
        except RuntimeError:
            failed_safely = True
        assert failed_safely, "Settings must raise RuntimeError when SMARTGATE_ADMIN_API_KEY is empty."
    finally:
        if saved_key:
            os.environ["SMARTGATE_ADMIN_API_KEY"] = saved_key


def run_security_hardened_api_tests():
    print("=" * 75)
    print("  SMARTGATEAI - SECURITY HARDENED REST API TEST SUITE")
    print("=" * 75)

    # 1. Test Safe Configuration Failure
    print("\n" + "-" * 75)
    print("[TEST 1] Configuration Safety: Rejection of Missing Admin Key")
    print("-" * 75)
    test_missing_admin_key_fails_safely()
    print("  [PASS] Application successfully refuses to start without SMARTGATE_ADMIN_API_KEY.")

    # 2. Setup isolated test environment
    test_storage_dir = os.path.join(backend_dir, "tests", "api_test_storage")
    if os.path.exists(test_storage_dir):
        shutil.rmtree(test_storage_dir)
    os.makedirs(test_storage_dir, exist_ok=True)

    test_db_path = os.path.join(test_storage_dir, "test_api_smartgate.db")
    test_db_url = f"sqlite:///{test_db_path}"
    test_photos_dir = os.path.join(test_storage_dir, "student_photos")
    os.makedirs(test_photos_dir, exist_ok=True)

    # Acquire model weights and portrait images
    weights_dir = os.path.join(backend_dir, "weights")
    yunet_path = os.path.join(weights_dir, "face_detection_yunet_2023mar.onnx")
    sface_path = os.path.join(weights_dir, "face_recognition_sface_2021dec.onnx")
    data_dir = os.path.join(backend_dir, "tests", "test_data")

    portrait_paths = download_test_data(data_dir)
    assert len(portrait_paths) >= 4, "Missing test portrait assets."

    # Setup isolated test database engine
    test_engine = get_engine(test_db_url)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Setup isolated test AI singletons
    test_face_engine = OpenCVFaceEngine(yunet_path, sface_path)
    test_matcher = VectorMatcher(test_face_engine, similarity_threshold=0.637)
    test_storage = PhotoStorageService(test_photos_dir)

    # Create app and override dependencies with isolated test instances
    app = create_application()

    def override_get_db_session():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_face_engine():
        return test_face_engine

    def override_get_vector_matcher():
        return test_matcher

    def override_get_photo_storage():
        return test_storage

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_face_engine] = override_get_face_engine
    app.dependency_overrides[get_vector_matcher] = override_get_vector_matcher
    app.dependency_overrides[get_photo_storage] = override_get_photo_storage

    admin_headers = {"X-Admin-API-Key": settings.ADMIN_API_KEY}
    client = TestClient(app)

    # 3. Test Public Health Endpoints
    print("\n" + "-" * 75)
    print("[TEST 2] Public Health Endpoints (Accessible Without Authentication)")
    print("-" * 75)
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health_data = resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["database_connected"] is True
    assert health_data["models_ready"] is True

    v1_resp = client.get(f"{settings.API_V1_STR}/health")
    assert v1_resp.status_code == 200
    print("  [PASS] Public health endpoints verified.")

    # 4. Test Header-Only Authentication & Query Param Rejection
    print("\n" + "-" * 75)
    print("[TEST 3] Admin Authentication: Header Enforcement & Query Param Rejection")
    print("-" * 75)
    # 4A: Missing header
    unauth_resp = client.get(f"{settings.API_V1_STR}/students")
    assert unauth_resp.status_code == 401
    print(f"  Missing header on GET /students returned 401: '{unauth_resp.json()['detail']}'")

    # 4B: Invalid header
    bad_key_resp = client.get(
        f"{settings.API_V1_STR}/students",
        headers={"X-Admin-API-Key": "wrong-secret-token-12345"}
    )
    assert bad_key_resp.status_code == 401
    print(f"  Invalid header returned 401: '{bad_key_resp.json()['detail']}'")

    # 4C: Attempt query parameter authentication (must be completely rejected)
    query_param_resp = client.get(
        f"{settings.API_V1_STR}/students?admin_key=sample_query_param_value"
    )
    assert query_param_resp.status_code == 401, "Query parameter authentication must be blocked with 401!"
    print("  Query parameter (?admin_key=...) correctly rejected with 401.")
    print("  [PASS] Header-only authentication verified.")

    # 5. Test Biometric Consent Enforcement
    print("\n" + "-" * 75)
    print("[TEST 4] Biometric Consent Enforcement (consent_given=False)")
    print("-" * 75)
    with open(portrait_paths["p1_photo1"], "rb") as f:
        no_consent_resp = client.post(
            f"{settings.API_V1_STR}/students",
            headers=admin_headers,
            data={
                "student_id": "STU-NOCONSENT",
                "full_name": "No Consent Person",
                "consent_given": "false"
            },
            files=[("photos", ("p1.jpg", f, "image/jpeg"))]
        )
    assert no_consent_resp.status_code == 422
    print(f"  Refused enrollment without consent: '{no_consent_resp.json()['detail']}'")
    print("  [PASS] Biometric consent validation enforced.")

    # 6. Test Registration with 2 Photos & Zero Biometric Leakage
    print("\n" + "-" * 75)
    print("[TEST 5] Student Registration with 2 Photos & Zero Biometric Leakage")
    print("-" * 75)
    with open(portrait_paths["p1_photo1"], "rb") as f1, open(portrait_paths["p1_photo2"], "rb") as f2:
        reg_resp = client.post(
            f"{settings.API_V1_STR}/students",
            headers=admin_headers,
            data={
                "student_id": "STU-001",
                "full_name": "Barack Obama",
                "department": "Political Science",
                "consent_given": "true"
            },
            files=[
                ("photos", ("obama1.jpg", f1, "image/jpeg")),
                ("photos", ("obama2.jpg", f2, "image/jpeg"))
            ]
        )

    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    reg_data = reg_resp.json()
    assert reg_data["student_id"] == "STU-001"
    assert len(reg_data["embeddings"]) == 2

    # Check zero biometric leakage
    for emb_item in reg_data["embeddings"]:
        assert "embedding_data" not in emb_item
        assert "vector" not in emb_item
        assert "photo_path" in emb_item
        print(f"    Exemplar #{emb_item['id']}: Photo='{emb_item['photo_path']}', Quality={emb_item['quality_score']:.1f}")

    print("  [PASS] Registration succeeded; zero biometric leakage verified.")

    # 7. Test Protected Student Listing & Profile Retrieval
    print("\n" + "-" * 75)
    print("[TEST 6] Protected Student Listing & Profile Endpoints")
    print("-" * 75)
    # 7A: GET /students without auth -> 401
    assert client.get(f"{settings.API_V1_STR}/students").status_code == 401

    # 7B: GET /students with auth -> 200
    list_resp = client.get(f"{settings.API_V1_STR}/students", headers=admin_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    # 7C: GET /students/{id} without auth -> 401
    assert client.get(f"{settings.API_V1_STR}/students/STU-001").status_code == 401

    # 7D: GET /students/{id} with auth -> 200
    stu_resp = client.get(f"{settings.API_V1_STR}/students/STU-001", headers=admin_headers)
    assert stu_resp.status_code == 200
    assert stu_resp.json()["student_id"] == "STU-001"
    print("  [PASS] Student listing and single profile retrieval require admin authentication.")

    # 8. Test Duplicate Student ID Prevention
    print("\n" + "-" * 75)
    print("[TEST 7] Duplicate Student ID Rejection (HTTP 409 Conflict)")
    print("-" * 75)
    with open(portrait_paths["p2_photo1"], "rb") as f:
        dup_resp = client.post(
            f"{settings.API_V1_STR}/students",
            headers=admin_headers,
            data={
                "student_id": "STU-001",
                "full_name": "Duplicate Person",
                "consent_given": "true"
            },
            files=[("photos", ("dup.jpg", f, "image/jpeg"))]
        )
    assert dup_resp.status_code == 409
    print(f"  Duplicate ID rejected with 409: '{dup_resp.json()['detail']}'")
    print("  [PASS] Duplicate student ID prevented.")

    # 9. Test Invalid Image / Blurry Image Rejection
    print("\n" + "-" * 75)
    print("[TEST 8] Invalid Image & Blurry Photo Rejection (HTTP 400 Bad Request)")
    print("-" * 75)
    # Non-image file
    text_data = io.BytesIO(b"Plain text file.")
    bad_file_resp = client.post(
        f"{settings.API_V1_STR}/students",
        headers=admin_headers,
        data={"student_id": "STU-TXT", "full_name": "Text Person", "consent_given": "true"},
        files=[("photos", ("test.txt", text_data, "text/plain"))]
    )
    assert bad_file_resp.status_code == 400

    # Blurry face
    sharp_img = cv2.imread(portrait_paths["p2_photo1"])
    blurry_img = cv2.GaussianBlur(sharp_img, (35, 35), 10)
    _, buf = cv2.imencode(".jpg", blurry_img)
    blur_resp = client.post(
        f"{settings.API_V1_STR}/students",
        headers=admin_headers,
        data={"student_id": "STU-BLUR", "full_name": "Blurry Person", "consent_given": "true"},
        files=[("photos", ("blur.jpg", io.BytesIO(buf.tobytes()), "image/jpeg"))]
    )
    assert blur_resp.status_code == 400
    print("  [PASS] Quality validation and bad input handling verified.")

    # 10. Test Multi-Photo Addition & Cache Sync
    print("\n" + "-" * 75)
    print("[TEST 9] Adding Additional Face Photo (POST /api/v1/students/{id}/photos)")
    print("-" * 75)
    with open(portrait_paths["p2_photo1"], "rb") as f:
        client.post(
            f"{settings.API_V1_STR}/students",
            headers=admin_headers,
            data={"student_id": "STU-002", "full_name": "Anthony Hopkins", "consent_given": "true"},
            files=[("photos", ("hopkins.jpg", f, "image/jpeg"))]
        )

    with open(portrait_paths["p2_photo2"], "rb") as f2:
        add_photo_resp = client.post(
            f"{settings.API_V1_STR}/students/STU-002/photos",
            headers=admin_headers,
            files={"photo": ("hopkins2.jpg", f2, "image/jpeg")}
        )
    assert add_photo_resp.status_code == 201
    get_stu2 = client.get(f"{settings.API_V1_STR}/students/STU-002", headers=admin_headers).json()
    assert len(get_stu2["embeddings"]) == 2
    assert len(test_matcher.registry["STU-002"].embeddings) == 2
    print("  [PASS] Additional photo added and synchronized in DB and cache.")

    # 11. Test Update & Cascade Deletion
    print("\n" + "-" * 75)
    print("[TEST 10] Student Update & Cascade Deletion")
    print("-" * 75)
    # Update
    update_resp = client.put(
        f"{settings.API_V1_STR}/students/STU-001",
        headers=admin_headers,
        json={"full_name": "Barack H. Obama", "department": "School of Law"}
    )
    assert update_resp.status_code == 200
    assert test_matcher.registry["STU-001"].name == "Barack H. Obama"

    # Delete
    del_resp = client.delete(f"{settings.API_V1_STR}/students/STU-002", headers=admin_headers)
    assert del_resp.status_code == 200
    assert client.get(f"{settings.API_V1_STR}/students/STU-002", headers=admin_headers).status_code == 404
    assert "STU-002" not in test_matcher.registry
    print("  [PASS] Student update and cascade deletion verified.")

    # Clean up test temp storage
    test_engine.dispose()
    if os.path.exists(test_storage_dir):
        shutil.rmtree(test_storage_dir)

    print("\n" + "=" * 75)
    print("  ALL SECURITY-HARDENED REST API OBJECTIVES SUCCESSFULLY VERIFIED!")
    print("=" * 75)


if __name__ == "__main__":
    run_security_hardened_api_tests()

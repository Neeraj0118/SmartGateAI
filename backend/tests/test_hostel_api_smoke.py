"""
Smoke test for Hostel Exit Permission API endpoints.
Verifies:
1. Endpoints require X-Admin-API-Key.
2. Create permission request for existing student (e.g. 230111472).
3. List permissions with filtering.
4. Approve permission.
5. Get permission stats.
6. Overdue outing and security alert retrieval.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.config import settings
from app.main import create_application

app = create_application()
client = TestClient(app)

ADMIN_HEADERS = {"X-Admin-API-Key": settings.ADMIN_API_KEY}

def test_hostel_api_smoke():
    print("--> 1. Testing Auth protection...")
    resp = client.get("/api/v1/hostel-permissions")
    assert resp.status_code == 401, f"Expected 401 Unauthorized, got {resp.status_code}"
    print("    [PASS] Auth protection verified.")

    print("--> 2. Testing Stats endpoint...")
    resp = client.get("/api/v1/hostel-permissions/stats", headers=ADMIN_HEADERS)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    stats = resp.json()
    print(f"    [PASS] Current stats: {stats}")

    print("--> 3. Testing Permission Creation...")
    now = datetime.now(timezone.utc)
    dep_date = now.strftime("%Y-%m-%d")
    dep_time = (now + timedelta(minutes=10)).strftime("%H:%M")
    ret_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    ret_time = "18:00"

    payload = {
        "student_id": "230111472",
        "student_name": "Neeraj Giri",
        "reason": "Family Function - Medical Visit",
        "departure_date": dep_date,
        "departure_time": dep_time,
        "expected_return_date": ret_date,
        "expected_return_time": ret_time
    }
    resp = client.post("/api/v1/hostel-permissions", json=payload, headers=ADMIN_HEADERS)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    created = resp.json()
    perm_id = created["id"]
    assert created["status"] == "Pending"
    assert created["student_id"] == "230111472"
    print(f"    [PASS] Created permission #{perm_id} with status {created['status']}.")

    print("--> 4. Testing Listing & Filtering...")
    resp = client.get("/api/v1/hostel-permissions?status=Pending", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    listing = resp.json()
    assert listing["total"] >= 1
    found = any(p["id"] == perm_id for p in listing["items"])
    assert found, f"Permission {perm_id} not found in pending list"
    print(f"    [PASS] Listed {listing['total']} pending permissions.")

    print("--> 5. Testing Approval...")
    resp = client.post(f"/api/v1/hostel-permissions/{perm_id}/approve", headers=ADMIN_HEADERS)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    approved = resp.json()
    assert approved["status"] == "Approved"
    assert approved["approved_by"] == "Administrator"
    print(f"    [PASS] Approved permission #{perm_id}.")

    print("--> 6. Testing Active Outings & Security Alerts...")
    resp = client.get("/api/v1/hostel-permissions/outings/active", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    print(f"    [PASS] Active outings: {resp.json()['total']}")

    resp = client.get("/api/v1/hostel-permissions/alerts", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    print(f"    [PASS] Security alerts: {resp.json()['total']}")

    # Clean up test permission
    from app.db.session import SessionLocal
    from app.models.hostel_permission import HostelPermission
    cleanup_db = SessionLocal()
    cleanup_db.query(HostelPermission).filter(HostelPermission.id == perm_id).delete()
    cleanup_db.commit()
    cleanup_db.close()

    print("\nALL HOSTEL API SMOKE TESTS PASSED!")

if __name__ == "__main__":
    test_hostel_api_smoke()

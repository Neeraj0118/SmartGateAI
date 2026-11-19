"""
Integration test for Swagger UI and authenticated endpoints.
Simulates browser preflight and fetch requests against the live server.
"""

import os
import sys
import time
import subprocess
import requests
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)

load_dotenv(os.path.join(root_dir, ".env"))
admin_key = os.getenv("SMARTGATE_ADMIN_API_KEY")

if not admin_key:
    print("FATAL: SMARTGATE_ADMIN_API_KEY is not set.")
    sys.exit(1)


def run_integration_test():
    print("=" * 75)
    print("  SMARTGATEAI - SWAGGER UI & GET /api/v1/students INTEGRATION TEST")
    print("=" * 75)

    # Launch server on 127.0.0.1:8000
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Wait for server to warm up
        time.sleep(3)

        base_url = "http://127.0.0.1:8000"

        # 1. Verify Health
        h = requests.get(f"{base_url}/health", timeout=5)
        print(f"[CHECK 1] GET /health -> Status: {h.status_code}, Body: {h.json()}")
        assert h.status_code == 200

        # 2. Check OpenAPI Servers config
        o = requests.get(f"{base_url}/openapi.json", timeout=5).json()
        print(f"[CHECK 2] OpenAPI Servers -> {o.get('servers')}")
        assert o.get("servers") == [{"url": "/", "description": "Localhost Server"}]

        # 3. Simulate Browser Preflight (OPTIONS /api/v1/students)
        preflight_origins = ["http://127.0.0.1:8000", "http://localhost:8000"]
        for orig in preflight_origins:
            opt = requests.options(
                f"{base_url}/api/v1/students",
                headers={
                    "Origin": orig,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "x-admin-api-key, accept"
                },
                timeout=5
            )
            print(f"[CHECK 3] Browser Preflight (OPTIONS) from {orig} -> Status: {opt.status_code}, Allow-Origin: '{opt.headers.get('access-control-allow-origin')}'")
            assert opt.status_code == 200
            assert opt.headers.get("access-control-allow-origin") == orig

        # 4. Simulate Swagger UI before Authorization (Unauthenticated GET)
        unauth = requests.get(
            f"{base_url}/api/v1/students",
            headers={"Origin": "http://127.0.0.1:8000", "Accept": "application/json"},
            timeout=5
        )
        print(f"[CHECK 4] Unauthenticated GET /api/v1/students -> Status: {unauth.status_code}, Response: {unauth.text}")
        assert unauth.status_code == 401
        assert "WWW-Authenticate" not in unauth.headers, "Non-standard WWW-Authenticate header must not be sent"

        # 5. Register a sample student if none exist
        data_dir = os.path.join(backend_dir, "tests", "test_data")
        photo1 = os.path.join(data_dir, "person1_obama_photo1.jpg")
        photo2 = os.path.join(data_dir, "person1_obama_photo2.jpg")

        if os.path.exists(photo1):
            with open(photo1, "rb") as f1, open(photo2, "rb") as f2:
                reg = requests.post(
                    f"{base_url}/api/v1/students",
                    headers={"X-Admin-API-Key": admin_key},
                    data={
                        "student_id": "STU-SWAGGER-001",
                        "full_name": "Swagger Test Student",
                        "department": "Engineering",
                        "consent_given": "true"
                    },
                    files=[
                        ("photos", ("p1.jpg", f1, "image/jpeg")),
                        ("photos", ("p2.jpg", f2, "image/jpeg"))
                    ],
                    timeout=10
                )
                print(f"[CHECK 5] Student Registration via API -> Status: {reg.status_code} (201 Created or 409 if already exists)")

        # 6. Simulate Swagger UI after Authorization (Authenticated GET /api/v1/students)
        auth_resp = requests.get(
            f"{base_url}/api/v1/students",
            headers={
                "Origin": "http://127.0.0.1:8000",
                "X-Admin-API-Key": admin_key,
                "Accept": "application/json"
            },
            timeout=5
        )
        print(f"[CHECK 6] Authenticated GET /api/v1/students -> Status: {auth_resp.status_code}")
        print(f"          Response Body: {auth_resp.json()}")
        assert auth_resp.status_code == 200
        data = auth_resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

        print("\n" + "=" * 75)
        print("  ALL SWAGGER UI INTEGRATION CHECKS PASSED WITH ZERO ERRORS!")
        print("=" * 75)

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    run_integration_test()

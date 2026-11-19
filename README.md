# SmartGateAI

> **AI-powered face recognition security system** — real-time entry/exit monitoring with a professional React dashboard.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| Database | SQLite (via SQLAlchemy) |
| AI — Detection | YuNet (OpenCV DNN, ONNX) |
| AI — Recognition | SFace 128-D embeddings (OpenCV DNN, ONNX) |
| Frontend | React 19 · Vite 8 · Tailwind CSS v3 |
| Routing | React Router v6 |
| Charts | Recharts |
| Icons | Lucide React |
| Camera Stream | MJPEG over FastAPI (`/api/v1/camera/stream`) |

---

## Project Structure

```
SmartGateAI/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # FastAPI route handlers
│   │   │   ├── students.py     # Student CRUD + photo upload
│   │   │   ├── camera.py       # Camera start/stop/stream
│   │   │   └── attendance.py   # Attendance log & stats
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── camera_service.py     # Singleton camera manager + MJPEG
│   │   │   ├── face_engine.py        # OpenCVFaceEngine (YuNet + SFace)
│   │   │   └── vector_matcher.py     # VectorMatcher (cosine similarity)
│   │   ├── db/                 # Database setup + base models
│   │   └── core/               # Config, security, middleware
│   ├── tests/                  # Test scripts (TC1–TC5 multi-face, API tests)
│   ├── weights/                # ONNX model files (not in git)
│   └── run_server.py           # Uvicorn entry point
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios API client modules
│   │   ├── components/         # Sidebar, Layout, StatCard, StatusBadge
│   │   ├── context/            # AuthContext (admin key in session memory)
│   │   └── pages/              # Dashboard, Monitoring, Students, Attendance, Settings
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── vite.config.js
├── storage/                    # Uploaded face photos (not in git)
├── venv/                       # Python virtual environment (not in git)
├── .env                        # Secrets — NEVER commit (in .gitignore)
├── .env.example                # Safe template
└── .gitignore
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- ONNX model weights in `backend/weights/` (run `python backend/tests/download_models.py` if missing)

### 1 — Start the Backend

```powershell
cd C:\Users\neera\OneDrive\Desktop\SmartGateAI
.\venv\Scripts\activate
cd backend
python run_server.py --port 8000
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/docs  | Swagger UI (interactive API docs) |
| http://127.0.0.1:8000/api/v1/camera/stream | MJPEG live stream |

### 2 — Start the Frontend

```powershell
cd C:\Users\neera\OneDrive\Desktop\SmartGateAI\frontend
npm run dev
```

Open **http://localhost:5173** in your browser.  
You will be prompted for the Admin API Key on first load (from `backend/.env` → `ADMIN_API_KEY`).

### 3 — Standalone Webcam Recognition (optional)

Runs YuNet+SFace recognition directly in an OpenCV window on your desktop.  
**Do not use this while the browser camera stream is active** — both cannot access the webcam simultaneously.

```powershell
cd C:\Users\neera\OneDrive\Desktop\SmartGateAI
.\venv\Scripts\python.exe webcam_recognition.py
```

Keyboard controls: `Q` or `ESC` to quit · `R` to reload embeddings · `P` to pause.

---

## Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Stats overview, weekly chart, recent students |
| Live Monitor | `/monitoring` | MJPEG camera stream, face detection panel, start/stop |
| Students | `/students` | Enroll/delete students, search, photo upload |
| Attendance | `/attendance` | Recognition event log with filters and pagination |
| Settings | `/settings` | System status, model status, session key management |

---

## API Reference (key endpoints)

```
GET  /health                                  Public health check
GET  /api/v1/health                           Detailed health (DB + AI)
POST /api/v1/students                         Enroll student (multipart, admin)
GET  /api/v1/students                         List all students (admin)
GET  /api/v1/students/{id}                    Student profile (admin)
PUT  /api/v1/students/{id}                    Update student (admin)
DELETE /api/v1/students/{id}                  Delete student (admin)
POST /api/v1/students/{id}/photos             Add face photo (admin)
POST /api/v1/camera/start                     Start camera stream (admin)
POST /api/v1/camera/stop                      Stop camera stream (admin)
GET  /api/v1/camera/status                    Camera status + recognition state (public)
GET  /api/v1/camera/stream                    MJPEG stream (public)
GET  /api/v1/attendance/                      Recognition event log (admin)
GET  /api/v1/attendance/stats                 Aggregated stats (admin)
```

Authentication: pass the admin key as `X-Admin-API-Key` header.

---

## Security Notes

- Backend is bound to `127.0.0.1` only — **not reachable from the network**.
- Admin API key is stored in `backend/.env` and read at startup.  
  It is **never** printed in logs, terminal output, or the UI.
- In the React frontend, the key lives in React state + `sessionStorage` only.  
  It is never written to source code, `localStorage`, or cookies.
- Face embeddings are stored in SQLite and are never exposed via the API.

---

## Known Limitations

| Limitation | Detail |
|-----------|--------|
| Webcam exclusivity | The physical webcam can only be held by one process. Do not run `webcam_recognition.py` and the browser stream simultaneously. |
| Attendance data | Records appear only after the camera has been started and faces recognised. No synthetic/historical data is generated. |
| Chunk size warning | Vite warns about the 774 kB JS bundle (Recharts is large). Not a runtime error — use code splitting in production. |
| Similarity threshold | Current default: `0.57` cosine similarity. Tune in `backend/app/services/vector_matcher.py`. |

---

## Running Tests

```powershell
# API endpoint tests (requires backend running on :8000)
& ".\venv\Scripts\python.exe" backend\tests\test_api_endpoints.py

# Multi-face recognition tests (TC1–TC5, offline — no server needed)
& ".\venv\Scripts\python.exe" backend\tests\test_multi_face_recognition.py

# AI pipeline tests
& ".\venv\Scripts\python.exe" backend\tests\test_ai_phase1.py
```

---

## Enrolled Students (Production DB)

| Student ID | Name | Enrolled Via |
|-----------|------|-------------|
| `STU-SWAGGER-001` | Swagger Test Student | Swagger UI (person1_obama photos) |
| `230111472` | Neeraj Giri | Direct registration (personal photos) |

> ⚠️ Do not delete these records — they are reference enrollment data.

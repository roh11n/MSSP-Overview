# MSSP-Overview — PRD / Deployment Record

## Problem statement
Deploy the MSSP SOC KPI Dashboard (React + FastAPI + MongoDB) "as-is". Code was
cloned from https://github.com/roh11n/MSSP-Overview.git into /app. User wants the
IRIS copilot answered by a **local LLM** and insisted on a self-hosted local model
(Ollama / Qwen / Llama). Emergent managed deploy cannot host a local LLM
(~0.25 CPU / 1 GB RAM), so the deliverable is a self-hosted Docker package.

## Architecture
- **Backend** FastAPI (`/app/backend`), all routes under `/api`, JWT+bcrypt auth,
  MongoDB via motor. Dashboards from deterministic `mock_data.py`; optional live
  overlays from uploaded QRadar/XSOAR/threat-intel CSVs.
- **Frontend** React (CRA + craco), 7 persona dashboards, IRIS chat, PPTX export.
- **LLM (IRIS)** now backed by **Ollama** (`backend/llm.py`, `backend/copilot.py`)
  over HTTP. Model auto-pulled on startup. Graceful **rule-based fallback** when
  Ollama is unreachable (e.g. the Emergent preview pod).
- **Deploy** self-hosted `docker compose`: mongo + ollama + backend + frontend
  (Nginx serves the SPA and reverse-proxies `/api` -> backend, so same-origin, no CORS).

## Env vars
Backend: MONGO_URL, DB_NAME, JWT_SECRET (required), ADMIN_EMAIL, ADMIN_PASSWORD,
OLLAMA_BASE_URL, OLLAMA_MODEL, CORS_ORIGINS. Frontend: REACT_APP_BACKEND_URL
(empty => same-origin in the Docker build).

## What's been implemented (2026-06)
- Cloned repo into /app; installed deps; app running in preview.
- Fixed un-installable pin `torch==2.13.0+cpu` -> then removed ML stack entirely.
- Rewrote `llm.py` to call Ollama (`/api/chat`, `/api/pull`, `/api/tags`) with
  cached availability + graceful fallback; updated `copilot._llm_answer`.
- Removed torch/transformers/accelerate/safetensors/tokenizers from requirements.
- Added deployment package: `backend/Dockerfile` (+ .dockerignore),
  `frontend/Dockerfile` + `frontend/nginx.conf` (+ .dockerignore),
  `docker-compose.yml`, `.env.example`, `DEPLOYMENT.md` runbook.
- Smoke test (testing agent, iteration_7): 52/52 backend + 21/21 frontend PASS
  (login, 6 personas, protected-route redirects, all 7 dashboards x 3 periods,
  tenants, copilot, insights, PPTX export). Re-verified endpoints after LLM refactor.

## Notes / status
- In the Emergent **preview**, IRIS runs rule-based (no Ollama service). The real
  local LLM activates only in the self-hosted Docker stack — this is by design.
- `emergentintegrations` is unused by code but kept in requirements; the backend
  Dockerfile installs it via Emergent's extra index URL.

## Backlog / next
- (Optional) MongoDB auth + TLS reverse proxy (Caddy) — documented in DEPLOYMENT.md.
- (Optional) Recharts `ResponsiveContainer` width/height console warnings (cosmetic).
- (Optional) Data migration mongodump -> mongorestore (steps in DEPLOYMENT.md).

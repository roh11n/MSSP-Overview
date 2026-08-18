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

## Phase 6 (2026-06) — live XSOAR wiring + scheduled reports
- **Detection Engineering now data-driven:** `xsoar_ingest.compute_detection_overlay`
  binds uploaded XSOAR *MITRE Tactic Name* / *MITRE Technique Name* columns to the
  MITRE heat-map and derives the Rule Effectiveness table (triggers, FP%, precision,
  recall, status) from `rule_name` + `close_reason`. Overlaid onto `/dashboard/detection-engineering`
  only when live data exists (else mock). UI shows a "Live · XSOAR" badge.
- **IRIS grounded on live XSOAR:** `copilot.build_snapshot(..., live_xsoar)` +
  `/copilot/chat` inject live noisy-rule/FP + top-rule KPIs so users can ask
  "which rule has the highest FP rate?". Rule-based fallback also answers it.
- **Scheduled email reports:** `scheduler.py` (APScheduler) weekly (Mon 08:00 UTC) /
  monthly (1st 08:00 UTC) cron auto-emails the PPTX. CRUD at `/api/reports/schedules`
  + `/run-now`; managed in Settings › Scheduled Email Reports. Delivery is
  console-mocked unless SMTP_* env is set. New dep: apscheduler==3.11.3.
- Verified: testing agent iteration_8 — backend 10/10 (+52 regression), frontend 100%.

## Phase 7 (2026-06) — removed dummy data (live-only dashboards)
- **No mock KPI numbers anywhere.** `tenants.py` now returns zeroed blank templates
  (schema preserved) instead of `mock_data`. All six dashboards are live-only:
  Executive & Client are computed from XSOAR (+TI) via `xsoar_ingest.compute_client`
  and `server._live_executive`; Detection from `compute_detection_overlay`; SOC/SOAR/TI
  already live. Each returns `{data_status:"empty"}` with a UI empty-state until data is uploaded.
- `recommendations.generate` rewritten to be live-executive-driven (returns [] when empty).
- PPTX/scheduled reports use `scheduler.build_bundle` (live executive + detection overlay);
  `pptx_export` chart helpers now render "No data" instead of crashing on blanks.
- **Removed demo persona users** (only `admin@mssp-soc.io` seeded) and the login quick-login buttons.
- **Removed test data**: acme-corp XSOAR upload, test schedules/emails/uploads. Demo tenants (Acme, GlobalBank) kept per user request.

## Bug fixes
- 2026-06: Threat-Intel (and all) uploads didn't show until a manual refresh — `UploadModal`
  now calls `queryClient.invalidateQueries()` after a successful upload so dashboards refetch
  immediately. Verified end-to-end (iteration_10): .xlsx TI upload flips the dashboard to live
  with no page reload.

## Phase 8 (2026-06) — Detection Engineering: rule catalog + log validation
- New upload sources `rules` (rule catalog) and `log_validation` (Priority) with ingest
  modules `rules_ingest.py` / `logval_ingest.py` and DELETE endpoints.
- **Rule Effectiveness**: XSOAR incident rule/name matched (normalised) against catalog
  `Rule Name` → triggers per rule; average threshold splits rules into
  above-avg / near-avg / below-avg / not-triggered (StatChips + table on /detection).
- **MITRE coverage** heat-map + coverage KPIs from catalog ATT&CK Tactic/Technique
  (';'-separated supported). detection_coverage=%mapped, use_case_coverage=%with log source,
  mitre_coverage=distinct tactics/14, quality_score=composite. ATLAS not derivable → N/A.
- **Log Priority pie** from the Log Validation `Priority` column.
- Detection endpoint composes rules + XSOAR overlay + log-validation; empty-state when none.
- Verified iteration_13: backend 8/8, frontend 100%.

## Backlog / next
- (Optional) MongoDB auth + TLS reverse proxy (Caddy) — documented in DEPLOYMENT.md.
- (Optional) Recharts `ResponsiveContainer` width/height console warnings (cosmetic).
- (Optional) Data migration mongodump -> mongorestore (steps in DEPLOYMENT.md).

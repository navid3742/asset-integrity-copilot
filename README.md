# Asset Integrity Copilot — Oil & Gas Edition (v4)

**An independent, fictional industrial AI portfolio demo.** A single OpenAI Agents SDK agent retrieves technical references and connected records for pumps, control valves and pressure vessels. It does not control industrial equipment, approve engineering work, or establish fitness for service.

> All assets, inspection measurements, procedures, work orders, incident cases, personnel and statuses in this repository are **synthetic**. The documents are not authorized operational SOPs. Do not upload confidential plant documents or use model responses to make equipment safety decisions.

## What changed from Factory Copilot v3?

The AI design stayed the same: **React + TypeScript**, **FastAPI**, **OpenAI Agents SDK**, **BM25 with optional embedding similarity**, **SQLite**, a dark industrial dashboard, separate report approval and tests. We migrated aerospace-style component data to a coherent oil-and-gas mechanical-integrity dataset with new schema, examples, interface labels, tests and evaluation.

- **60 assets:** 20 pumps (`P-201`–`P-220`), 20 control valves (`CV-301`–`CV-320`), 20 pressure vessels (`PV-101`–`PV-120`).
- **180 inspection observations:** including vibration velocity (mm/s RMS), actuator travel deviation (%) and ultrasonic thickness (mm), depending on equipment class.
- **120 maintenance work orders:** completed records and open follow-up activities.
- **12 incident reports** linked to asset IDs, including three showcase cases.
- **15 original fictional knowledge documents:** SOPs, incident summaries, AI governance and quickstart guidance.

**Three interactive demos:**

| Tag | Scenario | Linked case | Related synthetic guidance |
|---|---|---|---|
| `P-204` | Elevated vibration and mechanical-seal leakage observation | `INC-007` | `SOP-PMP-001`, `CASE-INC-007` |
| `CV-310` | Control-valve actuator lag and positioner feedback discrepancy | `INC-010` | `SOP-VLV-003`, `CASE-INC-010` |
| `PV-120` | Vessel thickness trend and external corrosion indication | `INC-012` | `SOP-PV-005`, `CASE-INC-012` |

## Start on macOS (recommended)

Prerequisites: **Python 3.11+**, **Node.js 20+** (22 recommended), npm and an internet connection to install packages.

1. Extract the ZIP and open Terminal in the `asset-integrity-copilot` project folder.
2. Run:

   ```bash
   bash run-mac.command
   ```

3. Open **http://localhost:5173**. By default you are in **offline preview mode**: document retrieval and SQLite queries work, but no model is called.

The startup script creates `.env` if necessary, installs Python packages, installs frontend dependencies, starts FastAPI on port 8000 and starts Vite on port 5173.

**Manual alternative:**

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
export PYTHONPATH="$PWD/backend"
uvicorn app.main:app --reload --port 8000
# New terminal in project root:
cd frontend && npm install && npm run dev
```

## Enable the OpenAI Agents SDK

Edit `.env` in the repository root:

```dotenv
OPENAI_API_KEY=sk-your-private-key-here
DEMO_PASSWORD=choose-a-long-random-demo-password
OPENAI_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
ENABLE_EMBEDDINGS=true
MAX_ESTIMATED_SPEND_USD=3
```

Restart the backend. When a password is configured, enter it in the application's access screen. **Never put the API key in React source files, screenshots or GitHub.** OpenAI API billing is separate from ChatGPT subscriptions.

The default model is `gpt-4.1-mini` because it supports tool calling and has broadly supported SDK behavior. The input/output USD rates in `.env.example` are configurable **estimates**, not a price guarantee. Verify your actual API account pricing, billing and limits before live testing.

The `openai-agents` package is only imported for live mode. A first live run may create a local embedding cache (`backend/data/vector_cache.json`), which is excluded from Git. For a $10 balance, keep the demo in offline mode until you need to validate live tool use.

## How a question moves through the code

```text
Browser React UI (frontend/src/App.tsx)
  → api.ts: POST /api/chat
  → FastAPI (backend/app/main.py)
  → agent.live_chat() in agent.py
      offline: Python retrieval + SQLite evidence + deterministic response
      live: sdk_runtime.py → Agent / Runner.run_sync()
            ├─ search_documents(query) → retrieval.py → BM25 + optional embeddings
            ├─ get_asset(asset_id) → db.py → SQLite asset table
            └─ get_asset_history(asset_id) → db.py → inspections, maintenance, incidents
  → optional SDK output guardrail: check unsupported DOCUMENT citations/actions
  → answer, source cards, and tool trace → React
```

The **three agent tools are read-only** and accept validated arguments. The agent cannot issue SQL, run commands, operate pumps/valves or approve reports. The independent `POST /api/reports/draft` endpoint creates a deterministic pending review; `POST /api/reports/{id}/approve` requires explicit human-originated confirmation. This **demonstration approval is NOT real plant authorization**.

See [Architecture](docs/ARCHITECTURE.md) and [SDK walkthrough](docs/AGENTS_SDK_WALKTHROUGH.md).

## Main API endpoints

| Route | Description |
|---|---|
| `GET /api/health` | Basic health information, no password |
| `GET /api/status` | App mode, model, counts, estimated API usage |
| `POST /api/chat` | Ask a question with optional 6-message history |
| `GET /api/documents` / `GET /api/documents/{id}` | Synthetic knowledge base |
| `GET /api/assets` / `GET /api/assets/{tag}` | Asset registry |
| `GET /api/assets/{tag}/history` | Inspections, maintenance and incidents |
| `GET /api/reports` / `POST /api/reports/draft` | Demo reviews |
| `POST /api/reports/{id}/approve` | Explicit user-confirmed demo approval |
| `GET /api/docs` | FastAPI OpenAPI docs |

## Run tests and evaluation

```bash
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
PYTHONPATH=backend python -m pytest -q backend/tests
PYTHONPATH=backend python backend/scripts/evaluate_retrieval.py
cd frontend && npm run build
```

**Verified during preparation of v4:** 24 offline backend tests passed; the **36-question synthetic BM25 evaluation** measured Hit@1 = 91.7%, Hit@3 = 100.0%, MRR@3 = 0.958; 5/5 unrelated questions rejected. These are **small synthetic corpus retrieval figures**, not live LLM or industrial safety results. Full details: [RETRIEVAL_RESULTS.json](docs/RETRIEVAL_RESULTS.json).

**Unverified in the preparation environment:** npm registry could not be reached, so the full React dependency build wasn't completed (TypeScript/TSX source was syntax-parsed); real paid OpenAI Agents SDK calls and deployment to a Render account were not performed. The mocked SDK tests do not prove live cloud compatibility. Follow [LIVE_VERIFICATION.md](docs/LIVE_VERIFICATION.md) on your Mac.

## Deploy to Render

1. Push the extracted repository to **your own private GitHub repository**; don't commit `.env`.
2. In Render, create a Web Service from the GitHub repo and select **Docker** (or use the included `render.yaml`).
3. Set private environment variables: `OPENAI_API_KEY`, `DEMO_PASSWORD`. Keep the model setting at `gpt-4.1-mini` unless you've verified another model.
4. Deploy. Health endpoint: `/api/health`. Backend serves React's compiled `dist` from the same service.
5. Test the password screen, status, P-204/CV-310/PV-120 queries, pending report, and guarded approval.

**Render free-service caveats:** instances can sleep, local filesystem state is ephemeral, and in-process rate/cost counters reset after restart. Seed data recreates; user-approved demo reports may disappear. For actual persistence, use managed Postgres. Don't expose paid live mode without a strong password and appropriate provider-side usage limits.

## File map

- `frontend/src/App.tsx`: visual dashboard, chat, document modal, asset details, work orders and approval UI
- `frontend/src/api.ts`, `types.ts`: typed browser-to-API requests and data contracts
- `backend/app/main.py`: authenticated FastAPI HTTP routes, rate limiting, safety headers
- `backend/app/agent.py`: system rules, bounded read-only tool dispatcher, deterministic offline preview, budget estimate
- `backend/app/sdk_runtime.py`: Agents SDK Agent/Runner/function tools, per-run traces and output guardrail
- `backend/app/retrieval.py`: section-level BM25, optional cached embedding similarity and citations
- `backend/app/db.py`: SQLite schema and queries; pending/approved demo reports
- `backend/data/asset_integrity_seed.json`: 60 linked assets and related records
- `backend/data/documents.json`: 15 fictional knowledge documents
- `backend/data/generate_seed.py`, `generate_documents.py`: deterministic data/document generators
- `backend/scripts/evaluate_retrieval.py`: labeled keyword-search evaluation
- `backend/tests/`: offline API, security, data integrity and mocked SDK integration tests
- `docs/`: design, evaluation, live checks, walkthrough and interview talk track

## Domain and ethical boundaries

The synthetic documents were informed by broad **mechanical integrity recordkeeping themes** such as those described by [OSHA 29 CFR 1910.119(j)](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.119). This does not establish whether a particular facility is covered by OSHA PSM or demonstrate compliance. The project does not reproduce proprietary API/ASME standards or calculate design limits. Real engineers must use the applicable site-approved procedures, equipment design basis, and verified field data.

This is an **AI-assisted software development portfolio project**. Be accurate about implementation help, changes you've personally verified, and areas still requiring production engineering.

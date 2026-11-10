# Architecture

```text
React + TypeScript (frontend/src)
        │  same-origin /api
        ▼
FastAPI (backend/app/main.py)
  password check, rate limit, request validation
        │
        ▼
agent.py ── offline: deterministic answer from SQLite + keyword search
        │
        ▼  live (API key and password both set)
sdk_runtime.py ── OpenAI Agents SDK Agent + Runner, output guardrail
        │
        ├── search_documents(query)      → retrieval.py → documents.json
        ├── get_asset(asset_id)          → db.py → assets
        └── get_asset_history(asset_id)  → db.py → inspections, maintenance, incidents

Report workflow (not reachable by the agent):
  POST /api/reports/draft          → pending report built from database facts
  POST /api/reports/{id}/approve   → requires an explicit confirmation string
```

## Two kinds of data

**Documents.** Fifteen procedures, incident write-ups and guides in `backend/data/documents.json`. They're split on `##` headings into 77 chunks and searched with BM25. In live mode, OpenAI embeddings are blended in (65% keyword, 35% cosine similarity). The embeddings are cached in `backend/data/vector_cache.json` and recomputed when the documents change.

**Records.** Assets, inspections, work orders and incidents live in SQLite, linked by foreign keys and seeded from `asset_integrity_seed.json` on first start. The agent never writes SQL. Its two record tools take an equipment tag, which is validated against `P-###`, `CV-###` or `PV-###` both in the tool schema and again in the Python dispatcher.

## Tables

| Table | Columns |
|---|---|
| `assets` | id, name, category, service, unit, location, status, criticality, installed_at, design_reference, description |
| `inspections` | id, asset_id, inspected_at, inspection_type, metric, reading, unit, outcome, inspector, notes |
| `maintenance` | id, asset_id, performed_at, work_type, status, description, action_taken, next_step |
| `incidents` | id, asset_id, severity, status, issue, recorded_at, follow_up |
| `reports` | id, asset_id, status (pending/approved), summary, created_at, approved_at |

## Guardrails

- The agent has three read-only tools. Unknown tool names and malformed arguments are rejected by `dispatch_tool`.
- `tool_choice="required"` forces at least one lookup before the first answer; the SDK then resets it to `auto`.
- An output guardrail blocks answers that cite a document ID (e.g. `[SOP-PMP-001]`) that wasn't returned by `search_documents` during the run, and answers that claim the agent approved, deleted or changed something. It doesn't verify every factual statement.
- Retrieved text is treated as data. The system prompt tells the model to ignore instructions inside documents or tool output.
- Live requests are serialised and capped by an estimated spend limit, an hourly request limit and a shared password. These protect API credit; they aren't user authentication.

## Out of scope

No connection to control systems, no alarm handling, no corrosion-rate or remaining-life calculations, no acceptance criteria, no multi-user roles or audit trail. Reports have no effect outside the app.

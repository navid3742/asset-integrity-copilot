# System architecture — Asset Integrity Copilot v4

## Design goal
An independent demonstration of a domain-specific knowledge + structured-record assistant for oil-and-gas reliability engineers. No real industrial control integrations.

```text
+------------------- React + TypeScript --------------------+
| Overview | Chat | SOPs | Assets | Integrity Reports | Log |
+---------------------------+-------------------------------+
                            | same-origin /api HTTP
+---------------------------v-------------------------------+
| FastAPI main.py: request schemas, demo auth, rate limit    |
+---------------------------+-------------------------------+
                            |
                  +---------v---------+
                  | agent.py           |
                  | safety rules,      |
                  | offline fallback   |
                  +---------+---------+
                            |
             +--------------v---------------+
             | sdk_runtime.py (live only)    |
             | OpenAI Agents SDK Agent/Runner|
             | SDK output guardrail         |
             +-----------+------------------+
                         |
          +--------------+-------------------+
          |              |                   |
  search_documents   get_asset     get_asset_history
          |              |                   |
    retrieval.py      db.py              db.py
   BM25 + optional   assets       inspections, maintenance,
   embedding index                   incidents
          |
   documents.json
          |
  citations + tool traces -> response to frontend

Separate user action: UI -> /reports/draft -> pending SQLite report
                    UI -> /reports/{id}/approve -> confirmation -> approved
                    NO agent tool for these writes
```

## Why the two data stores?

**Unstructured** procedures and incident case write-ups are searched by section using BM25; embeddings are optional in live mode. This is a small local collection, not a deployed vector database.

**Structured** asset tags, inspection observations, maintenance work orders and incidents are linked by SQLite foreign keys. The model cannot write SQL; its read-only tools accept validated asset tags.

## Asset entities

- `assets`: `id`, `name`, `category`, `service`, `unit`, `location`, `status`, `criticality`, `installed_at`, `design_reference`, `description`
- `inspections`: `id`, `asset_id`, `inspected_at`, `inspection_type`, `metric`, `reading`, `unit`, `outcome`, `inspector`, `notes`
- `maintenance`: `id`, `asset_id`, `performed_at`, `work_type`, `status`, `description`, `action_taken`, `next_step`
- `incidents`: `id`, `asset_id`, `severity`, `status`, `issue`, `recorded_at`, `follow_up`
- `reports`: `id`, `asset_id`, `status` (`pending`/`approved`), `summary`, `created_at`, `approved_at`

The equipment cases `P-204`, `CV-310` and `PV-120` have matching incidents and knowledge documents. Asset history tool returns all three related record types.

## Guardrails and limits

- The SDK agent has three registered read-only function tools.
- Python dispatcher refuses unknown tools or malformed asset tags.
- System instructions require source-backed answers and reject document/tool-text commands.
- The SDK output guardrail checks some unsupported *document* citations and certain false write-action claims; it does not check every factual statement.
- Model turn limit and serialized paid requests bound the small demonstration.
- A shared demo password, hourly per-client rate limiting and in-memory estimated usage threshold help limit costs; they are not production identity controls or provider billing enforcement.
- Human-confirmed report approval is a separate API action; reports are synthetic and have no effect on plant operations.

## What the system doesn't do

No live control system connectivity, maintenance scheduling, alarms, vibration diagnostics, anomaly prediction, corrosion rate calculations, remaining life prediction, engineering acceptance criteria, RBI models, actual permit-to-work authorization, multiuser RBAC, persistent audit ledger or guaranteed factual grounding.

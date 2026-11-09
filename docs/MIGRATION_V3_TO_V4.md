# Migration summary: Factory Copilot v3 → Asset Integrity Copilot v4

- Reused the **same architectural pattern**: React + TypeScript / FastAPI / SDK Agent+Runner / three read-only tools / BM25+optional embeddings / SQLite / explicit demo report approval / Docker / Render.
- Replaced aerospace component tags `AM-####` with oil-and-gas equipment tags `P-###`, `CV-###`, `PV-###` and renamed the interface to an independent identity.
- Refactored SQLite `components` into `assets`; inspections now hold equipment-specific reading names and units. Added relational `maintenance` work orders; incidents and reports reference `asset_id`.
- Generated **60 fictional assets, 180 inspections, 120 work orders, 12 incidents, 15 new SOP/case/guidance documents**.
- Changed SDK tools from `get_component` and `get_quality_history` to `get_asset` and `get_asset_history` (includes inspection + maintenance + incident records). `search_documents` remains.
- Updated agent prompt to prohibit fabricating vibration thresholds, pressure limits, minimum vessel wall thickness, equipment safety decisions or equipment controls.
- Updated pages, API contracts, report summaries, local verification instructions and synthetic evaluation set.
- New database filename: `backend/data/asset_integrity.sqlite3`. This avoids mixing v3 schema with v4 tables.
- **No longer uses the previous aerospace-focused interview dataset or metrics**. All numerical v4 evaluation scores are newly measured and labeled as synthetic retrieval-only results.

## Important limitation

This is a data-domain migration, not a qualified oil-and-gas inspection software system. Synthetic SOPs are not real operator instructions; actual asset integrity disposition needs approved site engineering data and competent personnel.

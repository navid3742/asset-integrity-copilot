# Interview walkthrough — Oil & Gas Asset Integrity Copilot

## 60-second framing

> I created a domain-specific equipment reliability assistant for a fictional oil-and-gas processing facility. Instead of focusing on aerospace, I used pumps, control valves and pressure vessels so I could reason about inspections and maintenance history in a domain familiar to me. The app combines a React interface, a FastAPI backend, an OpenAI Agents SDK agent with three read-only tools, BM25 and optional embedding retrieval across synthetic SOPs, and linked SQLite inspection, work-order and incident records. It can investigate an asset and produce a sourced summary. Separate human-initiated endpoints create and approve *fictional* reports, and the AI itself cannot authorize plant operations. I tested the offline API and keyword retrieval and documented what's still unverified in live deployment.

## Suggested 8-minute demonstration

1. **Context (1 min):** Equipment integrity recordkeeping across three equipment classes. All data is fictional.
2. **Pump (2 min):** Ask “Investigate pump P-204. Show inspection history, seal incident, open work orders and relevant SOPs.” Open the cited `[CASE-INC-007]` and `[SOP-PMP-001]` references.
3. **Valve (1 min):** Ask about `CV-310`: actuator/positioner issues and `INC-010`.
4. **Vessel (1 min):** Ask about `PV-120`: UT readings with **mm units**, corrosion observation and why safe thickness **cannot** be inferred.
5. **Records (1 min):** Open asset details to show inspections, 2 work orders and an incident attached to the same tag.
6. **Guardrails (1 min):** Explain three read-only tools, invalid tag rejection and prompt-injection data boundaries. Draft a report from the asset page and emphasize it is **not** an engineering disposition; approve only via a separate user action.
7. **Evidence + limitations (1 min):** Cite the 24 offline tests and retrieval evaluation; clearly state that actual paid model/Render testing still needs verification on your environment.

## Questions to anticipate

- **Why Oil & Gas if the employer manufactures aerospace parts?** Domain knowledge lets me demonstrate meaningful industrial data integration and data-quality boundaries; the agent/tool architecture can be adapted to different industrial domains.
- **Why BM25 and embeddings?** BM25 catches exact tag IDs and terms; optional semantic similarity covers paraphrases. The 65/35 blend is a demo heuristic, not tuned.
- **Why SQLite?** A single-file relational database with foreign keys suits a 60-asset MVP. Move to a managed DB for production concurrency and persistence.
- **Why Agents SDK?** It manages tool selection/execution loops, turn limits, optional tracing and output guardrail integration.
- **Does AI approve maintenance?** No. Tools are read-only; the only report write action is in a separate API endpoint requiring explicit confirmation, with no operational effect.
- **What is the most important limitation?** Synthetic training sources do not supply safe operating limits or validated site SOPs. The system cannot certify asset safety or fitness for service.

Be transparent about AI assistance and what you've personally verified or modified. The best technical defense is the ability to inspect and change the code yourself.

# Retrieval and backend evaluation — v4

## What was measured

- **BM25 keyword search over 15 fictional SOP/case-study/guidance documents**, divided into headed chunks.
- 36 manually labeled, transparent synthetic questions with one or more acceptable target documents.
- 5 unrelated questions to check basic out-of-scope rejection.
- 24 offline automated backend tests, including fake SDK Runner integration and SQLite referential integrity.

Run:

```bash
PYTHONPATH=backend python -m pytest -q backend/tests
PYTHONPATH=backend python backend/scripts/evaluate_retrieval.py
```

## Observed results (measured during package preparation)

| Metric | Result |
|---|---:|
| Offline backend tests | 24 / 24 passed |
| BM25 Hit@1 | 91.7% |
| BM25 Hit@3 | 100.0% |
| BM25 MRR@3 | 0.958 |
| Unrelated questions with no retrieved source | 5 / 5 |

See `RETRIEVAL_RESULTS.json` for every labeled query, expected ID, returned IDs and rank. The question set was constructed with knowledge of the synthetic documents. These scores are not independent external validation.

## Not evaluated yet

- Live OpenAI Agents SDK calls with the actual model and user API key.
- Retrieval using the OpenAI embedding option (`ENABLE_EMBEDDINGS=true`).
- Accuracy, hallucinations and tool-choice quality across real equipment logs.
- Production safety, remaining life, operating thresholds or engineering compliance.
- Actual Render deployment and browser interaction.

## Next useful evaluation steps

1. Run the full React build on your Mac and record the output.
2. Run 6–10 live questions across pump, valve, vessel and unrelated topics and inspect sources and traces.
3. Create new paraphrased questions written without looking at the document titles.
4. Compare BM25-only and hybrid retrieval Hit@k using the same question set.
5. Test deliberate prompt injection placed in a throwaway synthetic document and verify tool restrictions and citations.
6. Record actual API token usage and compare the estimate to the provider usage dashboard.

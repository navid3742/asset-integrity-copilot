# Evaluation

## Retrieval

`backend/scripts/evaluate_retrieval.py` runs the keyword retriever (no embeddings, no API calls) against 36 hand-labelled questions and 10 off-topic ones. Each in-scope question lists one or more acceptable source documents. Results are written to `RETRIEVAL_RESULTS.json`.

```bash
PYTHONPATH=backend python backend/scripts/evaluate_retrieval.py
```

| Metric | Result |
|---|---:|
| Hit@1 | 91.7% (33/36) |
| Hit@3 | 100% (36/36) |
| MRR@3 | 0.958 |
| Off-topic questions with no results | 10/10 |

The questions were written by someone who had read the documents, and several documents mention the demo tags directly, so these numbers are a regression check rather than a measure of real-world retrieval quality.

### The relevance bug

The first version of the retriever divided every BM25 score by the best score and kept anything above 0.16. That meant the top result was always 1.0 as soon as one word matched. "What is the best pizza in town for a pump party" returned the pump SOP as a perfect match, and "tell me a joke" returned the security guide. The original five off-topic questions didn't catch this because none of them shared a word with the corpus.

The fix is a query-level check (`retrieval.query_coverage`). It computes what share of the query's IDF weight comes from words that appear anywhere in the corpus. Below 0.5, keyword evidence is ignored. Five near-miss questions were added to the eval and a regression test was added to `test_app.py`.

| | Before | After |
|---|---:|---:|
| Off-topic questions rejected | 5/10 | 10/10 |
| Hit@1 | 91.7% | 91.7% |

The threshold was picked by looking at this question set. Two in-scope questions sit close to it (coverage 0.51) because they contain a word that isn't in the corpus ("leaks", "call"). Simple stemming would help with those.

In live mode, embedding similarity can still bring back a result for a low-coverage question if the cosine similarity is high enough. That path isn't covered by the offline eval.

## Backend tests

```bash
python -m pytest -q
```

25 tests, all offline. They cover the API, dataset integrity (foreign keys, counts), the tool allowlist and tag validation, the report approval flow, the output guardrail, and the SDK integration with a mocked `Runner`.

## Not measured yet

- How often the live agent calls the right tools for a question.
- Whether cited IDs are valid across a fixed question set (the guardrail already computes this per run).
- Whether the agent declines questions that ask for a safety decision, e.g. "Is PV-120 safe to restart?"
- Keyword vs. hybrid retrieval on the same question set.

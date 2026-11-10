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

28 tests, all offline. They cover the API, dataset integrity (foreign keys, counts), the tool allowlist and tag validation, the report approval flow, the output guardrail (including text from a real live answer), and the SDK integration with a mocked `Runner`.

## Live checks

Three questions run by hand against the deployed agent (`gpt-4.1-mini`, hybrid retrieval).

| Question | First version | After changes |
|---|---|---|
| "what is the best pizza in town for a pump party" | Retrieval correctly returned nothing, but the model then suggested pizza styles from general knowledge | Declines in two sentences and suggests an in-scope question |
| "Is PV-120 safe to restart?" | Declined to clear the vessel, but only called `get_asset` and `get_asset_history`, so no SOP was consulted and no record IDs were given | Calls all three tools, cites INSP-, INC- and WO- IDs plus SOP-PV-005, SOP-PV-006 and CASE-INC-012, and still declines |
| "Investigate P-204" | Not run | Calls all three tools; readings and IDs match the database |

What these turned up:

- **Prompt scope.** The only rule about unrelated questions was "Do not answer unrelated questions with fabricated industry citations". The model read that as "don't fake citations", not "don't answer". It's now an explicit scope rule, and asset questions must use all three tools and name record IDs.
- **The guardrail wasn't checking anything.** The model wrote citations as `(SOP-PMP-001)` or `[SOP-PV-005, SOP-PV-006, CASE-INC-012]`, but the guardrail only matched a single ID inside square brackets, so none of these citations were checked. It now finds document IDs anywhere in the answer and also checks INC/WO/INSP record IDs against the tool outputs from the same run. The tests use text from the real PV-120 answer.
- **A summary can be accurate and still miss something.** The PV-120 answer described a downward trend from 13.91 mm to 12.19 mm and skipped the middle reading of 11.39 mm. A later UT reading higher than an earlier one usually points to a measurement location or calibration problem, which an integrity engineer would want flagged. No ID check can catch that kind of omission.

## Not measured yet

- How often the live agent calls the right tools for a question.
- Whether cited IDs are valid across a fixed question set (the guardrail already computes this per run).
- Whether the agent declines questions that ask for a safety decision, e.g. "Is PV-120 safe to restart?"
- Keyword vs. hybrid retrieval on the same question set.

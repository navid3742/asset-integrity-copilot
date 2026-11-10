"""Section-level BM25 search over the knowledge base, optionally blended with
OpenAI embedding similarity when live mode is on.

Each result carries a stable chunk ID (``DOC-ID:section``) so the agent's
citations can be checked against what was actually retrieved.
"""

import hashlib
import json
import math
import re
import threading
from collections import Counter

from .config import API_KEY, DATA_DIR, EMBEDDING_MODEL, ENABLE_EMBEDDINGS, LIVE_ENABLED

_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
_STOPWORDS = set(
    "a an and are as at be been by can could do does for from had has have how i if in into is it its may me my of on or our please should so some than that the their them there these this those to was we were what when where which who why will with would you your".split()
)
_LOCK = threading.RLock()

# BM25 parameters (k1, b) and the hybrid weighting. The 0.65/0.35 split was picked
# by hand on the sample questions, not tuned.
_K1, _B = 1.2, 0.75
_LEXICAL_WEIGHT, _SEMANTIC_WEIGHT = 0.65, 0.35
_MIN_SIMILARITY = 0.35

# A query only counts as lexically relevant if at least this share of its IDF weight
# comes from terms that exist somewhere in the corpus. Without this, a single domain
# word ("pump") made an unrelated question look like a perfect match, because scores
# are normalised against the best hit. See docs/EVALUATION.md.
MIN_QUERY_COVERAGE = 0.5


def tokens(s):
    return [m.group().lower() for m in _TOKEN_RE.finditer(s)]


def load_chunks():
    docs = json.loads((DATA_DIR / "documents.json").read_text())
    chunks = []
    for doc in docs:
        content = doc["content"]
        sections = re.split(r"(?=^##\s+)", content, flags=re.MULTILINE)
        for idx, section in enumerate(sections):
            if not section.strip():
                continue
            lines = section.strip().splitlines()
            heading = (
                lines[0].removeprefix("##").strip() if lines[0].startswith("##") else "Overview"
            )
            chunks.append(
                {
                    "id": f"{doc['id']}:{idx}",
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "section": heading,
                    "category": doc["category"],
                    "content": section.strip(),
                }
            )
    return chunks


CHUNKS = load_chunks()
_DOC_COUNTS = [
    Counter(tokens(c["title"] + " " + c["title"] + " " + c["section"] + " " + c["content"]))
    for c in CHUNKS
]
_AVG_LENGTH = sum(map(lambda c: sum(c.values()), _DOC_COUNTS)) / max(len(_DOC_COUNTS), 1)
_DOC_FREQ = Counter(term for dc in _DOC_COUNTS for term in dc)


def _query_terms(query):
    return set(tokens(query)) - _STOPWORDS


def _idf(term):
    n = len(_DOC_COUNTS)
    df = _DOC_FREQ[term]
    return math.log(1 + (n - df + 0.5) / (df + 0.5))


def query_coverage(query):
    """Share of the query's IDF weight that comes from terms present in the corpus.

    Unknown words get the maximum IDF, so "best pizza for a pump party" scores
    low even though "pump" matches, while "pump seal leak history" scores 1.0.
    """
    terms = _query_terms(query)
    if not terms:
        return 0.0
    weights = {t: _idf(t) for t in terms}
    known = sum(w for t, w in weights.items() if _DOC_FREQ[t])
    return known / sum(weights.values())


def bm25_scores(query):
    query_terms = _query_terms(query)
    results = []
    for terms in _DOC_COUNTS:
        score = 0.0
        length = sum(terms.values())
        for t in query_terms:
            f = terms[t]
            if not f:
                continue
            norm = _K1 * (1 - _B + _B * length / _AVG_LENGTH)
            score += _idf(t) * f * (_K1 + 1) / (f + norm)
        results.append(score)
    return results


def _vectors_path():
    return DATA_DIR / "vector_cache.json"


def _get_vectors(client):
    digest = hashlib.sha256("".join(x["content"] for x in CHUNKS).encode()).hexdigest()
    path = _vectors_path()
    with _LOCK:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if data.get("hash") == digest and data.get("model") == EMBEDDING_MODEL:
                    return data["vectors"]
            except (ValueError, KeyError):
                pass
        response = client.embeddings.create(
            model=EMBEDDING_MODEL, input=[x["content"][:7000] for x in CHUNKS]
        )
        vectors = [r.embedding for r in sorted(response.data, key=lambda d: d.index)]
        path.write_text(json.dumps({"hash": digest, "model": EMBEDDING_MODEL, "vectors": vectors}))
        return vectors


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / mag if mag else 0


def search(query, top_k=4, semantic=True):
    """Return up to ``top_k`` chunks, at most one per source document.

    Keyword-only by default. In live mode with embeddings enabled, BM25 and cosine
    similarity are blended; if the embedding call fails we fall back to keywords
    and label the results ``keyword`` rather than ``hybrid``.
    """
    query = query[:500]
    if not tokens(query):
        return []
    k = min(max(top_k, 1), 6)
    if query_coverage(query) >= MIN_QUERY_COVERAGE:
        lexical = bm25_scores(query)
    else:
        # Mostly out-of-vocabulary question: ignore keyword evidence and let
        # embeddings (if enabled) decide whether anything is relevant.
        lexical = [0.0] * len(CHUNKS)
    max_b = max(lexical) if lexical else 0
    normalized = [s / max_b if max_b else 0 for s in lexical]
    similarity = [0.0] * len(CHUNKS)
    used_semantic = False
    if semantic and LIVE_ENABLED and ENABLE_EMBEDDINGS:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=API_KEY, timeout=18, max_retries=1)
            vectors = _get_vectors(client)
            q = client.embeddings.create(model=EMBEDDING_MODEL, input=query).data[0].embedding
            similarity = [_cos(q, v) for v in vectors]
            used_semantic = True
        except Exception:
            # Keep the app usable if the embeddings API is down; results are
            # reported as "keyword" so the UI doesn't claim hybrid search.
            used_semantic = False
    scored = []
    for idx, c in enumerate(CHUNKS):
        if used_semantic:
            combined = _LEXICAL_WEIGHT * normalized[idx] + _SEMANTIC_WEIGHT * max(
                0.0, similarity[idx]
            )
            threshold = 0.15
        else:
            combined = normalized[idx]
            threshold = 0.16
        if combined >= threshold and (lexical[idx] > 0 or similarity[idx] > _MIN_SIMILARITY):
            scored.append((combined, c))
    scored.sort(key=lambda p: p[0], reverse=True)
    # Prefer distinct source documents so repeated chunks do not crowd out other evidence.
    unique = []
    seen = set()
    for score, chunk in scored:
        if chunk["doc_id"] in seen:
            continue
        unique.append((score, chunk))
        seen.add(chunk["doc_id"])
        if len(unique) >= k:
            break
    return [
        {
            "id": c["id"],
            "doc_id": c["doc_id"],
            "title": c["title"],
            "section": c["section"],
            "category": c["category"],
            "excerpt": c["content"][:950],
            "score": round(s, 3),
            "method": "hybrid" if used_semantic else "keyword",
        }
        for s, c in unique
    ]


def documents():
    return [
        {k: d[k] for k in ("id", "title", "category", "description")}
        for d in json.loads((DATA_DIR / "documents.json").read_text())
    ]


def get_document(doc_id):
    return next(
        (d for d in json.loads((DATA_DIR / "documents.json").read_text()) if d["id"] == doc_id),
        None,
    )

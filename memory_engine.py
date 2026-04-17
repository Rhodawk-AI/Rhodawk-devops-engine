"""
Rhodawk AI — Fix Memory Engine (Data Flywheel)
===============================================
Retrieves semantically similar past successful fixes and injects them as
few-shot examples into the prompt for new failures.

This is the compounding advantage: the more repos Rhodawk heals, the better
it gets at healing new repos. After 500 examples, fix accuracy on similar
failures improves measurably. After 5,000 — you fine-tune the model on it.

Implementation: TF-IDF based similarity on failure signatures.
No external embedding API required. Runs entirely on-device.
Designed to be swapped out for a vector database (Pinecone/Qdrant) at scale.
"""

import hashlib
import re
import sqlite3
from collections import Counter
from typing import Optional

from training_store import DB_PATH


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    stopwords = {"the", "a", "an", "is", "in", "at", "of", "and", "or", "for", "with",
                 "line", "file", "test", "error", "assert", "none", "true", "false",
                 "self", "return", "import", "from", "def", "class"}
    return [t for t in tokens if len(t) > 2 and t not in stopwords]


def _tf_idf_similarity(query_tokens: list[str], doc_tokens: list[str], corpus_df: dict, corpus_size: int) -> float:
    import math

    def tf(tokens: list[str], term: str) -> float:
        count = tokens.count(term)
        return count / len(tokens) if tokens else 0

    def idf(term: str) -> float:
        df = corpus_df.get(term, 0)
        return math.log((corpus_size + 1) / (df + 1)) + 1

    query_set = set(query_tokens)
    doc_set = set(doc_tokens)
    all_terms = query_set | doc_set

    query_vec = {t: tf(query_tokens, t) * idf(t) for t in all_terms}
    doc_vec = {t: tf(doc_tokens, t) * idf(t) for t in all_terms}

    dot = sum(query_vec.get(t, 0) * doc_vec.get(t, 0) for t in all_terms)
    q_norm = sum(v**2 for v in query_vec.values()) ** 0.5
    d_norm = sum(v**2 for v in doc_vec.values()) ** 0.5

    if q_norm == 0 or d_norm == 0:
        return 0.0
    return dot / (q_norm * d_norm)


def retrieve_similar_fixes(failure_output: str, top_k: int = 3, min_similarity: float = 0.15) -> list[dict]:
    """
    Retrieve the most similar successful past fixes for a given failure output.
    Returns list of dicts with keys: failure_signature, fix_diff, success_rate, similarity
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row

        # Get all successful patterns
        rows = conn.execute("""
            SELECT fp.failure_signature, fp.fix_diff, fp.success_count, fp.attempt_count,
                   fa.failure_output as sample_failure
            FROM fix_patterns fp
            LEFT JOIN fix_attempts fa ON fa.failure_signature = fp.failure_signature
                AND fa.success_signal = 1
            WHERE fp.success_count > 0
            ORDER BY fp.success_count DESC
            LIMIT 200
        """).fetchall()

        conn.close()

        if not rows:
            return []

        query_tokens = _tokenize(failure_output)

        # Build corpus document frequency
        corpus_docs = [_tokenize(r["sample_failure"] or r["failure_signature"]) for r in rows]
        corpus_df: dict[str, int] = Counter()
        for doc in corpus_docs:
            for term in set(doc):
                corpus_df[term] += 1

        results = []
        for i, row in enumerate(rows):
            doc_tokens = corpus_docs[i]
            sim = _tf_idf_similarity(query_tokens, doc_tokens, corpus_df, len(rows))

            if sim >= min_similarity:
                total = row["attempt_count"] or 1
                success_rate = f"{(row['success_count'] / total * 100):.0f}%"
                results.append({
                    "failure_signature": row["failure_signature"],
                    "fix_diff": row["fix_diff"],
                    "success_rate": success_rate,
                    "similarity": round(sim, 3),
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    except Exception:
        return []


def record_fix_outcome(failure_output: str, context: str, fix_diff: str, success: bool):
    """Called after each fix attempt to update the memory store."""
    from training_store import record_pattern
    context_hash = hashlib.sha256(context.encode()).hexdigest()[:16]
    record_pattern(failure_output, context_hash, fix_diff, success)


def get_memory_stats() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        total = conn.execute("SELECT COUNT(*) FROM fix_patterns").fetchone()[0]
        successful = conn.execute("SELECT COUNT(*) FROM fix_patterns WHERE success_count > 0").fetchone()[0]
        conn.close()
        return {"patterns_stored": total, "successful_patterns": successful}
    except Exception:
        return {"patterns_stored": 0, "successful_patterns": 0}

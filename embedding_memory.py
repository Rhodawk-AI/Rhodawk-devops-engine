"""
Rhodawk AI — Embedding-Based Memory Engine v2
==============================================
Cross-repository semantic retrieval using sentence-transformers embeddings.
"""

import os
import re
import sqlite3
from typing import Optional

import numpy as np

from training_store import DB_PATH

EMBEDDING_DB_PATH = os.getenv("RHODAWK_EMBEDDING_DB", "/data/embedding_memory.db")
MODEL_NAME = os.getenv("RHODAWK_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def _normalize_failure(failure_output: str) -> str:
    text = re.sub(r'File "[^"]+", line \d+', "File <path>, line <n>", failure_output)
    text = re.sub(r"/[\w./-]+", "<path>", text)
    text = re.sub(r"\b\d+\b", "<num>", text)
    return text[:4000]


def embed_failure(failure_output: str) -> np.ndarray:
    normalized = _normalize_failure(failure_output)
    return _get_model().encode(normalized, normalize_embeddings=True)


def _ensure_schema() -> None:
    os.makedirs(os.path.dirname(EMBEDDING_DB_PATH), exist_ok=True)
    with sqlite3.connect(EMBEDDING_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fix_embeddings (
                failure_signature TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                fix_diff TEXT NOT NULL,
                success_rate TEXT NOT NULL,
                sample_failure TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def rebuild_embedding_index(limit: int = 1000) -> int:
    _ensure_schema()
    with sqlite3.connect(DB_PATH) as source:
        source.row_factory = sqlite3.Row
        rows = source.execute("""
            SELECT fp.failure_signature, fp.fix_diff, fp.success_count, fp.attempt_count,
                   fa.failure_output as sample_failure
            FROM fix_patterns fp
            LEFT JOIN fix_attempts fa ON fa.failure_signature = fp.failure_signature
                AND fa.success_signal = 1
            WHERE fp.success_count > 0
            ORDER BY fp.success_count DESC
            LIMIT ?
        """, (limit,)).fetchall()

    with sqlite3.connect(EMBEDDING_DB_PATH) as target:
        for row in rows:
            sample = row["sample_failure"] or row["failure_signature"]
            emb = embed_failure(sample).astype(np.float32).tobytes()
            attempts = row["attempt_count"] or 1
            success_rate = f"{(row['success_count'] / attempts * 100):.0f}%"
            target.execute("""
                INSERT INTO fix_embeddings (failure_signature, embedding, fix_diff, success_rate, sample_failure)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(failure_signature) DO UPDATE SET
                    embedding=excluded.embedding,
                    fix_diff=excluded.fix_diff,
                    success_rate=excluded.success_rate,
                    sample_failure=excluded.sample_failure,
                    updated_at=CURRENT_TIMESTAMP
            """, (row["failure_signature"], emb, row["fix_diff"], success_rate, sample))
    return len(rows)


def retrieve_similar_fixes_v2(
    failure_output: str,
    top_k: int = 5,
    min_similarity: float = 0.55,
) -> list[dict]:
    """
    BUG-004 FIX:
      1. min_similarity lowered from 0.75 → 0.55 so sparse/cold-start DBs
         can still return useful candidates.
      2. Auto-rebuild embedding index from training_store on cold start
         (empty index) so v2 memory is never dead on first run.
      3. Falls back gracefully to empty list (callers handle this).
    """
    _ensure_schema()

    # Auto-rebuild if the index is empty (cold start)
    with sqlite3.connect(EMBEDDING_DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM fix_embeddings").fetchone()[0]

    if count == 0:
        try:
            rebuilt = rebuild_embedding_index()
            if rebuilt == 0:
                return []
        except Exception:
            return []

    query_vec = embed_failure(failure_output).astype(np.float32)
    with sqlite3.connect(EMBEDDING_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT failure_signature, embedding, fix_diff, success_rate FROM fix_embeddings").fetchall()

    results = []
    for row in rows:
        vec = np.frombuffer(row["embedding"], dtype=np.float32)
        if vec.size != query_vec.size:
            continue
        sim = float(np.dot(query_vec, vec))
        if sim >= min_similarity:
            results.append({
                "failure_signature": row["failure_signature"],
                "fix_diff": row["fix_diff"],
                "success_rate": row["success_rate"],
                "similarity": round(sim, 3),
            })
    results.sort(key=lambda item: item["similarity"], reverse=True)
    return results[:top_k]
"""
Rhodawk AI — Embedding-Based Memory Engine v3
==============================================
Dual-backend semantic retrieval:
  - Default (v2 SQLite): sentence-transformers all-MiniLM-L6-v2 + cosine similarity
  - Enhanced (v3 Qdrant+CodeBERT): microsoft/codebert-base embeddings stored in
    an in-process Qdrant vector database for ANN retrieval with HNSW indexing

CodeBERT understands programming language syntax at the token level, giving
significantly better semantic similarity for code-related failure traces than
generic sentence-transformer models.

Backend selection:
  RHODAWK_EMBEDDING_BACKEND=sqlite   # default — no extra deps, works everywhere
  RHODAWK_EMBEDDING_BACKEND=qdrant   # requires: qdrant-client, transformers, torch

The public API (retrieve_similar_fixes_v2, rebuild_embedding_index,
record_fix_outcome) is unchanged — all callers continue to work.
"""

import hashlib
import os
import re
import sqlite3
import threading
from typing import Optional

import numpy as np

from training_store import DB_PATH

EMBEDDING_DB_PATH  = os.getenv("RHODAWK_EMBEDDING_DB", "/data/embedding_memory.db")
MODEL_NAME         = os.getenv("RHODAWK_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CODEBERT_MODEL     = os.getenv("RHODAWK_CODEBERT_MODEL", "microsoft/codebert-base")
BACKEND            = os.getenv("RHODAWK_EMBEDDING_BACKEND", "sqlite").lower()
QDRANT_COLLECTION  = "rhodawk_fixes"
QDRANT_DIM         = 768  # codebert-base hidden size

_model_lock        = threading.Lock()
_MINILM_MODEL      = None
_CODEBERT_TOKENIZER = None
_CODEBERT_MODEL    = None
_QDRANT_CLIENT     = None
_qdrant_lock       = threading.Lock()


# ──────────────────────────────────────────────────────────────
# MiniLM backend (v2, default)
# ──────────────────────────────────────────────────────────────

def _get_minilm():
    global _MINILM_MODEL
    with _model_lock:
        if _MINILM_MODEL is None:
            from sentence_transformers import SentenceTransformer
            _MINILM_MODEL = SentenceTransformer(MODEL_NAME)
    return _MINILM_MODEL


# ──────────────────────────────────────────────────────────────
# CodeBERT backend (v3, optional)
# ──────────────────────────────────────────────────────────────

def _get_codebert():
    global _CODEBERT_TOKENIZER, _CODEBERT_MODEL
    with _model_lock:
        if _CODEBERT_MODEL is None:
            from transformers import AutoTokenizer, AutoModel
            _CODEBERT_TOKENIZER = AutoTokenizer.from_pretrained(CODEBERT_MODEL)
            _CODEBERT_MODEL = AutoModel.from_pretrained(CODEBERT_MODEL)
            _CODEBERT_MODEL.eval()
    return _CODEBERT_TOKENIZER, _CODEBERT_MODEL


def _embed_codebert(text: str) -> np.ndarray:
    import torch
    tokenizer, model = _get_codebert()
    inputs = tokenizer(
        text[:512],
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=512,
    )
    with torch.no_grad():
        outputs = model(**inputs)
    # Mean-pool over token dimension
    vec = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    norm = np.linalg.norm(vec)
    return (vec / norm) if norm > 0 else vec


def _get_qdrant():
    global _QDRANT_CLIENT
    with _qdrant_lock:
        if _QDRANT_CLIENT is None:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            client = QdrantClient(path="/data/qdrant_store")
            existing = [c.name for c in client.get_collections().collections]
            if QDRANT_COLLECTION not in existing:
                client.create_collection(
                    collection_name=QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=QDRANT_DIM, distance=Distance.COSINE),
                )
            _QDRANT_CLIENT = client
    return _QDRANT_CLIENT


# ──────────────────────────────────────────────────────────────
# Shared utilities
# ──────────────────────────────────────────────────────────────

def _normalize_failure(failure_output: str) -> str:
    text = re.sub(r'File "[^"]+", line \d+', "File <path>, line <n>", failure_output)
    text = re.sub(r"/[\w./-]+", "<path>", text)
    text = re.sub(r"\b\d+\b", "<num>", text)
    return text[:4000]


def embed_failure(failure_output: str) -> np.ndarray:
    """Embed a failure string using the configured backend model."""
    normalized = _normalize_failure(failure_output)
    if BACKEND == "qdrant":
        try:
            return _embed_codebert(normalized)
        except Exception:
            pass
    return _get_minilm().encode(normalized, normalize_embeddings=True)


def pre_warm_model() -> bool:
    """Pre-warm the embedding model at startup. Returns True on success."""
    try:
        embed_failure("test warmup")
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
# SQLite backend (v2)
# ──────────────────────────────────────────────────────────────

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


def _rebuild_sqlite(limit: int) -> int:
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
                INSERT INTO fix_embeddings
                    (failure_signature, embedding, fix_diff, success_rate, sample_failure)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(failure_signature) DO UPDATE SET
                    embedding=excluded.embedding,
                    fix_diff=excluded.fix_diff,
                    success_rate=excluded.success_rate,
                    sample_failure=excluded.sample_failure,
                    updated_at=CURRENT_TIMESTAMP
            """, (row["failure_signature"], emb, row["fix_diff"], success_rate, sample))
    return len(rows)


def _retrieve_sqlite(failure_output: str, top_k: int, min_similarity: float) -> list[dict]:
    _ensure_schema()

    with sqlite3.connect(EMBEDDING_DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM fix_embeddings").fetchone()[0]

    if count == 0:
        try:
            rebuilt = _rebuild_sqlite(1000)
            if rebuilt == 0:
                return []
        except Exception:
            return []

    query_vec = embed_failure(failure_output).astype(np.float32)
    with sqlite3.connect(EMBEDDING_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT failure_signature, embedding, fix_diff, success_rate FROM fix_embeddings"
        ).fetchall()

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


# ──────────────────────────────────────────────────────────────
# Qdrant backend (v3)
# ──────────────────────────────────────────────────────────────

def _point_id(failure_signature: str) -> int:
    """Stable integer ID from signature hash — Qdrant requires int or UUID."""
    h = hashlib.md5(failure_signature.encode()).hexdigest()
    return int(h[:16], 16) % (2**63)


def _rebuild_qdrant(limit: int) -> int:
    client = _get_qdrant()
    from qdrant_client.models import PointStruct

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

    points = []
    for row in rows:
        sample = row["sample_failure"] or row["failure_signature"]
        try:
            vec = _embed_codebert(sample).tolist()
        except Exception:
            continue
        attempts = row["attempt_count"] or 1
        success_rate = f"{(row['success_count'] / attempts * 100):.0f}%"
        points.append(PointStruct(
            id=_point_id(row["failure_signature"]),
            vector=vec,
            payload={
                "failure_signature": row["failure_signature"],
                "fix_diff": row["fix_diff"],
                "success_rate": success_rate,
            }
        ))
        if len(points) >= 64:
            client.upsert(collection_name=QDRANT_COLLECTION, points=points)
            points = []

    if points:
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)

    return len(rows)


def _retrieve_qdrant(failure_output: str, top_k: int, min_similarity: float) -> list[dict]:
    try:
        client = _get_qdrant()
        vec = _embed_codebert(_normalize_failure(failure_output)).tolist()
        hits = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vec,
            limit=top_k,
            score_threshold=min_similarity,
        )
        return [
            {
                "failure_signature": h.payload.get("failure_signature", ""),
                "fix_diff": h.payload.get("fix_diff", ""),
                "success_rate": h.payload.get("success_rate", "?"),
                "similarity": round(h.score, 3),
            }
            for h in hits
        ]
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# Public API (unchanged signature)
# ──────────────────────────────────────────────────────────────

def rebuild_embedding_index(limit: int = 1000) -> int:
    """
    Rebuild the embedding index from training_store.
    Uses Qdrant+CodeBERT if RHODAWK_EMBEDDING_BACKEND=qdrant, otherwise SQLite.
    Returns number of records indexed.
    """
    if BACKEND == "qdrant":
        try:
            return _rebuild_qdrant(limit)
        except Exception:
            pass
    return _rebuild_sqlite(limit)


def retrieve_similar_fixes_v2(
    failure_output: str,
    top_k: int = 5,
    min_similarity: float = 0.55,
) -> list[dict]:
    """
    Retrieve semantically similar past fixes for a given failure output.

    Returns list of dicts with keys:
      failure_signature, fix_diff, success_rate, similarity
    """
    if BACKEND == "qdrant":
        try:
            results = _retrieve_qdrant(failure_output, top_k, min_similarity)
            if results is not None:
                return results
        except Exception:
            pass
    return _retrieve_sqlite(failure_output, top_k, min_similarity)


# ──────────────────────────────────────────────────────────────
# Alias used by app.py / memory_engine.py
# ──────────────────────────────────────────────────────────────
def record_fix_outcome(failure_output: str, test_path: str, diff_text: str, success: bool) -> None:
    """
    Persist a fix outcome to the training store and update the embedding index.
    This is the thin wrapper used by app.py's process_failing_test.
    """
    try:
        from training_store import record_fix_attempt
        record_fix_attempt(failure_output, test_path, diff_text, success)
    except Exception:
        pass

    if success:
        try:
            rebuild_embedding_index(limit=1)
        except Exception:
            pass


def get_memory_stats() -> dict:
    """Return basic stats about the embedding index."""
    try:
        _ensure_schema()
        with sqlite3.connect(EMBEDDING_DB_PATH) as conn:
            total = conn.execute("SELECT COUNT(*) FROM fix_embeddings").fetchone()[0]
        return {"patterns_stored": total, "successful_patterns": total, "backend": BACKEND}
    except Exception:
        return {"patterns_stored": 0, "successful_patterns": 0, "backend": BACKEND}

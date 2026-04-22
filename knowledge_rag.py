"""
knowledge_rag.py — security-knowledge RAG store (Masterplan §1.4).

A small, dependency-light vector store of security writeups, CVE detail
pages, disclosed bug-bounty reports, and research papers.  The store reuses
the embedder from ``embedding_memory.py`` if available, otherwise falls
back to a deterministic hash-bag baseline so unit tests pass with zero
extra dependencies.

The store is a single SQLite file under ``/data/knowledge_rag.sqlite`` so
it survives Space restarts and can be snapshotted to GitHub like the rest
of the Hermes memory.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

LOG = logging.getLogger("knowledge_rag")

DB_PATH = Path(os.getenv("KNOWLEDGE_RAG_DB", "/data/knowledge_rag.sqlite"))
EMBED_DIM = 256


SOURCES_DEFAULT: list[str] = [
    "https://hackerone.com/hacktivity",
    "https://www.cvedetails.com/",
    "https://github.com/ngalongc/bug-bounty-reference",
    "https://github.com/EdOverflow/bugbounty-cheatsheet",
    "https://github.com/nicowillis/awesome-bugbounty-writeups",
    "https://arxiv.org/list/cs.CR/recent",
    "https://googleprojectzero.blogspot.com/",
    "https://portswigger.net/research",
]


@dataclass
class Document:
    doc_id: str
    source: str
    title: str
    text: str
    tags: list[str] = field(default_factory=list)
    score: float = 0.0


# ── Embedding ──────────────────────────────────────────────────────────────
def _hash_embed(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic hash-bag embedder — no external deps, good enough for
    cosine-similarity ranking inside a single corpus."""
    vec = [0.0] * dim
    for tok in text.lower().split():
        h = int(hashlib.blake2s(tok.encode("utf-8"), digest_size=4).hexdigest(), 16)
        vec[h % dim] += 1.0
    n = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


def _embed(text: str) -> list[float]:
    try:
        from embedding_memory import embed as _real_embed  # type: ignore
        v = _real_embed(text)
        if isinstance(v, list) and v:
            return v
    except Exception:  # noqa: BLE001
        pass
    return _hash_embed(text)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))  # both are unit-normalised


# ── Storage ────────────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS docs (
            doc_id   TEXT PRIMARY KEY,
            source   TEXT NOT NULL,
            title    TEXT NOT NULL,
            text     TEXT NOT NULL,
            tags     TEXT NOT NULL,
            embed    TEXT NOT NULL,
            added_at REAL NOT NULL
        )
    """)
    return conn


class KnowledgeRAG:
    """Vector store of security knowledge documents."""

    SOURCES = SOURCES_DEFAULT

    def __init__(self, db_path: Path | None = None):
        global DB_PATH
        if db_path is not None:
            DB_PATH = Path(db_path)

    # ── ingestion ─────────────────────────────────────────────────────────
    def add(self, *, source: str, title: str, text: str,
            tags: Iterable[str] | None = None) -> str:
        doc_id = hashlib.blake2s(
            f"{source}::{title}::{text[:200]}".encode("utf-8"), digest_size=8
        ).hexdigest()
        embed = _embed(f"{title}\n{text}")
        with _connect() as c:
            c.execute(
                "INSERT OR REPLACE INTO docs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (doc_id, source, title, text,
                 json.dumps(list(tags or [])),
                 json.dumps(embed),
                 time.time()),
            )
        return doc_id

    def add_many(self, items: list[dict[str, Any]]) -> int:
        added = 0
        for it in items:
            try:
                self.add(
                    source=str(it["source"]),
                    title=str(it["title"]),
                    text=str(it["text"]),
                    tags=it.get("tags") or [],
                )
                added += 1
            except Exception as exc:  # noqa: BLE001
                LOG.warning("ingest failed: %s", exc)
        return added

    def ingest_text_file(self, path: str | Path, source: str) -> int:
        """Ingest a markdown / text file as one document per top-level heading."""
        p = Path(path)
        if not p.exists():
            return 0
        text = p.read_text(encoding="utf-8", errors="ignore")
        chunks: list[tuple[str, str]] = []
        cur_title = p.stem
        cur_buf: list[str] = []
        for line in text.splitlines():
            if line.startswith("# ") or line.startswith("## "):
                if cur_buf:
                    chunks.append((cur_title, "\n".join(cur_buf).strip()))
                cur_title = line.lstrip("# ").strip() or p.stem
                cur_buf = []
            else:
                cur_buf.append(line)
        if cur_buf:
            chunks.append((cur_title, "\n".join(cur_buf).strip()))
        return self.add_many([
            {"source": source, "title": t, "text": b, "tags": [p.stem]}
            for t, b in chunks if b
        ])

    # ── query ─────────────────────────────────────────────────────────────
    def query(self, query_text: str, *, top_k: int = 5,
              source_prefix: str | None = None) -> list[Document]:
        qv = _embed(query_text)
        with _connect() as c:
            rows = c.execute(
                "SELECT doc_id, source, title, text, tags, embed FROM docs"
            ).fetchall()
        scored: list[Document] = []
        for doc_id, source, title, text, tags_json, embed_json in rows:
            if source_prefix and not source.startswith(source_prefix):
                continue
            try:
                ev = json.loads(embed_json)
                tags = json.loads(tags_json)
            except Exception:
                continue
            score = _cosine(qv, ev)
            scored.append(Document(
                doc_id=doc_id, source=source, title=title,
                text=text, tags=tags, score=score,
            ))
        scored.sort(key=lambda d: d.score, reverse=True)
        return scored[:top_k]

    def stats(self) -> dict[str, Any]:
        with _connect() as c:
            n = c.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            sources = [r[0] for r in c.execute(
                "SELECT DISTINCT source FROM docs ORDER BY source"
            )]
        return {"total_docs": n, "sources": sources, "db": str(DB_PATH)}

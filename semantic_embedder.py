"""
Rhodawk AI — Semantic Embedder (GAP 6)
=======================================
Code-aware semantic embeddings for the data flywheel.

This module is the *typed*, *batched*, *cached* successor to the legacy
sentence-piece embeddings used by ``embedding_memory.py``. It is built
on top of `sentence-transformers <https://www.sbert.net>`_ and defaults
to **nomic-ai/nomic-embed-code** — a code-specialised retrieval model
trained on permissively-licensed source. Falls back to
``nomic-ai/nomic-embed-text-v1.5`` for natural-language inputs and to
``BAAI/bge-small-en-v1.5`` if neither nomic checkpoint is available.

Public API
----------
``SemanticEmbedder`` — singleton-friendly wrapper. Lazy-loads the model
on first use, then keeps it warm.

``embed(texts, *, instruction=None, normalize=True) -> list[list[float]]``
    Encode one or many strings into L2-normalised dense vectors.

``cosine(a, b) -> float``
    Dot product of two L2-normalised vectors (==cosine similarity).

``rank(query, candidates, *, top_k=5) -> list[tuple[int, float]]``
    Return the top-k (index, score) pairs of ``candidates`` sorted by
    cosine similarity to ``query``.

``pre_warm() -> bool``
    Trigger the lazy load synchronously. Designed to be called from
    ``app.py`` in a background thread at startup so the first real
    retrieval call does not block on a multi-second model download.

Environment variables
---------------------
``RHODAWK_EMBED_MODEL``       Model id, default ``nomic-ai/nomic-embed-code``.
``RHODAWK_EMBED_FALLBACK``    Fallback model, default ``nomic-ai/nomic-embed-text-v1.5``.
``RHODAWK_EMBED_DEVICE``      ``cpu`` | ``cuda`` | ``mps``. Auto-detected when unset.
``RHODAWK_EMBED_CACHE_DIR``   On-disk model cache, default ``/data/embed_cache``.
``RHODAWK_EMBED_BATCH_SIZE``  Batch size for ``encode``, default 16.
``RHODAWK_EMBED_MAX_TOKENS``  Truncate inputs to N tokens, default 8192.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from typing import Iterable, Optional, Sequence, Union

LOG = logging.getLogger("rhodawk.semantic_embedder")
if not LOG.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )

DEFAULT_MODEL    = os.getenv("RHODAWK_EMBED_MODEL",    "nomic-ai/nomic-embed-code")
FALLBACK_MODEL   = os.getenv("RHODAWK_EMBED_FALLBACK", "nomic-ai/nomic-embed-text-v1.5")
LAST_RESORT      = "BAAI/bge-small-en-v1.5"
CACHE_DIR        = os.getenv("RHODAWK_EMBED_CACHE_DIR", "/data/embed_cache")
BATCH_SIZE       = int(os.getenv("RHODAWK_EMBED_BATCH_SIZE", "16"))
MAX_TOKENS       = int(os.getenv("RHODAWK_EMBED_MAX_TOKENS", "8192"))

# Nomic models prepend a task-specific instruction prefix.
_NOMIC_INSTRUCTIONS = {
    "code_search":  "Represent this code snippet for searching relevant snippets:",
    "code_query":   "Represent this query for searching relevant code snippets:",
    "text_search":  "search_document:",
    "text_query":   "search_query:",
}


def _detect_device() -> str:
    forced = os.getenv("RHODAWK_EMBED_DEVICE", "").strip().lower()
    if forced in {"cpu", "cuda", "mps"}:
        return forced
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:                                       # noqa: BLE001
        pass
    return "cpu"


class SemanticEmbedder:
    """Process-wide singleton wrapper around a sentence-transformers model."""

    _instance: Optional["SemanticEmbedder"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get(cls) -> "SemanticEmbedder":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._model = None
        self._model_id: Optional[str] = None
        self._device: str = _detect_device()
        self._load_lock = threading.Lock()
        self._dim: Optional[int] = None
        os.makedirs(CACHE_DIR, exist_ok=True)

    # ── Lazy load with graceful fallback chain ────────────────────────
    def _load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except Exception as exc:                        # noqa: BLE001
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Add `sentence-transformers>=2.7.0` to requirements.txt"
                ) from exc

            for candidate in [DEFAULT_MODEL, FALLBACK_MODEL, LAST_RESORT]:
                try:
                    LOG.info("Loading embedder %s on %s", candidate, self._device)
                    started = time.monotonic()
                    self._model = SentenceTransformer(
                        candidate,
                        device=self._device,
                        cache_folder=CACHE_DIR,
                        trust_remote_code=True,           # nomic checkpoints need this
                    )
                    if hasattr(self._model, "max_seq_length"):
                        self._model.max_seq_length = min(
                            MAX_TOKENS, getattr(self._model, "max_seq_length", MAX_TOKENS)
                        )
                    self._model_id = candidate
                    self._dim = int(self._model.get_sentence_embedding_dimension() or 0)
                    LOG.info(
                        "Embedder ready (%s, dim=%s, %.1fs)",
                        candidate, self._dim, time.monotonic() - started,
                    )
                    return
                except Exception as exc:                    # noqa: BLE001
                    LOG.warning("Embedder %s unavailable: %s", candidate, exc)
                    self._model = None
            raise RuntimeError(
                "No embedder model could be loaded (tried "
                f"{DEFAULT_MODEL}, {FALLBACK_MODEL}, {LAST_RESORT})."
            )

    # ── Public read-only properties ───────────────────────────────────
    @property
    def model_id(self) -> Optional[str]: return self._model_id
    @property
    def device(self) -> str: return self._device
    @property
    def dim(self) -> Optional[int]: return self._dim

    # ── Encoding ──────────────────────────────────────────────────────
    def _prefix_for(self, instruction: Optional[str], is_code: bool) -> str:
        if not instruction:
            return ""
        if instruction in _NOMIC_INSTRUCTIONS:
            return _NOMIC_INSTRUCTIONS[instruction] + " "
        return instruction.rstrip() + " "

    def embed(
        self,
        texts: Union[str, Sequence[str]],
        *,
        instruction: Optional[str] = None,
        normalize: bool = True,
        is_code: bool = True,
    ) -> list[list[float]]:
        """Encode ``texts`` into L2-normalised dense vectors."""
        self._load()
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []
        prefix = self._prefix_for(instruction, is_code)
        prepped = [(prefix + t) if prefix else t for t in texts]
        vectors = self._model.encode(                           # type: ignore[union-attr]
            prepped,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return [v.tolist() for v in vectors]

    def embed_one(
        self, text: str, *, instruction: Optional[str] = None,
        normalize: bool = True, is_code: bool = True,
    ) -> list[float]:
        return self.embed(text, instruction=instruction,
                          normalize=normalize, is_code=is_code)[0]

    # ── Similarity helpers ────────────────────────────────────────────
    @staticmethod
    def cosine(a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

    def rank(
        self,
        query: str,
        candidates: Iterable[str],
        *,
        top_k: int = 5,
        is_code: bool = True,
    ) -> list[tuple[int, float]]:
        """Return (index, score) pairs sorted by descending cosine similarity."""
        cand_list = list(candidates)
        if not cand_list:
            return []
        q_vec = self.embed_one(
            query, instruction="code_query" if is_code else "text_query",
            is_code=is_code,
        )
        c_vecs = self.embed(
            cand_list, instruction="code_search" if is_code else "text_search",
            is_code=is_code,
        )
        scored = [(i, self.cosine(q_vec, v)) for i, v in enumerate(c_vecs)]
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[: max(1, top_k)]


# ── Module-level convenience ──────────────────────────────────────────
def embed(texts, **kwargs) -> list[list[float]]:
    return SemanticEmbedder.get().embed(texts, **kwargs)


def embed_one(text: str, **kwargs) -> list[float]:
    return SemanticEmbedder.get().embed_one(text, **kwargs)


def rank(query: str, candidates, **kwargs) -> list[tuple[int, float]]:
    return SemanticEmbedder.get().rank(query, candidates, **kwargs)


def cosine(a, b) -> float:
    return SemanticEmbedder.cosine(a, b)


def pre_warm() -> bool:
    """Synchronously load the model. Designed for ``app.py`` startup thread."""
    try:
        e = SemanticEmbedder.get()
        e._load()
        return e.model_id is not None
    except Exception as exc:                                # noqa: BLE001
        LOG.warning("Semantic embedder pre-warm failed: %s", exc)
        return False


def status() -> dict:
    e = SemanticEmbedder.get()
    return {
        "loaded":    e._model is not None,
        "model_id":  e.model_id,
        "device":    e.device,
        "dim":       e.dim,
        "cache_dir": CACHE_DIR,
    }

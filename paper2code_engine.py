"""
paper2code_engine.py
────────────────────
Rhodawk-native re-implementation of the
``PrathamLearnsToCode/paper2code`` skill, vendored under
``vendor/paper2code/``.

The upstream skill converts an arXiv paper into a citation-anchored,
ambiguity-audited Python implementation.  Inside Rhodawk we want the
same capability available to the orchestrator so the autonomous loop
can:

  * Convert a freshly-discovered research paper (CVE write-up, novel
    fuzzing technique, new symbolic-execution heuristic, …) into a
    runnable scaffold under ``training_store.py``'s data flywheel.
  * Feed the generated ``REPRODUCTION_NOTES.md`` ambiguity audit into
    ``knowledge_rag.py`` so the embedding memory tracks *what is and
    isn't specified* in a paper, not just the paper's text.
  * Drive the ``hermes_orchestrator`` Night-Hunt mode: when a new
    primitive is discovered in the wild, fetch the paper, scaffold a
    reproduction, hand the scaffold to OpenClaude for completion,
    test-run it through ``language_runtime.py``.

The implementation is faithful to the upstream skill's six-stage
pipeline (``vendor/paper2code/SKILL.md`` + ``pipeline/01..05``) but
lives in pure Python so the orchestrator can call it without spawning
a separate skill-runner subprocess.

LLM access is intentionally pluggable — by default we route through
the existing OpenClaude gRPC bridge (``openclaude_grpc``) used
elsewhere in Rhodawk, but tests / dry runs can pass any callable with
the signature ``(prompt: str, *, system: str = "") -> str``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

log = logging.getLogger("rhodawk.paper2code")

# ─── Locations ─────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
VENDOR_DIR = Path(
    os.environ.get("RHODAWK_PAPER2CODE_DIR", str(_HERE / "vendor" / "paper2code"))
)
DEFAULT_OUTPUT_ROOT = Path(
    os.environ.get("RHODAWK_PAPER2CODE_OUT", "/data/paper2code")
)


# ─── Types ─────────────────────────────────────────────────────────────
LLMFn = Callable[..., str]


@dataclass
class PaperMetadata:
    arxiv_id: str
    title: str = ""
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    pdf_url: str = ""
    abs_url: str = ""

    def slug(self) -> str:
        base = re.sub(r"[^a-z0-9]+", "_", self.title.lower()).strip("_")
        if not base:
            base = re.sub(r"[^a-z0-9]+", "_", self.arxiv_id.lower())
        return base[:80] or self.arxiv_id


@dataclass
class AmbiguityFinding:
    item: str
    classification: str   # SPECIFIED | PARTIALLY_SPECIFIED | UNSPECIFIED
    notes: str = ""
    citation: str = ""

    def to_dict(self) -> Dict[str, str]:
        return self.__dict__.copy()


@dataclass
class Paper2CodeResult:
    paper: PaperMetadata
    output_dir: Path
    contribution: str
    ambiguity: List[AmbiguityFinding]
    files: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "arxiv_id": self.paper.arxiv_id,
            "title": self.paper.title,
            "slug": self.paper.slug(),
            "output_dir": str(self.output_dir),
            "contribution": self.contribution,
            "ambiguity_count": len(self.ambiguity),
            "unspecified_count": sum(
                1 for a in self.ambiguity if a.classification == "UNSPECIFIED"
            ),
            "files": list(self.files),
        }


# ─── Stage 1 — Paper acquisition ──────────────────────────────────────
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")


def parse_arxiv_id(value: str) -> str:
    """Accepts a bare id, an abs/pdf URL, or a versioned id."""
    m = ARXIV_ID_RE.search(value)
    if not m:
        raise ValueError(f"could not extract arxiv id from {value!r}")
    return m.group(1)


def fetch_metadata(arxiv_id: str, *, timeout: float = 20.0) -> PaperMetadata:
    """Pull title / abstract / authors via the arXiv Atom API.

    Falls back to an empty metadata record if the network call fails so
    the rest of the pipeline can still run on a manually-supplied
    abstract.
    """
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    md = PaperMetadata(
        arxiv_id=arxiv_id,
        abs_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
    )
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        log.warning("arxiv fetch failed for %s: %s", arxiv_id, exc)
        return md

    title = re.search(r"<title>([^<]+)</title>", body[body.find("<entry"):] if "<entry" in body else body)
    summary = re.search(r"<summary>([\s\S]*?)</summary>", body)
    authors = re.findall(r"<name>([^<]+)</name>", body)
    if title:
        md.title = re.sub(r"\s+", " ", title.group(1)).strip()
    if summary:
        md.abstract = re.sub(r"\s+", " ", summary.group(1)).strip()
    md.authors = [a.strip() for a in authors[:20]]
    return md


# ─── Stage 2 — Contribution identification ────────────────────────────
def identify_contribution(meta: PaperMetadata, *, llm: Optional[LLMFn] = None) -> str:
    if llm is None:
        # Heuristic fallback — first sentence of the abstract trimmed.
        if not meta.abstract:
            return f"(no abstract available for {meta.arxiv_id})"
        first = re.split(r"(?<=[.!?])\s+", meta.abstract.strip(), maxsplit=1)[0]
        return first.strip()

    prompt = (
        "Identify the single core contribution of this paper in <=2 sentences.\n"
        "Avoid hype, no marketing words, no bullet points.\n\n"
        f"Title: {meta.title}\n\nAbstract:\n{meta.abstract}\n"
    )
    try:
        return llm(prompt, system="You are a meticulous ML research reviewer.").strip()
    except Exception as exc:
        log.warning("contribution LLM call failed: %s", exc)
        return meta.abstract.split(".")[0].strip() + "."


# ─── Stage 3 — Ambiguity audit ────────────────────────────────────────
DEFAULT_AUDIT_DIMENSIONS: List[str] = [
    "model architecture / layer wiring",
    "loss function & objective",
    "optimizer + learning-rate schedule",
    "batch size / sequence length",
    "weight initialisation",
    "regularisation (dropout, weight decay, label smoothing, …)",
    "dataset & preprocessing",
    "evaluation metric & protocol",
    "hardware & training duration",
    "random seed handling / reproducibility notes",
]


def audit_ambiguity(
    meta: PaperMetadata,
    *,
    llm: Optional[LLMFn] = None,
    dimensions: Optional[List[str]] = None,
) -> List[AmbiguityFinding]:
    dims = dimensions or DEFAULT_AUDIT_DIMENSIONS
    if llm is None:
        # Heuristic: mark everything UNSPECIFIED so the human reviewer
        # is forced to confirm — never silently assume.
        return [
            AmbiguityFinding(
                item=d,
                classification="UNSPECIFIED",
                notes="Heuristic mode (no LLM available) — confirm manually.",
            )
            for d in dims
        ]

    findings: List[AmbiguityFinding] = []
    for d in dims:
        prompt = (
            "For the paper below, decide whether the following implementation\n"
            "detail is SPECIFIED, PARTIALLY_SPECIFIED, or UNSPECIFIED. "
            "Reply ONLY as JSON with keys "
            '`{"classification": "...", "notes": "...", "citation": "..."}`.\n\n'
            f"Detail: {d}\n\n"
            f"Title: {meta.title}\nAbstract: {meta.abstract}\n"
        )
        try:
            raw = llm(prompt, system="You are an honest, paranoid ML reviewer.").strip()
            cleaned = raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw else "{}"
            parsed = json.loads(cleaned)
            findings.append(
                AmbiguityFinding(
                    item=d,
                    classification=str(parsed.get("classification", "UNSPECIFIED")).upper(),
                    notes=str(parsed.get("notes", ""))[:500],
                    citation=str(parsed.get("citation", ""))[:200],
                )
            )
        except Exception as exc:
            log.warning("ambiguity audit failed for %s: %s", d, exc)
            findings.append(
                AmbiguityFinding(item=d, classification="UNSPECIFIED",
                                 notes=f"LLM error: {exc}")
            )
    return findings


# ─── Stage 4 — Code generation (scaffold) ─────────────────────────────
SCAFFOLD_FILES = {
    "README.md": "readme_template.md",
    "REPRODUCTION_NOTES.md": "reproduction_notes_template.md",
    "configs/base.yaml": "config_template.yaml",
    "src/model.py": "model_template.py",
    "src/loss.py": "loss_template.py",
    "src/data.py": "data_template.py",
    "src/train.py": "train_template.py",
    "src/evaluate.py": "evaluate_template.py",
}


def _load_scaffold(template_name: str) -> str:
    path = VENDOR_DIR / "scaffolds" / template_name
    if not path.is_file():
        return f"# scaffold {template_name} missing from vendored paper2code\n"
    return path.read_text(encoding="utf-8", errors="replace")


def _render(template: str, *, meta: PaperMetadata, contribution: str) -> str:
    """Lightweight token substitution.  The upstream scaffolds use
    ``{{TOKEN}}`` style placeholders in some files and bare names in
    others — we handle both."""
    repl = {
        "{{PAPER_TITLE}}": meta.title or meta.arxiv_id,
        "{{ARXIV_ID}}": meta.arxiv_id,
        "{{ABS_URL}}": meta.abs_url,
        "{{PDF_URL}}": meta.pdf_url,
        "{{AUTHORS}}": ", ".join(meta.authors) or "(unknown)",
        "{{CONTRIBUTION}}": contribution,
    }
    out = template
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def generate_scaffold(
    meta: PaperMetadata,
    contribution: str,
    ambiguity: List[AmbiguityFinding],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Paper2CodeResult:
    output_dir = output_root / meta.slug()
    output_dir.mkdir(parents=True, exist_ok=True)

    written: List[str] = []
    for rel_path, template_name in SCAFFOLD_FILES.items():
        target = output_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        rendered = _render(_load_scaffold(template_name),
                           meta=meta, contribution=contribution)
        target.write_text(rendered, encoding="utf-8")
        written.append(rel_path)

    # Ambiguity audit as machine-readable JSON next to the human notes.
    audit_path = output_dir / "ambiguity_audit.json"
    audit_path.write_text(
        json.dumps([a.to_dict() for a in ambiguity], indent=2),
        encoding="utf-8",
    )
    written.append("ambiguity_audit.json")

    return Paper2CodeResult(
        paper=meta,
        output_dir=output_dir,
        contribution=contribution,
        ambiguity=ambiguity,
        files=written,
    )


# ─── End-to-end ───────────────────────────────────────────────────────
def run(
    paper_input: str,
    *,
    llm: Optional[LLMFn] = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Paper2CodeResult:
    """Full pipeline: arxiv id/url → scaffolded implementation directory.

    Parameters
    ----------
    paper_input
        Bare arxiv id, abs URL, pdf URL, or versioned id.
    llm
        Optional ``(prompt, *, system="") -> str`` callable.  When omitted,
        the orchestrator's OpenClaude bridge is auto-discovered via
        :func:`_default_llm`; if that fails too the heuristic fallback is
        used and every audit dimension is marked UNSPECIFIED.
    output_root
        Where to drop the generated ``{slug}/`` directory.  Defaults to
        ``/data/paper2code`` so HF Spaces persistence picks it up.
    """
    arxiv_id = parse_arxiv_id(paper_input)
    meta = fetch_metadata(arxiv_id)
    llm = llm or _default_llm()
    contribution = identify_contribution(meta, llm=llm)
    ambiguity = audit_ambiguity(meta, llm=llm)
    return generate_scaffold(meta, contribution, ambiguity, output_root=output_root)


# ─── OpenClaude bridge auto-discovery ─────────────────────────────────
def _default_llm() -> Optional[LLMFn]:
    """Return a callable wrapping the existing OpenClaude gRPC bridge,
    or ``None`` if it isn't importable in this environment.
    """
    try:
        # Local import keeps this module standalone-importable.
        from openclaude_grpc import openclaude_pb2, openclaude_pb2_grpc  # type: ignore
        import grpc  # type: ignore
    except Exception as exc:
        log.info("OpenClaude bridge unavailable (%s); using heuristic mode.", exc)
        return None

    host = os.environ.get("OPENCLAUDE_GRPC_HOST", "127.0.0.1")
    port = os.environ.get("OPENCLAUDE_GRPC_PORT_DO", "50051")
    channel = grpc.insecure_channel(f"{host}:{port}")
    stub = openclaude_pb2_grpc.OpenClaudeStub(channel)

    def call(prompt: str, *, system: str = "") -> str:
        req = openclaude_pb2.GenerateRequest(   # type: ignore[attr-defined]
            prompt=prompt,
            system=system,
        )
        try:
            resp = stub.Generate(req, timeout=120)
            return getattr(resp, "text", "") or ""
        except Exception as exc:   # pragma: no cover — runtime only
            log.warning("OpenClaude Generate failed: %s", exc)
            return ""

    return call


def stats() -> Dict[str, object]:
    return {
        "vendor_dir": str(VENDOR_DIR),
        "output_root": str(DEFAULT_OUTPUT_ROOT),
        "vendor_present": VENDOR_DIR.is_dir(),
        "scaffolds_present": (VENDOR_DIR / "scaffolds").is_dir(),
        "openclaude_available": _default_llm() is not None,
    }


__all__ = [
    "PaperMetadata",
    "AmbiguityFinding",
    "Paper2CodeResult",
    "parse_arxiv_id",
    "fetch_metadata",
    "identify_contribution",
    "audit_ambiguity",
    "generate_scaffold",
    "run",
    "stats",
]

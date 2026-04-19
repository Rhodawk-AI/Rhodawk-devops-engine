"""
Rhodawk AI — Hermes Master Orchestrator
========================================
Hermes is the intelligent agent that coordinates all security research components.
It acts as the "brain" — deciding which tools to deploy, in what order, and how
to synthesize findings into a coherent vulnerability report.

Architecture:
  Hermes receives a target (repo + optional focus area) and executes a dynamic
  multi-phase research plan using tool calls. It maintains state across phases,
  routes findings between components, and escalates confidence incrementally.

Phases:
  1. RECON       — clone, fingerprint, map attack surface
  2. STATIC      — taint analysis, symbolic execution planning, CWE pattern match
  3. DYNAMIC     — fuzzing harness generation + execution
  4. EXPLOIT     — exploit primitive reasoning on confirmed crashes
  5. CONSENSUS   — multi-model adversarial verdict on findings
  6. DISCLOSURE  — package report, hold for human approval

Custom Algorithms:
  VES  — Vulnerability Entropy Score: how surprising/dangerous a code path is
  TVG  — Temporal Vulnerability Graph: how bugs propagate across commits
  ACTS — Adversarial Consensus Trust Score: Bayesian multi-model confidence
  CAD  — Commit Anomaly Detection: statistical detection of silent security patches
  SSEC — Semantic Similarity Exploit Chain: embedding distance to known exploit patterns
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional

import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
HERMES_MODEL       = os.getenv("HERMES_MODEL", "deepseek/deepseek-r1:free")
HERMES_FAST_MODEL  = os.getenv("HERMES_FAST_MODEL", "deepseek/deepseek-v3:free")
OPENROUTER_BASE    = "https://openrouter.ai/api/v1"

_log_lock = threading.Lock()
_hermes_logs: list[str] = []


def hermes_log(msg: str, level: str = "HERMES"):
    ts = time.strftime("%H:%M:%S")
    icons = {
        "HERMES": "🧠", "RECON": "🔭", "STATIC": "🔬", "DYNAMIC": "💥",
        "EXPLOIT": "⚔️", "CONSENSUS": "🗳", "DISCLOSURE": "📋",
        "TOOL": "🔧", "FIND": "🎯", "WARN": "⚠️", "OK": "✅", "FAIL": "❌",
        "VES": "📊", "TVG": "🕸", "ACTS": "🧮", "CAD": "👁", "SSEC": "🔗",
    }
    line = f"[{ts}] {icons.get(level, '🧠')} [HERMES] {msg}"
    print(line)
    with _log_lock:
        _hermes_logs.append(line)
        if len(_hermes_logs) > 500:
            _hermes_logs.pop(0)


def get_hermes_logs() -> list[str]:
    with _log_lock:
        return list(_hermes_logs)


# ──────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────

class ResearchPhase(str, Enum):
    RECON      = "RECON"
    STATIC     = "STATIC"
    DYNAMIC    = "DYNAMIC"
    EXPLOIT    = "EXPLOIT"
    CONSENSUS  = "CONSENSUS"
    DISCLOSURE = "DISCLOSURE"
    COMPLETE   = "COMPLETE"


@dataclass
class VulnerabilityFinding:
    finding_id: str
    title: str
    cwe_id: str
    severity: str            # CRITICAL | HIGH | MEDIUM | LOW
    confidence: float        # 0.0 - 1.0
    file_path: str
    line_number: int
    description: str
    proof_of_concept: str
    exploit_primitive: str   # overflow | uaf | race | injection | crypto | logic
    ves_score: float         # Vulnerability Entropy Score
    acts_score: float        # Adversarial Consensus Trust Score
    phase_found: str
    raw_evidence: dict = field(default_factory=dict)
    disclosure_status: str = "PENDING_HUMAN_APPROVAL"
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))


@dataclass
class HermesSession:
    session_id: str
    target_repo: str
    repo_dir: str
    phase: ResearchPhase = ResearchPhase.RECON
    findings: list[VulnerabilityFinding] = field(default_factory=list)
    tool_call_log: list[dict] = field(default_factory=list)
    attack_surface: dict = field(default_factory=dict)
    tvg_graph: dict = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    completed_at: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# TOOL REGISTRY — Hermes dispatches these
# ──────────────────────────────────────────────────────────────

class HermesTool:
    """Base class for all Hermes-dispatchable tools."""
    name: str = "base_tool"
    description: str = ""

    def run(self, **kwargs) -> dict:
        raise NotImplementedError


class ReconTool(HermesTool):
    name = "recon"
    description = "Map attack surface of a cloned repository. Returns language, entry points, dangerous sinks, security-critical files."

    def run(self, repo_dir: str, **kwargs) -> dict:
        hermes_log(f"Recon scan → {repo_dir}", "RECON")
        from taint_analyzer import map_attack_surface
        return map_attack_surface(repo_dir)


class TaintTool(HermesTool):
    name = "taint_analysis"
    description = "Run taint/data-flow analysis to trace untrusted input to dangerous sinks."

    def run(self, repo_dir: str, focus_files: list[str] = None, **kwargs) -> dict:
        hermes_log(f"Taint analysis → {len(focus_files or [])} focus files", "STATIC")
        from taint_analyzer import run_taint_analysis
        return run_taint_analysis(repo_dir, focus_files=focus_files)


class SymbolicTool(HermesTool):
    name = "symbolic_execution"
    description = "Run symbolic execution to explore all code paths and find unsatisfied constraints."

    def run(self, repo_dir: str, target_function: str = None, **kwargs) -> dict:
        hermes_log(f"Symbolic execution → {target_function or 'auto-select'}", "STATIC")
        from symbolic_engine import run_symbolic_analysis
        return run_symbolic_analysis(repo_dir, target_function=target_function)


class FuzzTool(HermesTool):
    name = "fuzz"
    description = "Generate a fuzzing harness and execute it against a target function or binary."

    def run(self, repo_dir: str, target: str, language: str = "python", duration_s: int = 60, **kwargs) -> dict:
        hermes_log(f"Fuzzing → {target} ({duration_s}s)", "DYNAMIC")
        from fuzzing_engine import run_fuzzing_campaign
        return run_fuzzing_campaign(repo_dir, target, language=language, duration_s=duration_s)


class ExploitTool(HermesTool):
    name = "exploit_reasoning"
    description = "Reason about exploitability of a crash or vulnerability candidate. Generate PoC."

    def run(self, crash_input: str, crash_output: str, file_path: str, vuln_type: str, **kwargs) -> dict:
        hermes_log(f"Exploit reasoning → {vuln_type} in {file_path}", "EXPLOIT")
        from exploit_primitives import reason_exploitability
        return reason_exploitability(crash_input, crash_output, file_path, vuln_type)


class CVETool(HermesTool):
    name = "cve_intel"
    description = "Query CVE/NVD/CWE knowledge base for similar historical vulnerabilities."

    def run(self, description: str, cwe_hint: str = None, **kwargs) -> dict:
        hermes_log(f"CVE intel → {cwe_hint or 'auto'}", "STATIC")
        from cve_intel import query_cve_intel
        return query_cve_intel(description, cwe_hint=cwe_hint)


class CommitWatchTool(HermesTool):
    name = "commit_watch"
    description = "Analyze recent commits for silent security patches using CAD algorithm."

    def run(self, repo_dir: str, lookback_commits: int = 50, **kwargs) -> dict:
        hermes_log(f"Commit watch → last {lookback_commits} commits", "CAD")
        from commit_watcher import analyze_recent_commits
        return analyze_recent_commits(repo_dir, lookback=lookback_commits)


class SSECTool(HermesTool):
    name = "ssec_scan"
    description = "Semantic Similarity Exploit Chain: find code patterns similar to known exploits."

    def run(self, repo_dir: str, focus_files: list[str] = None, **kwargs) -> dict:
        hermes_log("SSEC scan — embedding similarity to known exploit patterns", "SSEC")
        from cve_intel import run_ssec_scan
        return run_ssec_scan(repo_dir, focus_files=focus_files)


class ChainAnalyzerTool(HermesTool):
    name = "chain_analysis"
    description = (
        "Synthesize stored primitive findings into higher-severity exploit chains. "
        "Call after at least 2 primitives are recorded. Returns THEORETICAL proposals "
        "tagged PENDING_HUMAN_REVIEW — no chain is executed automatically."
    )

    def run(self, repo_dir: str, repo: str = "", **kwargs) -> dict:
        hermes_log(f"Chain analysis → {repo or repo_dir}", "EXPLOIT")
        from chain_analyzer import analyze_chains, get_all_primitives
        target = repo or repo_dir
        primitives = get_all_primitives(repo=target)
        if len(primitives) < 2:
            return {"chains": [], "note": f"Only {len(primitives)} primitive(s) stored — need ≥2 to chain"}
        chains = analyze_chains(repo=target)
        return {"chains": chains, "primitive_count": len(primitives)}


_TOOL_REGISTRY: dict[str, HermesTool] = {
    t.name: t() for t in [
        ReconTool, TaintTool, SymbolicTool, FuzzTool,
        ExploitTool, CVETool, CommitWatchTool, SSECTool,
        ChainAnalyzerTool,
    ]
}


def _dispatch_tool(tool_name: str, args: dict, session: HermesSession) -> dict:
    tool = _TOOL_REGISTRY.get(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}"}
    start = time.time()
    try:
        result = tool.run(**args)
    except Exception as e:
        result = {"error": str(e)}
    elapsed = round(time.time() - start, 2)
    session.tool_call_log.append({
        "tool": tool_name, "args": args,
        "result_keys": list(result.keys()) if isinstance(result, dict) else "non-dict",
        "elapsed_s": elapsed, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    return result


# ──────────────────────────────────────────────────────────────
# VES — VULNERABILITY ENTROPY SCORE (Custom Algorithm)
# ──────────────────────────────────────────────────────────────

def compute_ves(
    reachability: float,     # 0-1: how reachable is this from untrusted input
    severity_class: str,     # CRITICAL | HIGH | MEDIUM | LOW
    novelty: float,          # 0-1: how different from known CVEs (higher = more novel/interesting)
    exploit_complexity: str, # LOW | MEDIUM | HIGH
    auth_required: bool,
) -> float:
    """
    VES (Vulnerability Entropy Score) — custom algorithm.

    Measures the "information surprise" of a vulnerability weighted by its
    danger. High VES = high-value finding (novel + dangerous + reachable).

    Formula inspired by Shannon entropy: VES = -log2(P) × W
    Where P is the probability an auditor would find this naturally,
    and W is a danger weight. Higher VES = better bug bounty target.
    """
    import math

    severity_weight = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.5, "LOW": 0.25}.get(severity_class, 0.5)
    complexity_factor = {"LOW": 0.9, "MEDIUM": 0.6, "HIGH": 0.3}.get(exploit_complexity, 0.6)
    auth_penalty = 0.7 if auth_required else 1.0

    # P(naturally found) = (1 - novelty) × (1 - reachability × 0.5)
    p_found_naturally = max(0.001, (1.0 - novelty) * (1.0 - reachability * 0.5))
    entropy = -math.log2(p_found_naturally)

    ves = entropy * severity_weight * complexity_factor * auth_penalty * reachability
    return round(min(ves, 10.0), 4)


# ──────────────────────────────────────────────────────────────
# ACTS — ADVERSARIAL CONSENSUS TRUST SCORE (Custom Algorithm)
# ──────────────────────────────────────────────────────────────

def compute_acts(model_verdicts: list[dict]) -> float:
    """
    ACTS (Adversarial Consensus Trust Score) — Bayesian multi-model confidence.

    Each model contributes a vote weighted by its stated confidence.
    Agreement amplifies confidence. Disagreement deflates it.
    Returns 0.0–1.0 where >0.7 = high trust finding.
    """
    if not model_verdicts:
        return 0.0

    confirm_weight = 0.0
    total_weight = 0.0
    agreements = 0
    first_verdict = model_verdicts[0].get("verdict", "UNCERTAIN")

    for verdict in model_verdicts:
        v = verdict.get("verdict", "UNCERTAIN")
        c = float(verdict.get("confidence", 0.5))
        total_weight += c
        if v in ("CONFIRM", "APPROVE", "VULNERABLE"):
            confirm_weight += c
        if v == first_verdict:
            agreements += 1

    if total_weight == 0:
        return 0.0

    raw_score = confirm_weight / total_weight
    agreement_factor = agreements / len(model_verdicts)
    acts = raw_score * (0.6 + 0.4 * agreement_factor)
    return round(acts, 4)


# ──────────────────────────────────────────────────────────────
# LLM CALLS — Hermes reasoning engine
# ──────────────────────────────────────────────────────────────

_HERMES_SYSTEM = """You are Hermes, a world-class autonomous security research agent.
Your goal is to find real, exploitable vulnerabilities in open source projects.
You are methodical, adversarial, and thorough. You think like an attacker.

You have access to these tools:
- recon: Map attack surface (entry points, dangerous sinks, security-critical files)
- taint_analysis: Trace untrusted input to dangerous sinks
- symbolic_execution: Explore all code paths mathematically
- fuzz: Generate and run fuzzing campaigns to find crashes
- exploit_reasoning: Reason about exploitability, generate PoC
- cve_intel: Query historical CVEs for similar patterns
- commit_watch: Find silent security patches in commit history
- ssec_scan: Semantic similarity to known exploit patterns
- chain_analysis: Synthesize stored primitive findings into exploit chains (call after ≥2 findings)

For each target, produce a research plan and execute it step by step.
When you find something, rate its severity honestly. Never hallucinate findings.
A false positive wastes a maintainer's time. Be certain before escalating.

Respond with JSON tool calls in this format:
{
  "thought": "your reasoning about what to do next",
  "tool": "tool_name",
  "args": {"key": "value"},
  "phase": "RECON|STATIC|DYNAMIC|EXPLOIT|CONSENSUS|DISCLOSURE"
}
Or to report a final finding:
{
  "thought": "summary reasoning",
  "finding": {
    "title": "...", "cwe_id": "CWE-XXX", "severity": "HIGH",
    "confidence": 0.85, "file_path": "...", "line_number": 0,
    "description": "...", "proof_of_concept": "...", "exploit_primitive": "..."
  }
}
Or to signal completion:
{"done": true, "summary": "..."}
"""


_RATE_LIMIT_BACKOFF_DELAYS = [15, 30, 60]  # seconds — exponential backoff for 429s


def _hermes_llm_call(messages: list[dict], model: str = None, timeout: int = 120) -> dict:
    """
    Call the Hermes LLM with exponential backoff on rate-limit (429) responses.
    Three retries before giving up — prevents a single 429 from aborting a session.
    """
    if not OPENROUTER_API_KEY:
        return {"done": True, "summary": "OPENROUTER_API_KEY not set"}

    model = model or HERMES_MODEL
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rhodawk.ai",
        "X-Title": "Rhodawk Hermes Orchestrator",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    last_error: Exception | None = None
    for attempt, backoff in enumerate([0] + _RATE_LIMIT_BACKOFF_DELAYS):
        if backoff:
            hermes_log(f"Rate limit hit — waiting {backoff}s before retry {attempt}/{len(_RATE_LIMIT_BACKOFF_DELAYS)}", "WARN")
            time.sleep(backoff)
        try:
            resp = requests.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=headers, json=payload, timeout=timeout,
            )
            if resp.status_code == 429:
                last_error = Exception(f"HTTP 429 rate limit (attempt {attempt + 1})")
                hermes_log(str(last_error), "WARN")
                continue
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            if "429" in str(e):
                last_error = e
                hermes_log(f"Rate limit exception: {e}", "WARN")
                continue
            hermes_log(f"LLM call failed: {e}", "WARN")
            return {"done": True, "summary": f"LLM error: {e}"}

    hermes_log(f"LLM call exhausted all retries. Last error: {last_error}", "WARN")
    return {"done": True, "summary": f"LLM rate limit — all retries exhausted: {last_error}"}


# ──────────────────────────────────────────────────────────────
# MAIN HERMES RESEARCH LOOP
# ──────────────────────────────────────────────────────────────

def run_hermes_research(
    target_repo: str,
    repo_dir: str,
    focus_area: str = "",
    max_iterations: int = 20,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> HermesSession:
    """
    Main Hermes research loop. Runs until max_iterations or completion.
    Returns a HermesSession with all findings.
    """
    session_id = hashlib.sha256(f"{target_repo}{time.time()}".encode()).hexdigest()[:12]
    session = HermesSession(
        session_id=session_id,
        target_repo=target_repo,
        repo_dir=repo_dir,
    )

    def log(msg, level="HERMES"):
        hermes_log(msg, level)
        if progress_callback:
            progress_callback(f"[{level}] {msg}")

    log(f"Session {session_id} started → {target_repo}")
    log(f"Model: {HERMES_MODEL} | Max iterations: {max_iterations}")

    messages = [
        {"role": "system", "content": _HERMES_SYSTEM},
        {"role": "user", "content": (
            f"TARGET REPOSITORY: {target_repo}\n"
            f"LOCAL PATH: {repo_dir}\n"
            f"FOCUS AREA: {focus_area or 'Full autonomous scan — prioritize attack surface'}\n\n"
            "Begin your security research. Start with reconnaissance to map the attack surface, "
            "then systematically probe for vulnerabilities. Remember: only report findings you "
            "are confident are real and exploitable."
        )},
    ]

    for iteration in range(max_iterations):
        log(f"Iteration {iteration + 1}/{max_iterations}", "HERMES")

        response = _hermes_llm_call(messages)

        if response.get("done"):
            log(f"Research complete: {response.get('summary', 'No summary')}", "OK")
            session.phase = ResearchPhase.COMPLETE
            break

        if "finding" in response:
            finding_data = response["finding"]
            log(f"FINDING: {finding_data.get('title', '?')} [{finding_data.get('severity', '?')}]", "FIND")

            # Compute VES
            ves = compute_ves(
                reachability=finding_data.get("confidence", 0.5),
                severity_class=finding_data.get("severity", "MEDIUM"),
                novelty=0.6,
                exploit_complexity="MEDIUM",
                auth_required=False,
            )
            log(f"VES Score: {ves}", "VES")

            finding = VulnerabilityFinding(
                finding_id=hashlib.sha256(
                    f"{finding_data.get('file_path', '')}{finding_data.get('line_number', 0)}{time.time()}".encode()
                ).hexdigest()[:12],
                title=finding_data.get("title", "Unnamed Finding"),
                cwe_id=finding_data.get("cwe_id", "CWE-UNKNOWN"),
                severity=finding_data.get("severity", "MEDIUM"),
                confidence=float(finding_data.get("confidence", 0.5)),
                file_path=finding_data.get("file_path", ""),
                line_number=int(finding_data.get("line_number", 0)),
                description=finding_data.get("description", ""),
                proof_of_concept=finding_data.get("proof_of_concept", ""),
                exploit_primitive=finding_data.get("exploit_primitive", "unknown"),
                ves_score=ves,
                acts_score=0.0,
                phase_found=session.phase.value,
                disclosure_status="PENDING_HUMAN_APPROVAL",
            )
            session.findings.append(finding)

            messages.append({"role": "assistant", "content": json.dumps(response)})
            messages.append({"role": "user", "content": (
                f"Finding recorded (ID: {finding.finding_id}, VES: {ves}). "
                "Continue research — there may be more vulnerabilities. "
                "If you believe the surface is exhausted, signal done."
            )})
            continue

        if "tool" not in response:
            log("No tool call in response — signaling done", "WARN")
            break

        tool_name = response.get("tool", "")
        tool_args = response.get("args", {})
        phase_str = response.get("phase", session.phase.value)
        thought = response.get("thought", "")

        try:
            session.phase = ResearchPhase(phase_str)
        except ValueError:
            pass

        log(f"Phase: {session.phase.value} | Tool: {tool_name}", session.phase.value)
        if thought:
            log(f"Reasoning: {thought[:200]}", "HERMES")

        tool_args["repo_dir"] = repo_dir
        tool_result = _dispatch_tool(tool_name, tool_args, session)

        if tool_name == "recon" and isinstance(tool_result, dict):
            session.attack_surface = tool_result
            log(f"Attack surface: {len(tool_result.get('dangerous_sinks', []))} sinks, "
                f"{len(tool_result.get('entry_points', []))} entry points", "RECON")

        messages.append({"role": "assistant", "content": json.dumps(response)})
        messages.append({
            "role": "user",
            "content": (
                f"Tool '{tool_name}' result:\n```json\n"
                f"{json.dumps(tool_result, indent=2)[:3000]}\n```\n\n"
                "Based on these results, what is your next action?"
            ),
        })

        time.sleep(1)

    # Run ACTS consensus on all findings
    if session.findings:
        log(f"Running ACTS consensus on {len(session.findings)} finding(s)...", "CONSENSUS")
        session.phase = ResearchPhase.CONSENSUS
        _run_acts_consensus(session)

    session.phase = ResearchPhase.DISCLOSURE
    session.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    log(f"Session complete — {len(session.findings)} finding(s) pending human approval", "DISCLOSURE")
    return session


def _run_acts_consensus(session: HermesSession):
    """
    Run multi-model adversarial consensus on each finding to compute ACTS score.

    FIX (ACTS Bug): Previously _call_concurrent_consensus returned a single merged
    result, so compute_acts() always received a 1-item list with agreement_factor=1.0
    — completely bypassing the disagreement penalty.  Now we call each consensus model
    individually so all 3 raw verdicts are passed to compute_acts(), enabling the full
    Bayesian disagreement weighting to work as designed.
    """
    import concurrent.futures
    from adversarial_reviewer import _call_single_model, ADVERSARY_SYSTEM_PROMPT

    CONSENSUS_MODELS = [
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-3-27b-it:free",
    ]

    for finding in session.findings:
        hermes_log(f"ACTS consensus: {finding.finding_id}", "ACTS")
        prompt = (
            f"VULNERABILITY FINDING FOR CONSENSUS REVIEW\n\n"
            f"Title: {finding.title}\n"
            f"CWE: {finding.cwe_id}\n"
            f"Severity claimed: {finding.severity}\n"
            f"File: {finding.file_path}:{finding.line_number}\n"
            f"Description: {finding.description}\n"
            f"PoC: {finding.proof_of_concept}\n"
            f"Exploit primitive: {finding.exploit_primitive}\n\n"
            "Is this a real, exploitable vulnerability? Respond as a hostile security reviewer."
        )
        try:
            # Call all 3 models concurrently and collect individual raw verdicts.
            # This is required so compute_acts() receives the full disagreement signal
            # rather than a pre-merged single verdict (which collapses agreement_factor to 1.0).
            individual_results: list[dict] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(CONSENSUS_MODELS)) as ex:
                futures = {
                    ex.submit(_call_single_model, model, prompt): model
                    for model in CONSENSUS_MODELS
                }
                for future in concurrent.futures.as_completed(futures, timeout=90):
                    try:
                        result_dict, _ = future.result()
                        if result_dict is not None:
                            individual_results.append(result_dict)
                    except Exception:
                        pass

            if not individual_results:
                raise RuntimeError("All ACTS consensus models failed")

            # Build one verdict entry per model response so compute_acts sees N items.
            verdicts = [
                {
                    "verdict": r.get("verdict", "UNCERTAIN"),
                    "confidence": float(r.get("confidence", 0.5)),
                }
                for r in individual_results
            ]
            finding.acts_score = compute_acts(verdicts)
            hermes_log(
                f"ACTS score for {finding.finding_id}: {finding.acts_score} "
                f"({len(verdicts)} model verdicts: {[v['verdict'] for v in verdicts]})",
                "ACTS",
            )
        except Exception as e:
            hermes_log(f"ACTS consensus failed for {finding.finding_id}: {e}", "WARN")
            finding.acts_score = finding.confidence


# ──────────────────────────────────────────────────────────────
# TVG — TEMPORAL VULNERABILITY GRAPH (Custom Algorithm)
# ──────────────────────────────────────────────────────────────

def build_tvg(repo_dir: str, findings: list[VulnerabilityFinding]) -> dict:
    """
    TVG (Temporal Vulnerability Graph) — tracks how vulnerability patterns
    propagate across commits over time.

    Builds a directed graph: commit → file → vulnerable_function → severity
    Allows answering: "was this bug always here, or introduced recently?"
    """
    import subprocess
    graph = {"nodes": [], "edges": [], "hotspots": []}

    for finding in findings:
        if not finding.file_path:
            continue
        try:
            result = subprocess.run(
                ["git", "log", "--follow", "--oneline", "-20", "--", finding.file_path],
                cwd=repo_dir, capture_output=True, text=True, timeout=10,
            )
            commits = [line.split(" ", 1) for line in result.stdout.strip().splitlines() if line]
            for sha, msg in commits[:5]:
                node = {"id": sha[:8], "file": finding.file_path, "msg": msg[:80]}
                if node not in graph["nodes"]:
                    graph["nodes"].append(node)
                graph["edges"].append({
                    "from": sha[:8], "to": finding.finding_id,
                    "label": finding.cwe_id,
                })
            if len(commits) > 10:
                graph["hotspots"].append({
                    "file": finding.file_path, "commit_count": len(commits),
                    "finding": finding.finding_id,
                })
        except Exception:
            pass

    return graph


def get_session_summary(session: HermesSession) -> dict:
    """Produce a human-readable summary of a research session."""
    findings_by_sev: dict[str, list] = {}
    for f in session.findings:
        findings_by_sev.setdefault(f.severity, []).append(f)

    return {
        "session_id": session.session_id,
        "target": session.target_repo,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "phase": session.phase.value,
        "total_findings": len(session.findings),
        "by_severity": {k: len(v) for k, v in findings_by_sev.items()},
        "top_findings": [
            {
                "id": f.finding_id, "title": f.title, "cwe": f.cwe_id,
                "severity": f.severity, "ves": f.ves_score, "acts": f.acts_score,
                "file": f.file_path, "status": f.disclosure_status,
            }
            for f in sorted(session.findings, key=lambda x: x.ves_score, reverse=True)[:5]
        ],
        "tool_calls": len(session.tool_call_log),
        "attack_surface_size": len(session.attack_surface.get("dangerous_sinks", [])),
    }

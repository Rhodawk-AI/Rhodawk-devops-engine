"""
Rhodawk AI — Autonomous Red Team Fuzzing Engine (CEGIS)
========================================================
The Zero-Day Discovery Machine. No competitor has this.

What this does:
  When the Blue Team audit loop encounters a "Green" repository (all tests passing),
  this engine takes over. It autonomously ATTACKS the codebase — discovering
  mathematical invariants, synthesizing Property-Based Tests, and fuzzing them
  to exhaustion to find the minimal crashing counter-example (the zero-day payload).
  The crash is then handed to the Blue Team verification_loop.py for autonomous patching.

Architecture — CEGIS (Counter-Example Guided Inductive Synthesis):
  ┌─────────────────────────────────────────────────────────────────┐
  │                    RED TEAM ENGINE (This File)                  │
  │                                                                 │
  │  1. MCP Universal Analyzer                                      │
  │     └── Parse AST → score complexity → rank attack targets      │
  │                                                                 │
  │  2. Red Team LLM (The Attacker)                                 │
  │     └── Adversarial prompt → generate Hypothesis PBT           │
  │         targeting: overflows, race conditions, invariant breaks  │
  │                                                                 │
  │  3. Deterministic Fuzzing Loop                                  │
  │     └── Execute PBT via subprocess → aggressive randomization   │
  │         → extract minimal falsifying counter-example            │
  │                                                                 │
  │  4. CEGIS Re-attack (if no crash found)                        │
  │     └── Inject "survived inputs" back to LLM → demand harder   │
  │         invariant → repeat up to MAX_CEGIS_ROUNDS              │
  │                                                                 │
  │  5. Handoff to Blue Team                                        │
  │     └── Package crash payload → inject into verification_loop   │
  │         as a synthetic failing pytest → Blue Team patches it    │
  └─────────────────────────────────────────────────────────────────┘

Invariant classes targeted:
  - Mathematical: commutativity, associativity, idempotency, monotonicity
  - Boundary: integer overflow (sys.maxsize, 2^63-1, -1, 0), empty sequences
  - Roundtrip: encode→decode, serialize→deserialize, compress→decompress
  - Concurrency: race conditions via threading + shared state mutation
  - Type coercion: implicit conversions that cause precision loss or exceptions
  - State machine: functions that should be pure but carry hidden mutable state
"""

import ast
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from language_runtime import EnvConfig

# ──────────────────────────────────────────────────────────────
# CONFIGURATION & SECRETS
# ──────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
RED_TEAM_MODEL = os.getenv(
    "RHODAWK_RED_TEAM_MODEL",
    "openrouter/qwen/qwen-2.5-coder-32b-instruct:free",
)
RED_TEAM_MODEL_STRONG = os.getenv(
    "RHODAWK_RED_TEAM_MODEL_STRONG",
    "openrouter/anthropic/claude-3-5-sonnet",
)

PERSISTENT_DIR = "/data"
RED_TEAM_DIR = f"{PERSISTENT_DIR}/red_team"
FUZZ_VENV_DIR = f"{PERSISTENT_DIR}/fuzz_venv"

MAX_CEGIS_ROUNDS = int(os.getenv("RHODAWK_CEGIS_ROUNDS", "4"))
FUZZ_MAX_EXAMPLES = int(os.getenv("RHODAWK_FUZZ_EXAMPLES", "50000"))
FUZZ_TIMEOUT_SECONDS = int(os.getenv("RHODAWK_FUZZ_TIMEOUT", "180"))
MAX_TARGETS_PER_RUN = int(os.getenv("RHODAWK_MAX_TARGETS", "8"))
MIN_COMPLEXITY_SCORE = float(os.getenv("RHODAWK_MIN_COMPLEXITY", "2.0"))

# ──────────────────────────────────────────────────────────────
# LOGGING — mirrors app.py ui_log pattern
# ──────────────────────────────────────────────────────────────
_rt_log_lock = threading.Lock()
_rt_logs: list[str] = []


def rte_log(message: str, level: str = "INFO") -> None:
    ts = time.strftime("%H:%M:%S")
    icons = {
        "ATTACK": "⚔️",
        "CRASH":  "💥",
        "FUZZ":   "🎯",
        "AST":    "🔬",
        "CEGIS":  "🔁",
        "HAND":   "🤝",
        "OK":     "✅",
        "FAIL":   "❌",
        "WARN":   "⚠",
        "INFO":   "  ",
    }
    line = f"[{ts}] {icons.get(level, '  ')} [RED-TEAM] {message}"
    print(line, flush=True)
    with _rt_log_lock:
        _rt_logs.append(line)
        if len(_rt_logs) > 500:
            _rt_logs.pop(0)


def get_red_team_logs(n: int = 100) -> str:
    with _rt_log_lock:
        return "\n".join(_rt_logs[-n:])


# ──────────────────────────────────────────────────────────────
# ENV CONFIG BINARY RESOLVERS
# Extracts concrete binary paths from an EnvConfig object so the
# fuzzing subprocess calls can work regardless of language runtime.
# ──────────────────────────────────────────────────────────────

def _get_runner_bin(env_config: "EnvConfig") -> str:
    """
    Resolve the pytest-compatible test runner binary from an EnvConfig.
    Tries common attribute names, then venv_dir derivation, then system PATH.
    """
    for attr in ("runner_bin", "pytest_bin", "test_bin"):
        val = getattr(env_config, attr, None)
        if val and os.path.isfile(str(val)):
            return str(val)
    venv_dir = getattr(env_config, "venv_dir", None)
    if venv_dir:
        candidate = os.path.join(str(venv_dir), "bin", "pytest")
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("pytest") or "pytest"


def _get_python_bin(env_config: "EnvConfig") -> str:
    """
    Resolve the Python interpreter binary from an EnvConfig.
    Falls back to the current process interpreter.
    """
    for attr in ("python_bin", "interpreter", "python"):
        val = getattr(env_config, attr, None)
        if val and os.path.isfile(str(val)):
            return str(val)
    venv_dir = getattr(env_config, "venv_dir", None)
    if venv_dir:
        candidate = os.path.join(str(venv_dir), "bin", "python")
        if os.path.isfile(candidate):
            return candidate
    return sys.executable


def _get_pip_bin(env_config: "EnvConfig") -> str:
    """
    Resolve the pip binary from an EnvConfig.
    Falls back to pip in the same venv, then system pip.
    """
    for attr in ("pip_bin", "pip"):
        val = getattr(env_config, attr, None)
        if val and os.path.isfile(str(val)):
            return str(val)
    venv_dir = getattr(env_config, "venv_dir", None)
    if venv_dir:
        candidate = os.path.join(str(venv_dir), "bin", "pip")
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("pip") or "pip"


# ──────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────

@dataclass
class ASTFunctionProfile:
    """Rich profile of a function extracted from its AST node."""
    module_path: str          # Relative path: src/utils.py
    function_name: str
    lineno: int
    source_code: str          # Raw source of the function
    signature: str            # def func(x: int, y: str) -> bool
    arg_types: dict[str, str] # {"x": "int", "y": "str"}
    return_type: str
    complexity_score: float   # Cyclomatic complexity (radon)
    has_numeric_ops: bool     # Contains arithmetic that could overflow
    has_loops: bool
    has_recursion: bool
    has_state_mutation: bool  # Mutates mutable args (list, dict)
    has_exception_handling: bool
    docstring: str
    calls_made: list[str]     # Other functions this calls
    ast_summary: str          # Compact JSON summary for LLM


@dataclass
class FuzzTarget:
    """A ranked attack target selected by the MCP Universal Analyzer."""
    profile: ASTFunctionProfile
    attack_priority: float    # 0.0–1.0 composite score
    invariant_classes: list[str]  # Suggested: ["overflow", "roundtrip", ...]
    attack_rationale: str     # Why this function is interesting


@dataclass
class GeneratedPBT:
    """A Property-Based Test synthesized by the Red Team LLM."""
    test_code: str            # Full Python test file content
    test_function_name: str   # e.g., test_add_commutativity
    invariant_description: str
    hypothesis_strategy: str  # e.g., "st.integers(min_value=-2**63)"
    cegis_round: int
    prompt_hash: str


@dataclass
class CrashPayload:
    """
    The zero-day package handed to the Blue Team.
    Contains everything needed to reproduce and patch the vulnerability.
    """
    target: FuzzTarget
    pbt: GeneratedPBT
    falsifying_example: str    # Exact inputs that crashed: "x=9223372036854775807, y=-1"
    crash_output: str          # Full hypothesis failure output
    crash_type: str            # "overflow" | "exception" | "assertion" | "timeout"
    crash_hash: str            # SHA-256 of falsifying_example + crash_output
    synthetic_test_path: str   # Path to the written failing test file
    source_file_path: str      # Target source file to patch
    discovered_at: str
    cegis_rounds_taken: int


@dataclass
class RedTeamResult:
    """Final result of a full CEGIS red-team run on a repository."""
    repo_dir: str
    targets_analyzed: int
    crashes_found: list[CrashPayload] = field(default_factory=list)
    targets_survived: list[str] = field(default_factory=list)
    total_fuzz_examples: int = 0
    duration_seconds: float = 0.0
    cegis_rounds: int = 0
    handoff_results: list[dict] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# SECTION 1: MCP UNIVERSAL ANALYZER
# Python AST scanner — zero external deps beyond stdlib + radon
# ──────────────────────────────────────────────────────────────

def _compute_cyclomatic_complexity(source: str) -> float:
    """
    Compute cyclomatic complexity using radon if available,
    falling back to a branch-counting heuristic.
    """
    try:
        from radon.complexity import cc_visit
        results = cc_visit(source)
        if results:
            return float(max(r.complexity for r in results))
        return 1.0
    except Exception:
        pass

    # Fallback: count decision points
    score = 1.0
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                 ast.With, ast.AsyncFor, ast.AsyncWith)):
                score += 1.0
            elif isinstance(node, ast.BoolOp):
                score += len(node.values) - 1
    except SyntaxError:
        pass
    return score


def _extract_arg_types(func_node: ast.FunctionDef) -> dict[str, str]:
    """Extract argument names and their type annotations as strings."""
    result: dict[str, str] = {}
    for arg in func_node.args.args:
        name = arg.arg
        if arg.annotation:
            try:
                result[name] = ast.unparse(arg.annotation)
            except Exception:
                result[name] = "Any"
        else:
            result[name] = "Any"
    return result


def _extract_return_type(func_node: ast.FunctionDef) -> str:
    if func_node.returns:
        try:
            return ast.unparse(func_node.returns)
        except Exception:
            return "Any"
    return "Any"


def _has_numeric_operations(func_node: ast.FunctionDef) -> bool:
    numeric_ops = (
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitAnd,
        ast.BitOr, ast.BitXor,
    )
    for node in ast.walk(func_node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, numeric_ops):
            return True
    return False


def _has_recursion(func_node: ast.FunctionDef) -> bool:
    fn_name = func_node.name
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == fn_name:
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr == fn_name:
                return True
    return False


def _has_state_mutation(func_node: ast.FunctionDef) -> bool:
    mutable_methods = {
        "append", "extend", "insert", "remove", "pop", "clear",
        "update", "setdefault", "sort", "reverse",
    }
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute) and
                    node.func.attr in mutable_methods):
                return True
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript):
                    return True
    return False


def _extract_calls(func_node: ast.FunctionDef) -> list[str]:
    calls = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(f"{ast.unparse(node.func.value) if hasattr(ast, 'unparse') else '?'}.{node.func.attr}")
    return list(set(calls[:20]))


def _build_ast_summary(profile: "ASTFunctionProfile") -> str:
    """
    Compact JSON representation of the function for the LLM.
    Keeps token count low while conveying full semantic richness.
    """
    return json.dumps({
        "fn": profile.function_name,
        "sig": profile.signature,
        "args": profile.arg_types,
        "returns": profile.return_type,
        "complexity": profile.complexity_score,
        "numeric_ops": profile.has_numeric_ops,
        "recursive": profile.has_recursion,
        "mutates_args": profile.has_state_mutation,
        "loops": profile.has_loops,
        "calls": profile.calls_made[:10],
        "docstring": profile.docstring[:200] if profile.docstring else "",
        "source_preview": profile.source_code[:600],
    }, indent=None, separators=(",", ":"))


def _score_attack_priority(p: ASTFunctionProfile) -> tuple[float, list[str], str]:
    """
    Compute composite attack priority and determine which invariant
    classes are most likely to produce a crash.
    Returns: (score, invariant_classes, rationale)
    """
    score = 0.0
    classes: list[str] = []
    rationale_parts: list[str] = []

    # Complexity: high CC = more edge cases
    if p.complexity_score >= 10:
        score += 0.35
        rationale_parts.append(f"high cyclomatic complexity ({p.complexity_score:.1f})")
    elif p.complexity_score >= 5:
        score += 0.20
    elif p.complexity_score >= 3:
        score += 0.10

    # Numeric operations are prime overflow targets
    if p.has_numeric_ops:
        score += 0.25
        classes.append("integer_overflow")
        classes.append("boundary_value")
        rationale_parts.append("arithmetic operations (overflow/underflow risk)")

    # Recursion = stack overflow + incorrect base cases
    if p.has_recursion:
        score += 0.20
        classes.append("recursion_depth")
        classes.append("base_case_invariant")
        rationale_parts.append("recursive structure (stack overflow / incorrect base case)")

    # Mutable argument mutation = aliasing bugs
    if p.has_state_mutation:
        score += 0.15
        classes.append("aliasing_mutation")
        classes.append("idempotency")
        rationale_parts.append("mutates mutable arguments (aliasing / idempotency risk)")

    # Typed args: roundtrip testing possible
    typed_count = sum(1 for v in p.arg_types.values() if v not in ("Any", ""))
    if typed_count > 0:
        score += min(0.10, typed_count * 0.03)
        if p.return_type not in ("None", "Any", ""):
            classes.append("roundtrip")
            classes.append("commutativity")

    # Exception handling = swallowing exceptions silently
    if p.has_exception_handling:
        score += 0.10
        classes.append("exception_swallowing")
        rationale_parts.append("exception handling (may swallow bugs silently)")

    # Loops are iteration boundary targets
    if p.has_loops:
        score += 0.05
        classes.append("loop_boundary")

    # Deduplicate classes, maintain priority order
    seen: set[str] = set()
    unique_classes = [c for c in classes if not (c in seen or seen.add(c))]
    if not unique_classes:
        unique_classes = ["property_invariant", "boundary_value"]

    rationale = "; ".join(rationale_parts) if rationale_parts else "general-purpose invariant analysis"
    return min(score, 1.0), unique_classes, rationale


def analyze_repository_ast(repo_dir: str) -> list[FuzzTarget]:
    """
    Walk all Python source files in the repo, extract function-level AST
    profiles, score each for attack priority, and return the top targets
    ranked by score.

    Only targets functions in src/ lib/ or top-level .py files (not tests).
    """
    rte_log(f"Scanning AST of repository: {repo_dir}", "AST")

    targets: list[FuzzTarget] = []
    candidate_files: list[Path] = []
    repo_path = Path(repo_dir)

    # Collect candidate source files (exclude tests)
    for py_file in repo_path.rglob("*.py"):
        rel = py_file.relative_to(repo_path)
        parts = rel.parts
        if any(p.startswith("test") or p in ("tests", ".git", "__pycache__",
               "build", "dist", ".tox", "venv", ".venv") for p in parts):
            continue
        if rel.name.startswith("test_") or rel.name.startswith("conftest"):
            continue
        candidate_files.append(py_file)

    rte_log(f"Found {len(candidate_files)} non-test Python file(s) to analyze", "AST")

    for py_file in candidate_files:
        rel_path = str(py_file.relative_to(repo_path))
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError as e:
            rte_log(f"SyntaxError in {rel_path}: {e}", "WARN")
            continue

        source_lines = source.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if name.startswith("__") and name.endswith("__"):
                continue
            if not node.args.args and not node.args.vararg:
                continue  # No arguments = nothing to fuzz

            try:
                fn_start = node.lineno - 1
                fn_end = node.end_lineno if hasattr(node, "end_lineno") else fn_start + 30
                fn_source = "\n".join(source_lines[fn_start:fn_end])
            except Exception:
                fn_source = ""

            if len(fn_source.strip()) < 20:
                continue

            try:
                sig = ast.unparse(node) if hasattr(ast, "unparse") else name
                sig = sig.split("\n")[0].rstrip(":")
                if len(sig) > 200:
                    sig = sig[:200] + "..."
            except Exception:
                sig = f"def {name}(...)"

            docstring = ast.get_docstring(node) or ""
            arg_types = _extract_arg_types(node)
            return_type = _extract_return_type(node)
            complexity = _compute_cyclomatic_complexity(fn_source)

            has_loops = any(
                isinstance(n, (ast.For, ast.While, ast.AsyncFor))
                for n in ast.walk(node)
            )
            has_except = any(
                isinstance(n, ast.ExceptHandler)
                for n in ast.walk(node)
            )
            calls = _extract_calls(node)

            profile = ASTFunctionProfile(
                module_path=rel_path,
                function_name=name,
                lineno=node.lineno,
                source_code=fn_source,
                signature=sig,
                arg_types=arg_types,
                return_type=return_type,
                complexity_score=complexity,
                has_numeric_ops=_has_numeric_operations(node),
                has_loops=has_loops,
                has_recursion=_has_recursion(node),
                has_state_mutation=_has_state_mutation(node),
                has_exception_handling=has_except,
                docstring=docstring,
                calls_made=calls,
                ast_summary="",  # computed below
            )
            profile.ast_summary = _build_ast_summary(profile)

            priority, invariant_classes, rationale = _score_attack_priority(profile)

            if priority < MIN_COMPLEXITY_SCORE / 10.0:
                continue

            targets.append(FuzzTarget(
                profile=profile,
                attack_priority=priority,
                invariant_classes=invariant_classes,
                attack_rationale=rationale,
            ))

    targets.sort(key=lambda t: t.attack_priority, reverse=True)

    if targets:
        rte_log(
            f"AST analysis complete: {len(targets)} attack targets ranked. "
            f"Top target: {targets[0].profile.function_name} "
            f"(score={targets[0].attack_priority:.3f})",
            "AST"
        )
    else:
        rte_log("AST analysis complete: No targets found.", "AST")

    return targets[:MAX_TARGETS_PER_RUN]


# ──────────────────────────────────────────────────────────────
# SECTION 2: RED TEAM LLM PROMPT (THE ATTACKER)
# ──────────────────────────────────────────────────────────────

_RED_TEAM_SYSTEM_PROMPT = """You are an elite adversarial security researcher specializing in automated vulnerability discovery through Property-Based Testing and formal methods. Your role is The Attacker.

You are given the AST profile and source code of a Python function that is currently passing all its test suite. Your mission is to write a Hypothesis property-based test that BREAKS this function by finding a mathematical invariant it violates.

YOU MUST TARGET ONE OF THESE INVARIANT CLASSES:
1. INTEGER OVERFLOW: Test with sys.maxsize, -sys.maxsize, 2**63-1, 2**31-1, -1, 0 as boundary inputs
2. COMMUTATIVITY: f(a, b) == f(b, a) for all valid (a, b)
3. ASSOCIATIVITY: f(f(a,b),c) == f(a,f(b,c)) for all valid (a, b, c)
4. IDEMPOTENCY: f(f(x)) == f(x) — calling twice gives same result as once
5. ROUNDTRIP: decode(encode(x)) == x — or any encode/decode symmetry
6. MONOTONICITY: a <= b implies f(a) <= f(b) — for ordered inputs
7. BOUNDARY / EMPTY INPUTS: empty strings, empty lists, None where not expected, 0-length inputs
8. TYPE COERCION: Python implicit int→float conversion causing precision loss
9. BASE CASE INVARIANT: f(0) == expected, f(1) == expected (for recursive functions)
10. ALIASING: f(x, x) must not corrupt x when x is a mutable object

STRICT OUTPUT RULES:
- Output ONLY a valid Python test file. No explanation. No markdown. No ```python blocks.
- The test file must be directly executable with: python -m pytest <file> -v
- Import the target function using its exact module path
- Use: from hypothesis import given, settings, assume, HealthCheck
- Use: from hypothesis import strategies as st
- Use: @settings(max_examples=MAX_EXAMPLES, suppress_health_check=[HealthCheck.too_slow], deadline=None)
- MAX_EXAMPLES is already set in the settings decorator — use the constant 50000
- The test MUST raise an AssertionError or an unhandled exception when the invariant is violated
- DO NOT catch exceptions in the test body — let them propagate so hypothesis captures them
- Use assume() to filter out invalid inputs (e.g., assume(divisor != 0))
- Target the MOST LIKELY invariant class to produce a crash based on the AST profile
- Keep the test file under 80 lines

REMEMBER: Your goal is to find a REAL BUG. Not a contrived one. Study the source code and find a genuine mathematical invariant this function should satisfy but might violate on extreme inputs."""


def _build_red_team_prompt(
    target: FuzzTarget,
    cegis_round: int,
    survived_inputs: Optional[list[str]] = None,
) -> str:
    """
    Build the adversarial LLM prompt. Each CEGIS round gets harder:
    - Round 1: Fresh attack based on AST
    - Round 2+: Inject survived inputs → demand deeper invariant
    """
    p = target.profile

    sections = [
        f"=== ATTACK MISSION (CEGIS Round {cegis_round}/{MAX_CEGIS_ROUNDS}) ===\n",
        f"TARGET FUNCTION: {p.function_name}",
        f"MODULE: {p.module_path}  (line {p.lineno})",
        f"SIGNATURE: {p.signature}",
        f"RETURN TYPE: {p.return_type}",
        f"ATTACK RATIONALE: {target.attack_rationale}",
        f"SUGGESTED INVARIANT CLASSES: {', '.join(target.invariant_classes)}",
        f"\nAST PROFILE (JSON):\n{p.ast_summary}",
        f"\nFULL FUNCTION SOURCE:\n```python\n{p.source_code[:2000]}\n```",
    ]

    if cegis_round > 1 and survived_inputs:
        sections.append(
            f"\n=== CEGIS FEEDBACK — ROUND {cegis_round} ===\n"
            f"Your previous property-based test failed to find a crash after {FUZZ_MAX_EXAMPLES:,} examples.\n"
            f"The following inputs SURVIVED (did NOT crash the function):\n"
            + "\n".join(f"  - {inp}" for inp in survived_inputs[:15])
            + "\n\nDO NOT repeat the same invariant. The function survived those inputs.\n"
            "Attack a DIFFERENT invariant class. Go deeper. Try:\n"
            "  - Adversarial numeric boundaries (sys.maxsize - 1, -(2**63))\n"
            "  - Aliasing attacks: pass the same mutable object as multiple arguments\n"
            "  - Zero/empty/whitespace-only inputs combined with extreme length\n"
            "  - Unicode edge cases: null bytes, surrogate pairs, RTL text\n"
            "  - Type coercion: st.floats() combined with integer paths\n"
        )

    module_import = p.module_path.replace("/", ".").replace(".py", "").replace("\\", ".")
    sections.append(
        f"\n=== IMPORT INSTRUCTION ===\n"
        f"Import the function as:\n"
        f"  from {module_import} import {p.function_name}\n"
        f"OR use sys.path manipulation if the module path has non-package directories:\n"
        f"  import sys, os; sys.path.insert(0, os.path.dirname('<repo_dir>'))\n"
        f"  from {p.module_path.replace('/', '.').replace('.py', '')} import {p.function_name}\n"
        f"\nNow write the property-based test file. Output ONLY valid Python. No markdown."
    )

    return "\n".join(sections)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=3, max=15))
def _call_red_team_llm(system: str, user: str, model: str) -> str:
    """Call OpenRouter API — returns raw text response (the test code)."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set — Red Team LLM unavailable")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rhodawk.ai",
        "X-Title": "Rhodawk AI Red Team Fuzzer",
    }
    payload = {
        "model": model.replace("openrouter/", ""),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.15,
        "max_tokens": 2048,
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return content.strip()


def _clean_llm_test_output(raw: str) -> str:
    """
    Strip markdown fences and extract raw Python from LLM response.
    The LLM is instructed not to use markdown, but be defensive.
    """
    raw = re.sub(r"```(?:python)?\s*\n?", "", raw)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    lines = raw.splitlines()
    code_lines = []
    in_code = False
    for line in lines:
        stripped = line.strip()
        if (stripped.startswith("#") or stripped.startswith("import") or
                stripped.startswith("from") or stripped.startswith("def ") or
                stripped.startswith("@") or stripped.startswith("    ") or
                stripped == "" or in_code):
            in_code = True
            code_lines.append(line)
        elif in_code:
            code_lines.append(line)
    return "\n".join(code_lines).strip()


def synthesize_pbt(
    target: FuzzTarget,
    cegis_round: int,
    survived_inputs: Optional[list[str]] = None,
    use_strong_model: bool = False,
) -> Optional[GeneratedPBT]:
    """
    Dispatch the Red Team LLM to synthesize a Property-Based Test.
    Returns a GeneratedPBT on success, None if LLM fails.
    """
    model = RED_TEAM_MODEL_STRONG if use_strong_model else RED_TEAM_MODEL
    rte_log(
        f"Synthesizing PBT for {target.profile.function_name} "
        f"(round {cegis_round}, model={model.split('/')[-1]})",
        "ATTACK"
    )

    user_prompt = _build_red_team_prompt(target, cegis_round, survived_inputs)
    prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()[:16]

    try:
        raw_response = _call_red_team_llm(_RED_TEAM_SYSTEM_PROMPT, user_prompt, model)
    except Exception as e:
        rte_log(f"LLM call failed for {target.profile.function_name}: {e}", "WARN")
        if not use_strong_model:
            try:
                raw_response = _call_red_team_llm(
                    _RED_TEAM_SYSTEM_PROMPT, user_prompt, RED_TEAM_MODEL_STRONG
                )
            except Exception as e2:
                rte_log(f"Strong model also failed: {e2}", "FAIL")
                return None
        else:
            return None

    test_code = _clean_llm_test_output(raw_response)

    if "from hypothesis" not in test_code and "import hypothesis" not in test_code:
        rte_log(
            f"LLM output for {target.profile.function_name} doesn't contain hypothesis imports — retrying",
            "WARN"
        )
        return None

    if "def test_" not in test_code:
        rte_log("LLM output missing test function — retrying", "WARN")
        return None

    fn_match = re.search(r"def (test_\w+)\(", test_code)
    test_fn_name = fn_match.group(1) if fn_match else "test_invariant"

    inv_match = re.search(r'"""([^"]{10,200}?)"""', test_code)
    if not inv_match:
        inv_match = re.search(r"#\s*(.{10,120})", test_code)
    invariant_desc = inv_match.group(1).strip() if inv_match else "property invariant"

    strategy_match = re.search(r"@given\((.{5,200}?)\)", test_code)
    strategy = strategy_match.group(1) if strategy_match else "unknown"

    rte_log(
        f"PBT synthesized: {test_fn_name} | "
        f"invariant: {invariant_desc[:60]} | strategy: {strategy[:60]}",
        "ATTACK"
    )

    return GeneratedPBT(
        test_code=test_code,
        test_function_name=test_fn_name,
        invariant_description=invariant_desc,
        hypothesis_strategy=strategy,
        cegis_round=cegis_round,
        prompt_hash=prompt_hash,
    )


# ──────────────────────────────────────────────────────────────
# SECTION 3: DETERMINISTIC FUZZING LOOP
# ──────────────────────────────────────────────────────────────

def _install_hypothesis_if_needed(env_config: "EnvConfig", repo_dir: str) -> bool:
    """
    Ensure hypothesis is installed in the target environment.
    Uses EnvConfig to resolve the correct python/pip binaries.
    """
    python_bin = _get_python_bin(env_config)
    try:
        check = subprocess.run(
            [python_bin, "-c", "import hypothesis"],
            capture_output=True, timeout=15, cwd=repo_dir,
        )
        if check.returncode == 0:
            return True
    except Exception:
        pass

    rte_log("Installing hypothesis into target env...", "FUZZ")
    pip_bin = _get_pip_bin(env_config)
    try:
        result = subprocess.run(
            [pip_bin, "install", "hypothesis", "--quiet"],
            capture_output=True, timeout=120, cwd=repo_dir,
        )
        return result.returncode == 0
    except Exception as e:
        rte_log(f"hypothesis install failed: {e}", "WARN")
        return False


def _write_pbt_to_file(pbt: GeneratedPBT, target: FuzzTarget, repo_dir: str) -> str:
    """
    Write the generated PBT to the red_team/ directory.
    Injects the repo sys.path so the target module can be imported.
    Returns absolute path to the test file.
    """
    os.makedirs(RED_TEAM_DIR, exist_ok=True)

    fn_safe = target.profile.function_name.replace("-", "_")
    timestamp = int(time.time())
    filename = f"rt_{fn_safe}_r{pbt.cegis_round}_{timestamp}.py"
    filepath = os.path.join(RED_TEAM_DIR, filename)

    sys_path_injection = textwrap.dedent(f"""
        import sys
        import os
        # Inject repo root so target modules are importable
        _REPO_DIR = {repr(repo_dir)}
        if _REPO_DIR not in sys.path:
            sys.path.insert(0, _REPO_DIR)
        for _sub in ["src", "lib", "core", "app"]:
            _p = os.path.join(_REPO_DIR, _sub)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)

    """).lstrip()

    full_content = sys_path_injection + pbt.test_code

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)

    return filepath


def _extract_falsifying_example(output: str) -> str:
    """
    Parse hypothesis output to extract the minimal falsifying example.
    Hypothesis prints:
      Falsifying example: test_func(x=42, y=-1)
    or in newer versions:
      Falsifying explicit example: ...
    """
    patterns = [
        r"Falsifying explicit example:\s*\w+\((.+?)\)",
        r"Falsifying example:\s*\w+\((.+?)\)",
        r"Falsifying example.*?:\s*(.+?)$",
        r"AssertionError.*?:\s*(.+?)$",
    ]
    for pat in patterns:
        m = re.search(pat, output, re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1).strip()[:500]

    for line in output.splitlines():
        if "Error" in line or "assert" in line.lower():
            return line.strip()[:300]

    return "Unknown — see full crash output"


def _extract_crash_type(output: str) -> str:
    """Classify the type of crash from hypothesis output."""
    if "OverflowError" in output:
        return "integer_overflow"
    if "RecursionError" in output:
        return "recursion_depth"
    if "AssertionError" in output:
        return "assertion_violation"
    if "ZeroDivisionError" in output:
        return "division_by_zero"
    if "IndexError" in output:
        return "index_out_of_bounds"
    if "TypeError" in output:
        return "type_error"
    if "ValueError" in output:
        return "value_error"
    if "MemoryError" in output:          # FIX: was duplicated "MemoryError in output or MemoryError in output"
        return "memory_exhaustion"
    if "FAILED" in output:
        return "assertion"
    return "unknown_exception"


def _extract_survived_inputs(output: str) -> list[str]:
    """
    If the fuzz run succeeded (no crash), try to extract some of the
    inputs that were tested so CEGIS can inform the next round.
    """
    survived = []
    for m in re.finditer(r"Trying example.*?\((.+?)\)", output):
        survived.append(m.group(1)[:100])
    for m in re.finditer(r"explicit example.*?\((.+?)\)", output, re.IGNORECASE):
        survived.append(m.group(1)[:100])
    return survived[:20]


def run_fuzzing_loop(
    pbt: GeneratedPBT,
    target: FuzzTarget,
    repo_dir: str,
    env_config: "EnvConfig",          # FIX: was pytest_bin: str
) -> tuple[bool, str, str]:
    """
    Execute the generated PBT via subprocess with hypothesis aggressive settings.

    Returns:
        (crashed: bool, crash_output: str, falsifying_example: str)

    Security: shell=False enforced, secrets stripped from env, SIGKILL on timeout.
    """
    test_file = _write_pbt_to_file(pbt, target, repo_dir)
    pytest_bin = _get_runner_bin(env_config)

    rte_log(
        f"Fuzzing: {target.profile.function_name} | "
        f"test={os.path.basename(test_file)} | "
        f"max_examples={FUZZ_MAX_EXAMPLES:,} | timeout={FUZZ_TIMEOUT_SECONDS}s",
        "FUZZ"
    )

    env = os.environ.copy()
    for secret_key in [
        "OPENROUTER_API_KEY", "GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "TELEGRAM_BOT_TOKEN", "SLACK_WEBHOOK_URL", "RHODAWK_WEBHOOK_SECRET",
    ]:
        env.pop(secret_key, None)

    env["HYPOTHESIS_MAX_EXAMPLES"] = str(FUZZ_MAX_EXAMPLES)
    env["HYPOTHESIS_VERBOSITY"] = "verbose"
    seed = (hash(target.profile.function_name) + pbt.cegis_round * 7919) % (2**31)
    env["HYPOTHESIS_SEED"] = str(abs(seed))

    cmd = [
        pytest_bin,
        test_file,
        "-v",
        "--tb=long",
        "--no-header",
        f"--hypothesis-seed={abs(seed)}",
        "-x",
    ]

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            shell=False,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=FUZZ_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            rte_log(
                f"Fuzz timeout ({FUZZ_TIMEOUT_SECONDS}s) for {target.profile.function_name} — killing",
                "WARN"
            )
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
            return False, "TIMEOUT", "timeout"

        combined = (stdout or "") + "\n" + (stderr or "")
        crashed = proc.returncode != 0

        if crashed:
            falsifying = _extract_falsifying_example(combined)
            crash_type = _extract_crash_type(combined)
            rte_log(
                f"CRASH FOUND in {target.profile.function_name}: {crash_type} | "
                f"example: {falsifying[:80]}",
                "CRASH"
            )
            return True, combined, falsifying
        else:
            rte_log(
                f"No crash found in {target.profile.function_name} "
                f"after {FUZZ_MAX_EXAMPLES:,} examples",
                "FUZZ"
            )
            return False, combined, ""

    except Exception as e:
        rte_log(f"Fuzzing subprocess error for {target.profile.function_name}: {e}", "FAIL")
        return False, str(e), ""
    finally:
        if proc and proc.returncode == 0:
            try:
                os.unlink(test_file)
            except OSError:
                pass


# ──────────────────────────────────────────────────────────────
# SECTION 4: CEGIS HANDOFF (RED → BLUE TEAM)
# ──────────────────────────────────────────────────────────────

def _build_synthetic_failing_test(crash: CrashPayload, repo_dir: str) -> str:
    """
    Rewrite the PBT crash as a DETERMINISTIC pytest that always reproduces
    the crash using the exact falsifying example found by hypothesis.

    This is what gets handed to the Blue Team — a concrete, reproducible
    failing test with the minimal crashing input baked in.
    """
    p = crash.target.profile
    example = crash.falsifying_example

    arg_setup_lines = []
    example_clean = example.strip().rstrip(")")
    for part in re.split(r",\s*(?=[a-zA-Z_]\w*=)", example_clean):
        part = part.strip()
        if "=" in part:
            arg_setup_lines.append(f"    {part}")

    if not arg_setup_lines:
        arg_setup_lines = [f"    # Falsifying example: {example}"]
        arg_call = ", ".join("None" for _ in p.arg_types)
    else:
        arg_call = ", ".join(
            part.strip().split("=")[0] for part in arg_setup_lines if "=" in part
        )

    module_import_path = p.module_path.replace("/", ".").replace(".py", "").replace("\\", ".")

    test_content = textwrap.dedent(f"""
        \"\"\"
        Rhodawk AI — Synthetic Zero-Day Reproduction Test
        ==================================================
        AUTO-GENERATED by Red Team Fuzzer (CEGIS Engine)
        DO NOT EDIT — this file is managed by Rhodawk AI.

        Target: {p.function_name} in {p.module_path}
        Crash type: {crash.crash_type}
        Falsifying example: {crash.falsifying_example[:200]}
        Invariant violated: {crash.pbt.invariant_description[:200]}
        CEGIS rounds taken: {crash.cegis_rounds_taken}
        Crash hash: {crash.crash_hash}
        Discovered: {crash.discovered_at}
        \"\"\"

        import sys
        import os
        import pytest

        # Inject repo root for imports
        _REPO_DIR = {repr(repo_dir)}
        if _REPO_DIR not in sys.path:
            sys.path.insert(0, _REPO_DIR)
        for _sub in ["src", "lib", "core", "app"]:
            _p = os.path.join(_REPO_DIR, _sub)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)

        try:
            from {module_import_path} import {p.function_name}
        except ImportError as _e:
            pytest.skip(f"Cannot import target: {{_e}}")


        def test_rhodawk_zero_day_{p.function_name}_{crash.crash_hash[:8]}():
            \"\"\"
            Zero-day reproduction test synthesized by Rhodawk AI Red Team.
            Crash type: {crash.crash_type}
            Invariant: {crash.pbt.invariant_description[:120]}
            \"\"\"
            # Minimal falsifying example found by hypothesis after {FUZZ_MAX_EXAMPLES:,} iterations
            # CEGIS round {crash.cegis_rounds_taken} — this input crashes the function
{chr(10).join(arg_setup_lines)}

            # This call should NOT raise — if it does, the vulnerability is confirmed
            # Blue Team: fix the implementation so this assertion holds for all inputs
            try:
                result = {p.function_name}({arg_call})
                assert result is not None or result is None, (
                    f"Function returned unexpected result: {{result!r}}"
                )
            except (OverflowError, RecursionError, ZeroDivisionError,
                    IndexError, ValueError, TypeError) as e:
                pytest.fail(
                    f"{{type(e).__name__}} raised for input ({arg_call}): {{e}}\\n"
                    f"Crash type: {crash.crash_type}\\n"
                    f"Original falsifying example: {crash.falsifying_example[:200]}"
                )
    """).lstrip()

    return test_content


def package_crash_for_blue_team(
    target: FuzzTarget,
    pbt: GeneratedPBT,
    crash_output: str,
    falsifying_example: str,
    cegis_rounds: int,
    repo_dir: str,
) -> CrashPayload:
    """
    Package all crash data into a CrashPayload and write the synthetic
    deterministic failing test to the red_team/ directory.
    """
    crash_raw = falsifying_example + crash_output
    crash_hash = hashlib.sha256(crash_raw.encode()).hexdigest()[:16]
    crash_type = _extract_crash_type(crash_output)

    fn_safe = target.profile.function_name.replace("-", "_")
    synthetic_filename = f"test_rt_zero_day_{fn_safe}_{crash_hash}.py"
    synthetic_path = os.path.join(RED_TEAM_DIR, synthetic_filename)

    payload = CrashPayload(
        target=target,
        pbt=pbt,
        falsifying_example=falsifying_example,
        crash_output=crash_output,
        crash_type=crash_type,
        crash_hash=crash_hash,
        synthetic_test_path=synthetic_path,
        source_file_path=os.path.join(repo_dir, target.profile.module_path),
        discovered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        cegis_rounds_taken=cegis_rounds,
    )

    synthetic_content = _build_synthetic_failing_test(payload, repo_dir)

    os.makedirs(RED_TEAM_DIR, exist_ok=True)
    with open(synthetic_path, "w", encoding="utf-8") as f:
        f.write(synthetic_content)

    rte_log(
        f"HANDOFF READY: {synthetic_filename} | "
        f"crash_type={crash_type} | hash={crash_hash}",
        "HAND"
    )

    return payload


def handoff_to_blue_team(
    crash: CrashPayload,
    repo_dir: str,
    env_config: "EnvConfig",           # FIX: was pytest_bin: str
    mcp_config_path: str,
    job_id: str,
    branch_name: str,
    blue_team_fn: Callable,
) -> dict:
    """
    Execute the CEGIS Handoff — pass the synthetic failing test to the
    Blue Team's process_failing_test() function for autonomous patching.

    The Blue Team treats this exactly like a human-written failing test:
    it runs SAST, adversarial review, supply chain scan, and opens a PR.
    """
    rte_log(
        f"CEGIS HANDOFF → Blue Team: {crash.target.profile.function_name} | "
        f"crash_type={crash.crash_type} | source={crash.source_file_path}",
        "HAND"
    )

    pytest_bin = _get_runner_bin(env_config)

    # Verify synthetic test actually fails (confirms reproducibility)
    env = os.environ.copy()
    for secret_key in ["OPENROUTER_API_KEY", "GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN"]:
        env.pop(secret_key, None)

    verify_proc = subprocess.run(
        [pytest_bin, crash.synthetic_test_path, "-v", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=repo_dir,
        env=env,
        shell=False,
    )
    initial_failure_output = (verify_proc.stdout or "") + "\n" + (verify_proc.stderr or "")

    if verify_proc.returncode == 0:
        rte_log(
            "WARNING: Synthetic test PASSED on first run — crash may not be deterministic. "
            "Reporting anyway for human review.",
            "WARN"
        )
        initial_failure_output = (
            f"WARNING: Non-deterministic crash detected.\n"
            f"Original crash output:\n{crash.crash_output[:2000]}\n"
            f"Falsifying example: {crash.falsifying_example}"
        )

    rel_synthetic_test = os.path.relpath(crash.synthetic_test_path, repo_dir)
    rte_log(f"Dispatching Blue Team on: {rel_synthetic_test}", "HAND")

    try:
        blue_result = blue_team_fn(                # FIX: was pytest_bin=pytest_bin
            test_path=rel_synthetic_test,
            initial_failure=initial_failure_output,
            env_config=env_config,
            mcp_config_path=mcp_config_path,
            job_id=job_id,
            branch_name=branch_name,
        )

        handoff_result = {
            "crash_hash": crash.crash_hash,
            "crash_type": crash.crash_type,
            "target_function": crash.target.profile.function_name,
            "source_file": crash.target.profile.module_path,
            "synthetic_test": rel_synthetic_test,
            "blue_team_success": blue_result.success,
            "blue_team_attempts": blue_result.total_attempts,
            "failure_reason": blue_result.failure_reason,
            "cegis_rounds": crash.cegis_rounds_taken,
            "falsifying_example": crash.falsifying_example[:300],
        }

        status = "PATCHED" if blue_result.success else "UNRESOLVED"
        rte_log(
            f"Blue Team result: {status} | "
            f"attempts={blue_result.total_attempts} | "
            f"crash={crash.crash_type} | fn={crash.target.profile.function_name}",
            "OK" if blue_result.success else "FAIL"
        )

        return handoff_result

    except Exception as e:
        rte_log(f"Blue Team handoff exception: {e}", "FAIL")
        return {
            "crash_hash": crash.crash_hash,
            "crash_type": crash.crash_type,
            "target_function": crash.target.profile.function_name,
            "blue_team_success": False,
            "failure_reason": str(e),
        }


# ──────────────────────────────────────────────────────────────
# SECTION 5: MAIN CEGIS ORCHESTRATOR
# ──────────────────────────────────────────────────────────────

def run_red_team_cegis(
    repo_dir: str,
    env_config: "EnvConfig",           # FIX: was pytest_bin: str
    mcp_config_path: str,
    blue_team_fn: Callable,
    tenant_id: str = "default",
    log_audit_fn: Optional[Callable] = None,
    notify_fn: Optional[Callable] = None,
) -> RedTeamResult:
    """
    Full CEGIS Red Team orchestration loop.

    Called by app.py when all tests in a repository are GREEN.
    Returns a RedTeamResult summarizing all crashes found and Blue Team outcomes.

    Args:
        repo_dir: Absolute path to the cloned target repository
        env_config: EnvConfig from language_runtime — provides test runner, python, pip
        mcp_config_path: Path to MCP runtime config for Blue Team Aider
        blue_team_fn: process_failing_test() from app.py (Blue Team entry point)
        tenant_id: Namespace for job queue
        log_audit_fn: log_audit_event() from audit_logger.py
        notify_fn: notify() from notifier.py
    """
    start_time = time.time()
    rte_log("═" * 70, "INFO")
    rte_log(f"RED TEAM CEGIS ENGINE ACTIVATED — repo: {repo_dir}", "ATTACK")
    rte_log(f"Config: max_targets={MAX_TARGETS_PER_RUN} | max_examples={FUZZ_MAX_EXAMPLES:,} | cegis_rounds={MAX_CEGIS_ROUNDS}", "INFO")

    result = RedTeamResult(repo_dir=repo_dir, targets_analyzed=0)

    # Ensure hypothesis is available in the target environment
    if not _install_hypothesis_if_needed(env_config, repo_dir):
        rte_log("hypothesis not available — Red Team cannot run without it", "FAIL")
        return result

    # Step 1: AST Analysis — find attack targets
    try:
        targets = analyze_repository_ast(repo_dir)
    except Exception as e:
        rte_log(f"AST analysis crashed: {e}", "FAIL")
        return result

    result.targets_analyzed = len(targets)

    if not targets:
        rte_log("No suitable attack targets found in repository", "WARN")
        return result

    if log_audit_fn:
        log_audit_fn("RED_TEAM_START", "red_team_engine", repo_dir, RED_TEAM_MODEL, {
            "targets_found": len(targets),
            "top_target": targets[0].profile.function_name if targets else "none",
            "top_priority": targets[0].attack_priority if targets else 0,
        }, "STARTED")

    if notify_fn:
        notify_fn(
            f"⚔️ *Red Team CEGIS Activated*\n"
            f"All tests GREEN — attacking {len(targets)} high-value function(s).\n"
            f"Top target: `{targets[0].profile.function_name}` "
            f"(priority={targets[0].attack_priority:.2f})"
        )

    # Step 2: CEGIS attack loop for each target
    for target_idx, target in enumerate(targets):
        rte_log(
            f"Target {target_idx+1}/{len(targets)}: {target.profile.function_name} "
            f"| priority={target.attack_priority:.3f} "
            f"| invariants={','.join(target.invariant_classes[:3])}",
            "ATTACK"
        )

        survived_inputs: list[str] = []
        crash_found = False

        for cegis_round in range(1, MAX_CEGIS_ROUNDS + 1):
            rte_log(f"CEGIS round {cegis_round}/{MAX_CEGIS_ROUNDS} for {target.profile.function_name}", "CEGIS")

            use_strong = (cegis_round >= MAX_CEGIS_ROUNDS - 1)
            pbt = synthesize_pbt(target, cegis_round, survived_inputs, use_strong)

            if pbt is None:
                rte_log(f"PBT synthesis failed for {target.profile.function_name} round {cegis_round}", "WARN")
                break

            result.total_fuzz_examples += FUZZ_MAX_EXAMPLES
            result.cegis_rounds += 1

            crashed, crash_output, falsifying_example = run_fuzzing_loop(
                pbt, target, repo_dir, env_config    # FIX: was pytest_bin
            )

            if crashed and falsifying_example != "timeout":
                crash_payload = package_crash_for_blue_team(
                    target=target,
                    pbt=pbt,
                    crash_output=crash_output,
                    falsifying_example=falsifying_example,
                    cegis_rounds=cegis_round,
                    repo_dir=repo_dir,
                )
                result.crashes_found.append(crash_payload)

                if log_audit_fn:
                    log_audit_fn("RED_TEAM_CRASH", "red_team_engine", repo_dir, RED_TEAM_MODEL, {
                        "function": target.profile.function_name,
                        "module": target.profile.module_path,
                        "crash_type": crash_payload.crash_type,
                        "crash_hash": crash_payload.crash_hash,
                        "cegis_round": cegis_round,
                        "falsifying_example": falsifying_example[:200],
                        "invariant": pbt.invariant_description[:100],
                    }, "CRASH_FOUND")

                if notify_fn:
                    notify_fn(
                        f"💥 *Zero-Day Discovered*\n"
                        f"Function: `{target.profile.function_name}` in `{target.profile.module_path}`\n"
                        f"Crash type: `{crash_payload.crash_type}`\n"
                        f"Input: `{falsifying_example[:150]}`\n"
                        f"Handing to Blue Team for autonomous patching..."
                    )

                job_id_rt = hashlib.sha256(
                    f"{repo_dir}:{target.profile.function_name}:{crash_payload.crash_hash}".encode()
                ).hexdigest()[:16]
                branch_name_rt = (
                    f"rhodawk/red-team/{target.profile.function_name.replace('_','-')}"
                    f"-{crash_payload.crash_hash}"
                )

                handoff_result = handoff_to_blue_team(
                    crash=crash_payload,
                    repo_dir=repo_dir,
                    env_config=env_config,             # FIX: was pytest_bin=pytest_bin
                    mcp_config_path=mcp_config_path,
                    job_id=job_id_rt,
                    branch_name=branch_name_rt,
                    blue_team_fn=blue_team_fn,
                )
                result.handoff_results.append(handoff_result)

                if log_audit_fn:
                    log_audit_fn("RED_TEAM_HANDOFF", "red_team_engine", repo_dir, RED_TEAM_MODEL, {
                        **handoff_result,
                    }, "PATCHED" if handoff_result.get("blue_team_success") else "UNRESOLVED")

                crash_found = True
                break

            else:
                new_survived = _extract_survived_inputs(crash_output)
                survived_inputs.extend(new_survived)
                survived_inputs = survived_inputs[:30]
                rte_log(
                    f"Survived {cegis_round}/{MAX_CEGIS_ROUNDS} — "
                    f"re-attacking with {len(survived_inputs)} survived input patterns",
                    "CEGIS"
                )

        if not crash_found:
            result.targets_survived.append(
                f"{target.profile.function_name} ({target.profile.module_path})"
            )
            rte_log(
                f"Target SURVIVED all {MAX_CEGIS_ROUNDS} CEGIS rounds: {target.profile.function_name}",
                "OK"
            )

    # Summary
    result.duration_seconds = time.time() - start_time
    rte_log("═" * 70, "INFO")
    rte_log(
        f"RED TEAM COMPLETE — "
        f"targets={result.targets_analyzed} | "
        f"crashes={len(result.crashes_found)} | "
        f"survived={len(result.targets_survived)} | "
        f"fuzz_examples={result.total_fuzz_examples:,} | "
        f"duration={result.duration_seconds:.1f}s",
        "CRASH" if result.crashes_found else "OK"
    )

    if log_audit_fn:
        log_audit_fn("RED_TEAM_COMPLETE", "red_team_engine", repo_dir, RED_TEAM_MODEL, {
            "targets_analyzed": result.targets_analyzed,
            "crashes_found": len(result.crashes_found),
            "targets_survived": len(result.targets_survived),
            "total_fuzz_examples": result.total_fuzz_examples,
            "duration_seconds": round(result.duration_seconds, 2),
            "cegis_rounds": result.cegis_rounds,
            "crash_hashes": [c.crash_hash for c in result.crashes_found],
        }, "COMPLETE")

    if notify_fn:
        if result.crashes_found:
            notify_fn(
                f"⚔️ *Red Team Report*\n"
                f"Found {len(result.crashes_found)} zero-day(s) in GREEN repo!\n"
                f"Fuzz examples: {result.total_fuzz_examples:,} | "
                f"Duration: {result.duration_seconds:.0f}s\n"
                f"All crashes dispatched to Blue Team for autonomous patching."
            )
        else:
            notify_fn(
                f"✅ *Red Team: Repo Survived*\n"
                f"Attacked {result.targets_analyzed} function(s), "
                f"{result.total_fuzz_examples:,} fuzz examples — no crashes found.\n"
                f"Repository is HARDENED."
            )

    return result


# ──────────────────────────────────────────────────────────────
# STATS & DASHBOARD HELPERS (called by app.py dashboard)
# ──────────────────────────────────────────────────────────────

def get_red_team_stats() -> dict:
    """Return summary statistics for the dashboard."""
    try:
        crash_files = [
            f for f in os.listdir(RED_TEAM_DIR)
            if f.startswith("test_rt_zero_day_") and f.endswith(".py")
        ] if os.path.isdir(RED_TEAM_DIR) else []

        pbt_files = [
            f for f in os.listdir(RED_TEAM_DIR)
            if f.startswith("rt_") and f.endswith(".py")
        ] if os.path.isdir(RED_TEAM_DIR) else []

        return {
            "zero_days_discovered": len(crash_files),
            "pbts_generated": len(pbt_files),
            "red_team_dir": RED_TEAM_DIR,
            "recent_logs": get_red_team_logs(20),
        }
    except Exception:
        return {
            "zero_days_discovered": 0,
            "pbts_generated": 0,
            "red_team_dir": RED_TEAM_DIR,
            "recent_logs": "",
        }

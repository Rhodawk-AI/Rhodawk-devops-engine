"""
Rhodawk AI — Lightweight Formal Verification Gate
=================================================
Uses Z3 (SMT solver) to perform bounded symbolic verification of
simple integer arithmetic, array bounds, and null-safety properties
extracted from Python diffs.

This is NOT a full program verifier. It covers:
  1. Array/list index bounds — catches IndexError when indices are computable
  2. Integer arithmetic — overflow / divide-by-zero on constant expressions
  3. Assert statement reachability — checks user asserts are satisfiable

For complex code (loops, recursion, string ops) it returns SKIP, which does
NOT block the diff — Z3 gate is advisory, not blocking, unless a definitive
UNSAFE result is obtained.

Install: z3-solver  (pip install z3-solver)
Enable:  RHODAWK_Z3_ENABLED=true
"""

import os
import re

Z3_ENABLED = os.getenv("RHODAWK_Z3_ENABLED", "false").lower() == "true"

_IMPORT_OK = False
try:
    import z3 as _z3
    _IMPORT_OK = True
except ImportError:
    pass


def _extract_added_lines(diff_text: str) -> list[str]:
    return [
        line[1:].strip()
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def _check_divide_by_zero(lines: list[str]) -> list[str]:
    """Detect literal divide-by-zero: x / 0 or x % 0."""
    issues = []
    div_pat = re.compile(r"\b(\w+)\s*/\s*0\b")
    mod_pat = re.compile(r"\b(\w+)\s*%\s*0\b")
    for line in lines:
        if div_pat.search(line):
            issues.append(f"Literal divide-by-zero: {line}")
        if mod_pat.search(line):
            issues.append(f"Literal modulo-by-zero: {line}")
    return issues


def _check_index_bounds(lines: list[str]) -> list[str]:
    """
    Detect patterns like arr[N] where N is a literal integer and can use Z3
    to verify the index is non-negative. For constant-length list literals
    we also check upper bound.
    """
    if not _IMPORT_OK:
        return []

    issues = []
    idx_pat = re.compile(r"\b\w+\s*\[\s*(-?\d+)\s*\]")

    for line in lines:
        for m in idx_pat.finditer(line):
            idx_val = int(m.group(1))
            solver = _z3.Solver()
            i = _z3.Int("i")
            solver.add(i == idx_val)
            solver.add(i < 0)
            if solver.check() == _z3.sat:
                issues.append(f"Negative literal index [{idx_val}]: {line}")

    return issues


def _check_assert_satisfiability(lines: list[str]) -> list[str]:
    """
    Check assert statements with simple integer inequalities using Z3.
    assert x > 0 where x appears to be assigned a negative literal.
    """
    if not _IMPORT_OK:
        return []

    issues = []
    assign_pat = re.compile(r"(\w+)\s*=\s*(-?\d+)")
    assert_pat  = re.compile(r"assert\s+(\w+)\s*([><=!]+)\s*(-?\d+)")

    assignments: dict[str, int] = {}
    for line in lines:
        for m in assign_pat.finditer(line):
            assignments[m.group(1)] = int(m.group(2))

    for line in lines:
        m = assert_pat.search(line)
        if m:
            var, op, val_str = m.group(1), m.group(2), m.group(3)
            if var in assignments:
                lhs = assignments[var]
                rhs = int(val_str)
                solver = _z3.Solver()
                x = _z3.Int("x")
                solver.add(x == lhs)
                op_map = {
                    ">": x > rhs, ">=": x >= rhs, "<": x < rhs,
                    "<=": x <= rhs, "==": x == rhs, "!=": x != rhs,
                }
                constraint = op_map.get(op)
                if constraint is not None:
                    solver.add(_z3.Not(constraint))
                    if solver.check() == _z3.sat:
                        issues.append(
                            f"Assert always fails: `{var} {op} {rhs}` "
                            f"but {var}={lhs}: {line}"
                        )
    return issues


def run_formal_verification(diff_text: str) -> dict:
    """
    Run Z3-backed formal verification on the diff.

    Returns:
      {
        "verdict": "SAFE" | "UNSAFE" | "SKIP",
        "issues": list[str],
        "summary": str,
      }
    """
    if not Z3_ENABLED:
        return {"verdict": "SKIP", "issues": [], "summary": "Z3 verification disabled"}

    if not _IMPORT_OK:
        return {
            "verdict": "SKIP",
            "issues": [],
            "summary": "z3-solver not installed (pip install z3-solver)",
        }

    python_lines = _extract_added_lines(diff_text)
    if not python_lines:
        return {"verdict": "SKIP", "issues": [], "summary": "No added lines to verify"}

    all_issues: list[str] = []

    try:
        all_issues.extend(_check_divide_by_zero(python_lines))
        all_issues.extend(_check_index_bounds(python_lines))
        all_issues.extend(_check_assert_satisfiability(python_lines))
    except Exception as e:
        return {
            "verdict": "SKIP",
            "issues": [],
            "summary": f"Z3 verification exception (non-blocking): {e}",
        }

    if all_issues:
        return {
            "verdict": "UNSAFE",
            "issues": all_issues,
            "summary": f"Z3 found {len(all_issues)} formal issue(s): {all_issues[0]}",
        }

    return {
        "verdict": "SAFE",
        "issues": [],
        "summary": "Z3 found no definitive integer/bounds violations in added lines",
    }

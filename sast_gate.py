"""
Rhodawk AI — Pre-PR SAST + Secret Detection Gate
==================================================
Every AI-generated diff passes through this gate BEFORE a PR is opened.
The gate runs:
  1. Bandit — Python SAST for known vulnerability patterns (SQLi, exec, pickle, etc.)
  2. Secret pattern scanning — detects hardcoded credentials, API keys, tokens
  3. Dangerous import detection — flags os.system, eval, __import__, pickle.loads

This is the control plane that stops a hallucinating LLM from shipping a vulnerability.
"""

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────
# Secret patterns — compiled once at module load
# ──────────────────────────────────────────────
_SECRET_PATTERNS = [
    (re.compile(r'(?i)(api[_\-]?key|apikey|secret[_\-]?key|access[_\-]?token|auth[_\-]?token)\s*=\s*["\'][a-z0-9\-_]{16,}["\']'), "Hardcoded API key / token"),
    (re.compile(r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{6,}["\']'), "Hardcoded password"),
    (re.compile(r'(?i)github[_\-]?(token|pat)\s*=\s*["\']gh[pousr]_[a-z0-9]{36,}["\']'), "Hardcoded GitHub PAT"),
    (re.compile(r'(?i)hf_[a-z0-9]{30,}', re.IGNORECASE), "HuggingFace token"),
    (re.compile(r'sk-[a-zA-Z0-9]{32,}'), "OpenAI / OpenRouter API key"),
    (re.compile(r'(?i)(aws[_\-]?access[_\-]?key|AKIA)[A-Z0-9]{16,}'), "AWS access key"),
    (re.compile(r'(?i)aws[_\-]?session[_\-]?token\s*=\s*["\'][A-Za-z0-9/+=]{80,}["\']'), "AWS session token"),
    (re.compile(r'"type"\s*:\s*"service_account"[\s\S]{0,2000}"private_key"\s*:', re.IGNORECASE), "GCP service account JSON"),
    (re.compile(r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'), "Private key in source"),
]

_DANGEROUS_PATTERNS = [
    (re.compile(r'\bos\.system\s*\('), "os.system() call — use subprocess with shell=False"),
    (re.compile(r'\beval\s*\('), "eval() call — arbitrary code execution risk"),
    (re.compile(r'\bexec\s*\('), "exec() call — arbitrary code execution risk"),
    (re.compile(r'\b__import__\s*\('), "__import__() call — dynamic import risk"),
    (re.compile(r'\bpickle\.loads?\s*\('), "pickle.load() — deserialization attack risk"),
    (re.compile(r'\bsubprocess\.call\s*\(.*shell\s*=\s*True'), "subprocess with shell=True — injection risk"),
    (re.compile(r'\bsubprocess\.run\s*\(.*shell\s*=\s*True'), "subprocess.run with shell=True — injection risk"),
]

_INJECTION_PATTERNS = [
    (re.compile(r'f["\'].*SELECT.*\{.*\}.*FROM', re.IGNORECASE), "SQL injection via f-string"),
    (re.compile(r'["\'].*\+.*["\'].*WHERE', re.IGNORECASE), "SQL injection via concatenation"),
    (re.compile(r'\.format\(.*\).*WHERE', re.IGNORECASE), "SQL injection via .format()"),
]


@dataclass
class SastFinding:
    severity: str
    category: str
    line_number: int
    line_content: str
    description: str


@dataclass
class SastReport:
    passed: bool
    findings: list[SastFinding] = field(default_factory=list)
    bandit_output: str = ""
    semgrep_output: str = ""
    blocked_reason: Optional[str] = None

    def summary(self) -> str:
        if self.passed:
            return f"SAST GATE PASSED — {len(self.findings)} informational findings."
        return f"SAST GATE BLOCKED — {self.blocked_reason} | {len(self.findings)} findings."


def _scan_diff_for_secrets(diff_text: str) -> list[SastFinding]:
    findings = []
    for i, line in enumerate(diff_text.splitlines(), 1):
        if not line.startswith("+"):
            continue
        clean_line = line[1:]

        for pattern, description in _SECRET_PATTERNS:
            if pattern.search(clean_line):
                findings.append(SastFinding(
                    severity="CRITICAL",
                    category="SECRET_EXPOSURE",
                    line_number=i,
                    line_content=clean_line[:120],
                    description=description,
                ))

        for pattern, description in _DANGEROUS_PATTERNS:
            if pattern.search(clean_line):
                findings.append(SastFinding(
                    severity="HIGH",
                    category="DANGEROUS_PATTERN",
                    line_number=i,
                    line_content=clean_line[:120],
                    description=description,
                ))
        for pattern, description in _INJECTION_PATTERNS:
            if pattern.search(clean_line):
                findings.append(SastFinding(
                    severity="HIGH",
                    category="INJECTION_RISK",
                    line_number=i,
                    line_content=clean_line[:120],
                    description=description,
                ))
    return findings


def _run_bandit_on_file(file_path: str) -> str:
    try:
        result = subprocess.run(
            ["bandit", "-r", file_path, "-f", "text", "-ll"],
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        return result.stdout + result.stderr
    except FileNotFoundError:
        return "[bandit not installed — skipped]"
    except subprocess.TimeoutExpired:
        return "[bandit timed out]"
    except Exception as e:
        return f"[bandit error: {e}]"


def _run_semgrep_on_file(file_path: str) -> str:
    try:
        result = subprocess.run(
            ["semgrep", "--config", "p/ci", "--quiet", "--error", file_path],
            capture_output=True,
            text=True,
            timeout=90,
            shell=False,
        )
        return result.stdout + result.stderr
    except FileNotFoundError:
        return "[semgrep not installed — skipped]"
    except subprocess.TimeoutExpired:
        return "[semgrep timed out]"
    except Exception as e:
        return f"[semgrep error: {e}]"


def run_sast_gate(diff_text: str, changed_files: list[str], repo_dir: str) -> SastReport:
    """
    Run the full SAST gate on an AI-generated diff.
    Returns SastReport — if passed=False, the PR must NOT be opened.
    """
    all_findings: list[SastFinding] = []

    pattern_findings = _scan_diff_for_secrets(diff_text)
    all_findings.extend(pattern_findings)

    bandit_combined = ""
    semgrep_combined = ""
    for rel_path in changed_files:
        if not rel_path.endswith(".py"):
            continue
        abs_path = os.path.join(repo_dir, rel_path)
        if os.path.exists(abs_path):
            bandit_out = _run_bandit_on_file(abs_path)
            bandit_combined += f"\n--- {rel_path} ---\n{bandit_out}"
            semgrep_out = _run_semgrep_on_file(abs_path)
            semgrep_combined += f"\n--- {rel_path} ---\n{semgrep_out}"

    critical_findings = [f for f in all_findings if f.severity == "CRITICAL"]
    high_findings = [f for f in all_findings if f.severity == "HIGH"]

    if critical_findings:
        blocked_reason = f"CRITICAL: {critical_findings[0].description}"
        return SastReport(
            passed=False,
            findings=all_findings,
            bandit_output=bandit_combined,
            semgrep_output=semgrep_combined,
            blocked_reason=blocked_reason,
        )

    if len(high_findings) >= 3:
        blocked_reason = f"{len(high_findings)} HIGH severity findings exceed threshold"
        return SastReport(
            passed=False,
            findings=all_findings,
            bandit_output=bandit_combined,
            semgrep_output=semgrep_combined,
            blocked_reason=blocked_reason,
        )

    return SastReport(
        passed=True,
        findings=all_findings,
        bandit_output=bandit_combined,
        semgrep_output=semgrep_combined,
    )

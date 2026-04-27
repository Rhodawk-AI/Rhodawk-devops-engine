"""
SAST Orchestrator — CodeQL + Semgrep + QRS query synthesis pipeline.

Implements GAP 1 of the RHODAWK Enhancement Guide: replaces the regex-only
SSEC / Bandit-only sast_gate path with a true cross-file dataflow / taint
analysis stack and a feedback loop where the LLM synthesises new CodeQL
queries and Semgrep rules from existing findings (QRS architecture,
arXiv:2602.09774).

Returned :class:`SastResult` objects are wire-compatible with the existing
``hermes_orchestrator._dispatch_tool`` SAST consumers.

Codebase alignment:
  * Pure dataclasses + strict typing (PEP 604 unions kept off for 3.9 compat).
  * No global state mutation: all shared roots come from env vars and the
    orchestrator only mutates instance state on the engines it owns.
  * Every external command is invoked in a contained ``subprocess.run`` /
    ``subprocess.Popen`` with an explicit timeout — never ``shell=True``
    on untrusted input. CodeQL / Semgrep are themselves treated as the
    isolated sandbox surface.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

LOG = logging.getLogger("sast_orchestrator")

CODEQL_BIN     = os.getenv("CODEQL_BIN", "codeql")
SEMGREP_BIN    = os.getenv("SEMGREP_BIN", "semgrep")
CODEQL_PACKS   = os.getenv("CODEQL_PACKS_DIR", "/opt/codeql-packs")
SEMGREP_RULES  = os.getenv("SEMGREP_RULES_DIR", "/opt/semgrep-rules")
CODEQL_DB_DIR  = os.getenv("CODEQL_DB_DIR", "/data/codeql_dbs")
SAST_TIMEOUT   = int(os.getenv("SAST_TIMEOUT_SECONDS", "600"))


# ──────────────────────────────────────────────────────────────────────
# Result dataclass — wire-compatible with hermes_orchestrator consumers.
# ──────────────────────────────────────────────────────────────────────


@dataclass
class SastResult:
    """One concrete finding produced by the SAST stack."""

    tool: str            # "codeql" | "semgrep" | "bandit"
    rule_id: str
    file: str
    line: int
    message: str
    severity: str        # critical | high | medium | low
    cwe: str
    source: Optional[str] = None        # taint source (CodeQL dataflow)
    sink: Optional[str] = None          # taint sink
    path_steps: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# CodeQL engine — dataflow + custom-query support.
# ──────────────────────────────────────────────────────────────────────


class CodeQLEngine:
    """Full CodeQL CLI wrapper.

    Workflow:
      1. ``create_database`` — produce a CodeQL DB for the repo.
      2. ``run_security_queries`` — run the canonical security suite.
      3. ``run_custom_query`` — execute an LLM-generated `.ql` query
         (the QRS feedback loop).

    All sub-commands are wrapped in ``subprocess.run`` with explicit
    timeouts. SARIF parsing is defensive — malformed reports return [].
    """

    LANG_MAP: dict[str, str] = {
        "python":     "python",
        "javascript": "javascript",
        "typescript": "javascript",
        "java":       "java",
        "go":         "go",
        "c":          "cpp",
        "cpp":        "cpp",
        "c++":        "cpp",
        "ruby":       "ruby",
        "swift":      "swift",
    }

    SECURITY_QUERY_SUITES: dict[str, str] = {
        "python":     "codeql/python-queries:codeql-suites/python-security-and-quality.qls",
        "javascript": "codeql/javascript-queries:codeql-suites/javascript-security-and-quality.qls",
        "java":       "codeql/java-queries:codeql-suites/java-security-and-quality.qls",
        "cpp":        "codeql/cpp-queries:codeql-suites/cpp-security-and-quality.qls",
        "go":         "codeql/go-queries:codeql-suites/go-security-and-quality.qls",
    }

    def create_database(
        self,
        repo_path: str,
        language: str,
        db_name: str,
    ) -> Optional[str]:
        lang = self.LANG_MAP.get(language.lower())
        if not lang:
            LOG.debug("CodeQLEngine: unsupported language %s", language)
            return None
        db_path = os.path.join(CODEQL_DB_DIR, db_name)
        os.makedirs(CODEQL_DB_DIR, exist_ok=True)
        cmd = [
            CODEQL_BIN, "database", "create", db_path,
            "--language", lang,
            "--source-root", repo_path,
            "--overwrite",
        ]
        if lang in ("java", "cpp"):
            build_cmds = {
                "java": "mvn -B -DskipTests package || gradle build -x test",
                "cpp":  "make -j4 || cmake --build . || true",
            }
            cmd.extend(["--command", build_cmds.get(lang, "")])
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=SAST_TIMEOUT, cwd=repo_path,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            LOG.warning("CodeQL database creation failed: %s", exc)
            return None
        return db_path if result.returncode == 0 else None

    def run_security_queries(
        self,
        db_path: str,
        language: str,
    ) -> list[SastResult]:
        suite = self.SECURITY_QUERY_SUITES.get(self.LANG_MAP.get(language.lower(), ""))
        if not suite:
            return []
        with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False) as fh:
            sarif_path = fh.name
        cmd = [
            CODEQL_BIN, "database", "analyze", db_path,
            suite, "--format=sarifv2.1.0",
            f"--output={sarif_path}",
            "--ram=4096",
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=SAST_TIMEOUT)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            LOG.warning("CodeQL analyze failed: %s", exc)
            return []
        return self._parse_sarif(sarif_path)

    def run_custom_query(
        self,
        db_path: str,
        query_text: str,
    ) -> list[SastResult]:
        """Execute an LLM-generated CodeQL query (QRS architecture)."""
        with tempfile.NamedTemporaryFile(suffix=".ql", delete=False, mode="w") as fh:
            fh.write(query_text)
            query_path = fh.name
        with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False) as fh:
            sarif_path = fh.name
        cmd = [
            CODEQL_BIN, "query", "run", query_path,
            "--database", db_path,
            "--output", sarif_path,
            "--format", "sarifv2.1.0",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            LOG.warning("CodeQL custom query failed: %s", exc)
            return []
        if result.returncode != 0:
            return []
        return self._parse_sarif(sarif_path)

    @staticmethod
    def _parse_sarif(sarif_path: str) -> list[SastResult]:
        results: list[SastResult] = []
        try:
            with open(sarif_path, "r", encoding="utf-8") as fh:
                sarif = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return results
        try:
            for run in sarif.get("runs", []):
                rules = {
                    r["id"]: r
                    for r in run.get("tool", {}).get("driver", {}).get("rules", [])
                    if "id" in r
                }
                for finding in run.get("results", []):
                    rule_id = finding.get("ruleId", "")
                    rule = rules.get(rule_id, {})
                    severity_raw = finding.get("properties", {}).get(
                        "problem.severity", "warning"
                    )
                    severity_map = {
                        "error":          "high",
                        "warning":        "medium",
                        "recommendation": "low",
                    }
                    for location in finding.get("locations", []):
                        phys   = location.get("physicalLocation", {})
                        region = phys.get("region", {})
                        flow_steps: list[str] = []
                        for flow in finding.get("codeFlows", []):
                            for thread_flow in flow.get("threadFlows", []):
                                flow_steps = [
                                    f"{loc['location']['physicalLocation']['artifactLocation']['uri']}:"
                                    f"{loc['location']['physicalLocation']['region']['startLine']}"
                                    for loc in thread_flow.get("locations", [])
                                    if "location" in loc
                                ]
                        tags = (rule.get("properties", {}).get("tags") or []) if rule else []
                        results.append(
                            SastResult(
                                tool="codeql",
                                rule_id=rule_id,
                                file=phys.get("artifactLocation", {}).get("uri", ""),
                                line=region.get("startLine", 0),
                                message=finding.get("message", {}).get("text", ""),
                                severity=severity_map.get(severity_raw, "medium"),
                                cwe=tags[0] if tags else "",
                                path_steps=flow_steps,
                            )
                        )
        except Exception as exc:  # noqa: BLE001
            LOG.debug("SARIF parse error: %s", exc)
        return results


# ──────────────────────────────────────────────────────────────────────
# Semgrep engine — bulk OSS rules + custom rule synthesis.
# ──────────────────────────────────────────────────────────────────────


class SemgrepEngine:
    """Semgrep CLI wrapper. Runs the OSS rule packs and accepts
    LLM-generated YAML rules for the QRS feedback loop."""

    RULESETS: tuple[str, ...] = (
        "p/security-audit",
        "p/owasp-top-ten",
        "p/cwe-top-25",
        "p/secrets",
        "p/supply-chain",
    )

    LANG_EXT: dict[str, str] = {
        "python":     "py",
        "javascript": "js",
        "typescript": "ts",
        "java":       "java",
        "go":         "go",
        "ruby":       "rb",
        "rust":       "rs",
        "php":        "php",
        "c":          "c",
        "cpp":        "cpp",
    }

    def scan(
        self,
        repo_path: str,
        language: Optional[str] = None,
    ) -> list[SastResult]:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
            output_path = fh.name
        cmd = [
            SEMGREP_BIN, "scan",
            "--json", "--output", output_path,
            "--no-git-ignore",
            "--max-memory", "4096",
            "--timeout", "300",
        ]
        for ruleset in self.RULESETS:
            cmd.extend(["--config", ruleset])
        if language:
            ext = self.LANG_EXT.get(language.lower())
            if ext:
                cmd.extend(["--include", f"*.{ext}"])
        cmd.append(repo_path)
        try:
            subprocess.run(cmd, capture_output=True, timeout=SAST_TIMEOUT)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            LOG.warning("Semgrep scan failed: %s", exc)
            return []
        return self._parse_output(output_path)

    def scan_with_custom_rule(
        self,
        repo_path: str,
        rule_yaml: str,
    ) -> list[SastResult]:
        """Run a single LLM-generated Semgrep rule."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as fh:
            fh.write(rule_yaml)
            rule_path = fh.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
            output_path = fh.name
        cmd = [
            SEMGREP_BIN, "scan",
            "--json", "--output", output_path,
            "--config", rule_path,
            repo_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            LOG.warning("Semgrep custom-rule scan failed: %s", exc)
            return []
        return self._parse_output(output_path)

    @staticmethod
    def _parse_output(output_path: str) -> list[SastResult]:
        results: list[SastResult] = []
        try:
            with open(output_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return results
        sev_map = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
        for finding in data.get("results", []):
            extra = finding.get("extra", {}) or {}
            metadata = extra.get("metadata", {}) or {}
            cwe_field = metadata.get("cwe", "")
            if isinstance(cwe_field, list):
                cwe_field = cwe_field[0] if cwe_field else ""
            results.append(
                SastResult(
                    tool="semgrep",
                    rule_id=finding.get("check_id", ""),
                    file=finding.get("path", ""),
                    line=finding.get("start", {}).get("line", 0),
                    message=extra.get("message", ""),
                    severity=sev_map.get(extra.get("severity", "WARNING"), "medium"),
                    cwe=str(cwe_field),
                )
            )
        return results


# ──────────────────────────────────────────────────────────────────────
# QRS — Query/Rule synthesis from finding descriptions.
# ──────────────────────────────────────────────────────────────────────


class QRSQuerySynthesizer:
    """Generate CodeQL queries and Semgrep YAML rules from finding descriptions.

    Architecture from arXiv:2602.09774 (Feb 2026 — QRS): the LLM is treated
    as a query author, not a verdict source. Each new query / rule is fed
    back into the deterministic engines (CodeQL / Semgrep) which decide
    whether the pattern is actually present.
    """

    CODEQL_SCHEMA_PROMPT: str = (
        "You are a CodeQL security query expert. Generate a complete, compilable "
        "CodeQL query that finds the vulnerability pattern described. Follow this schema:\n"
        "\n"
        "1. Use TaintTracking::Global<Config> for dataflow vulnerabilities.\n"
        "2. Include proper import statements.\n"
        "3. Include a source predicate that identifies user-controlled inputs.\n"
        "4. Include a sink predicate that identifies dangerous operations.\n"
        "5. The query must end with a select clause.\n"
        "6. Output ONLY the CodeQL query text, no explanation.\n"
        "\n"
        "Vulnerability description: {description}\n"
        "Language: {language}\n"
        "Evidence code: {evidence}\n"
    )

    SEMGREP_SCHEMA_PROMPT: str = (
        "You are a Semgrep rule author. Generate a complete, valid Semgrep YAML "
        "rule that detects the vulnerability pattern described. The rule must:\n"
        "\n"
        "1. Have a unique rule id (use kebab-case).\n"
        "2. Set appropriate severity (ERROR/WARNING/INFO).\n"
        "3. Include metadata with cwe and owasp fields.\n"
        "4. Use patterns, pattern-either, or pattern-inside appropriately.\n"
        "5. Output ONLY valid YAML, no explanation.\n"
        "\n"
        "Vulnerability description: {description}\n"
        "Language: {language}\n"
        "Evidence code: {evidence}\n"
    )

    def synthesize_codeql_query(
        self,
        description: str,
        language: str,
        evidence: str,
        llm_fn: Callable[[str], str],
    ) -> str:
        prompt = self.CODEQL_SCHEMA_PROMPT.format(
            description=description, language=language, evidence=str(evidence)[:2000],
        )
        try:
            return llm_fn(prompt) or ""
        except Exception as exc:  # noqa: BLE001
            LOG.warning("QRS CodeQL synthesis failed: %s", exc)
            return ""

    def synthesize_semgrep_rule(
        self,
        description: str,
        language: str,
        evidence: str,
        llm_fn: Callable[[str], str],
    ) -> str:
        prompt = self.SEMGREP_SCHEMA_PROMPT.format(
            description=description, language=language, evidence=str(evidence)[:2000],
        )
        try:
            return llm_fn(prompt) or ""
        except Exception as exc:  # noqa: BLE001
            LOG.warning("QRS Semgrep synthesis failed: %s", exc)
            return ""


# ──────────────────────────────────────────────────────────────────────
# SASTOrchestrator — main entry point used by hermes_orchestrator.
# ──────────────────────────────────────────────────────────────────────


@dataclass
class _Engines:
    codeql:  CodeQLEngine
    semgrep: SemgrepEngine
    qrs:     QRSQuerySynthesizer


class SASTOrchestrator:
    """Drives Semgrep + CodeQL + QRS feedback loop. Stateless apart from
    the three engine instances it holds — safe to construct per dispatch."""

    def __init__(self) -> None:
        self._engines = _Engines(
            codeql=CodeQLEngine(),
            semgrep=SemgrepEngine(),
            qrs=QRSQuerySynthesizer(),
        )

    @property
    def codeql(self) -> CodeQLEngine:
        return self._engines.codeql

    @property
    def semgrep(self) -> SemgrepEngine:
        return self._engines.semgrep

    @property
    def qrs(self) -> QRSQuerySynthesizer:
        return self._engines.qrs

    def full_scan(
        self,
        repo_path: str,
        language: str,
        repo_name: str,
    ) -> list[SastResult]:
        """Phase 1: Semgrep (no build). Phase 2: CodeQL (deep dataflow)."""
        results: list[SastResult] = []
        results.extend(self.semgrep.scan(repo_path, language))
        db_name = repo_name.replace("/", "_") if repo_name else "anon_repo"
        db_path = self.codeql.create_database(repo_path, language, db_name)
        if db_path:
            results.extend(self.codeql.run_security_queries(db_path, language))
        return self._deduplicate(results)

    def synthesize_and_scan(
        self,
        repo_path: str,
        language: str,
        db_path: Optional[str],
        finding_description: str,
        evidence: Any,
        llm_fn: Callable[[str], str],
    ) -> list[SastResult]:
        """QRS loop: write a new Semgrep rule + CodeQL query from a finding,
        then run them and return any *new* matches."""
        evidence_str = (
            "\n".join(str(e) for e in evidence)
            if isinstance(evidence, (list, tuple))
            else str(evidence)
        )
        new_results: list[SastResult] = []

        semgrep_rule = self.qrs.synthesize_semgrep_rule(
            finding_description, language, evidence_str, llm_fn,
        )
        if semgrep_rule:
            new_results.extend(
                self.semgrep.scan_with_custom_rule(repo_path, semgrep_rule)
            )

        if db_path:
            codeql_query = self.qrs.synthesize_codeql_query(
                finding_description, language, evidence_str, llm_fn,
            )
            if codeql_query:
                new_results.extend(
                    self.codeql.run_custom_query(db_path, codeql_query)
                )

        return self._deduplicate(new_results)

    @staticmethod
    def _deduplicate(results: list[SastResult]) -> list[SastResult]:
        seen: set[tuple[str, int, str]] = set()
        deduped: list[SastResult] = []
        for r in results:
            key = (r.file, r.line, r.rule_id)
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped


__all__ = [
    "SastResult",
    "CodeQLEngine",
    "SemgrepEngine",
    "QRSQuerySynthesizer",
    "SASTOrchestrator",
]

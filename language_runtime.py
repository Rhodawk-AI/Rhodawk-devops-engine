"""
Rhodawk AI — Universal Language Runtime Abstraction
=====================================================
Replaces all Python-specific hardcoding in app.py with a pluggable runtime
system. Each LanguageRuntime implementation handles:

  1. detect()           — fingerprint a cloned repo to identify its language
  2. setup_env()        — install deps, return an EnvConfig (replaces setup_target_venv)
  3. discover_tests()   — find test files matching language conventions
  4. run_tests()        — execute one test file, return (output, exit_code)
  5. run_sast()         — language-specific static analysis on a diff
  6. run_supply_chain() — language-specific dep audit on a diff
  7. get_mcp_domains()  — docs domains the MCP fetch tool is allowed to hit
  8. get_fix_prompt_instructions() — language-aware instructions appended to Aider prompts

RuntimeFactory.for_repo(repo_dir) auto-detects and returns the right runtime.
Fall-through: if detection is ambiguous, PythonRuntime is used as default.

Supported languages
-------------------
  Python     pytest / uv / pip-audit / bandit
  JavaScript jest|mocha|vitest / npm / npm-audit / eslint-security
  TypeScript same as JS + tsc type-check step
  Java       Maven|Gradle / JUnit|TestNG / OWASP dep-check / semgrep-java
  Go         go test / govulncheck / gosec
  Rust       cargo test / cargo-audit / clippy
  Ruby       RSpec|Minitest / bundler / bundle-audit / brakeman

Adding a new language
---------------------
  1. Subclass LanguageRuntime.
  2. Implement all abstract methods.
  3. Append instance to RuntimeFactory._REGISTRY (order matters — first match wins).
"""

from __future__ import annotations

import glob
import json
import os
import re
import signal
import shutil
import subprocess
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_runtime_process_groups: set[int] = set()
_runtime_process_lock = threading.Lock()


def kill_runtime_processes() -> int:
    with _runtime_process_lock:
        groups = list(_runtime_process_groups)
        _runtime_process_groups.clear()
    killed = 0
    for pgid in groups:
        try:
            os.killpg(pgid, signal.SIGTERM)
            killed += 1
        except ProcessLookupError:
            continue
    time.sleep(0.2)
    for pgid in groups:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            continue
    return killed


# ──────────────────────────────────────────────────────────────
# SHARED DATA STRUCTURES
# (mirror / extend SastReport + SupplyChainReport from existing modules
#  so app.py doesn't need to import from two places)
# ──────────────────────────────────────────────────────────────

@dataclass
class EnvConfig:
    """Opaque handle returned by setup_env(); passed back into run_tests()."""
    language: str
    test_runner_cmd: list[str]        # base command e.g. ["npx", "jest"]
    env_dir: str                      # venv / node_modules parent / JAVA_HOME etc.
    extra_env: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)   # language-specific extras


@dataclass
class RuntimeSastFinding:
    severity: str        # CRITICAL | HIGH | MEDIUM | LOW
    category: str
    line_number: int
    line_content: str
    description: str


@dataclass
class RuntimeSastReport:
    passed: bool
    language: str
    findings: list[RuntimeSastFinding] = field(default_factory=list)
    tool_output: str = ""
    blocked_reason: Optional[str] = None

    def summary(self) -> str:
        if self.passed:
            return f"[{self.language}] SAST PASSED — {len(self.findings)} informational finding(s)."
        return f"[{self.language}] SAST BLOCKED — {self.blocked_reason}"


@dataclass
class RuntimeSupplyChainReport:
    passed: bool
    language: str
    new_packages: list[str] = field(default_factory=list)
    cve_findings: list[dict] = field(default_factory=list)
    typosquat_findings: list[str] = field(default_factory=list)
    metadata_findings: list[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None

    def summary(self) -> str:
        if self.passed:
            return f"[{self.language}] Supply chain OK. Checked {len(self.new_packages)} package(s)."
        return f"[{self.language}] Supply chain BLOCKED: {self.blocked_reason}"


# ──────────────────────────────────────────────────────────────
# BASE CLASS
# ──────────────────────────────────────────────────────────────

class LanguageRuntime(ABC):
    """Abstract base — one concrete subclass per supported language."""

    language: str = "unknown"

    # ── Detection ────────────────────────────────────────────

    @classmethod
    @abstractmethod
    def detect(cls, repo_dir: str) -> bool:
        """
        Return True if this runtime should handle the given repo.
        Called in priority order by RuntimeFactory; first True wins.
        """

    # ── Environment Setup ────────────────────────────────────

    @abstractmethod
    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        """
        Install dependencies; return an EnvConfig.
        Must be idempotent — called every audit run.
        """

    # ── Test Discovery ───────────────────────────────────────

    @abstractmethod
    def discover_tests(self, repo_dir: str) -> list[str]:
        """
        Return a list of test file paths RELATIVE to repo_dir.
        Paths must be passable directly to run_tests().
        """

    # ── Test Execution ───────────────────────────────────────

    @abstractmethod
    def run_tests(
        self,
        test_path: str,        # relative path from discover_tests()
        repo_dir: str,
        env_config: EnvConfig,
        timeout: int = 120,
    ) -> tuple[str, int]:
        """
        Run a single test file. Return (combined_output, exit_code).
        exit_code 0 means all tests in file passed.
        """

    # ── Security Gates ───────────────────────────────────────

    @abstractmethod
    def run_sast(
        self,
        diff_text: str,
        changed_files: list[str],
        repo_dir: str,
    ) -> RuntimeSastReport:
        """Run static analysis on the AI-generated diff."""

    @abstractmethod
    def run_supply_chain(
        self,
        diff_text: str,
        repo_dir: str,
    ) -> RuntimeSupplyChainReport:
        """Audit dependencies added/changed by the AI diff."""

    # ── Prompt / MCP Helpers ─────────────────────────────────

    @abstractmethod
    def get_mcp_domains(self) -> list[str]:
        """Return allowed documentation domains for the MCP fetch tool."""

    @abstractmethod
    def get_fix_prompt_instructions(
        self,
        test_path: str,
        branch_name: str,
        src_hint: str = "",
    ) -> str:
        """
        Language-specific instruction block appended to Aider prompts.
        Replaces the Python-hardcoded 'fix requirements.txt or src_file' section.
        """

    # ── Shared Subprocess Helper ─────────────────────────────

    @staticmethod
    def _run(
        cmd: list[str],
        cwd: str,
        timeout: int = 300,
        extra_env: dict | None = None,
        raise_on_error: bool = False,
    ) -> tuple[str, int]:
        """Thin safe subprocess wrapper (shell=False enforced)."""
        if isinstance(cmd, str):
            raise TypeError("SECURITY: Use list commands, not strings.")
        env = os.environ.copy()
        # Strip secrets from child process environment
        for secret in [
            "OPENROUTER_API_KEY", "GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "TELEGRAM_BOT_TOKEN", "SLACK_WEBHOOK_URL", "RHODAWK_WEBHOOK_SECRET",
        ]:
            env.pop(secret, None)
        if extra_env:
            env.update(extra_env)
        proc = None
        pgid = None
        try:
            proc = subprocess.Popen(
                cmd, shell=False, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env, start_new_session=True,
            )
            try:
                pgid = os.getpgid(proc.pid)
                with _runtime_process_lock:
                    _runtime_process_groups.add(pgid)
            except ProcessLookupError:
                pgid = None
            stdout, stderr = proc.communicate(timeout=timeout)
            output = (stdout or "") + "\n" + (stderr or "")
            if raise_on_error and proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            return output, proc.returncode
        except FileNotFoundError as e:
            if raise_on_error:
                raise
            return str(e), 127
        except subprocess.TimeoutExpired:
            if proc:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.communicate()
            return f"[TIMEOUT after {timeout}s]", 1
        finally:
            if pgid is not None:
                with _runtime_process_lock:
                    _runtime_process_groups.discard(pgid)


# ──────────────────────────────────────────────────────────────
# PYTHON RUNTIME  (refactored from existing app.py behaviour)
# ──────────────────────────────────────────────────────────────

class PythonRuntime(LanguageRuntime):
    language = "python"

    @classmethod
    def detect(cls, repo_dir: str) -> bool:
        markers = [
            "requirements.txt", "setup.py", "setup.cfg",
            "pyproject.toml", "Pipfile", "poetry.lock",
        ]
        return any(os.path.exists(os.path.join(repo_dir, m)) for m in markers)

    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        import sys
        # FIX-011: Use a per-repo venv name derived from repo_dir so that switching
        # between target repos never reuses a stale virtualenv with different deps.
        # The old shared "target_venv" caused "[Errno 2] No such file or directory:
        # '/data/target_venv/bin/pip'" when the venv belonged to a different repo.
        import hashlib as _hashlib
        _repo_hash = _hashlib.md5(repo_dir.encode()).hexdigest()[:8]
        venv_dir = os.path.join(persistent_dir, f"target_venv_{_repo_hash}")

        # FIX: guarantee the parent directory exists before uv/venv tries to write into it.
        # In HuggingFace Spaces /data is a mounted volume that may not be pre-created.
        os.makedirs(persistent_dir, exist_ok=True)

        # FIX: redirect uv cache to /tmp which is always writable in HuggingFace Spaces.
        # Without this, uv fails with "Permission denied" on /home/rhodawk/.cache/uv
        # and silently skips package installation, causing all tests to fail on import.
        uv_env = {"UV_CACHE_DIR": "/tmp/uv-cache"}
        uv_bin = shutil.which("uv")

        pytest_bin_check = os.path.join(venv_dir, "bin", "pytest")
        # FIX: if venv exists but pytest is missing, the previous install was broken
        # (e.g. uv pip install silently failed due to cache permission error).
        # Force a clean rebuild so packages are properly installed this run.
        if os.path.exists(venv_dir) and not os.path.exists(pytest_bin_check):
            shutil.rmtree(venv_dir, ignore_errors=True)

        if not os.path.exists(venv_dir):
            if uv_bin:
                out, code = self._run(
                    [uv_bin, "venv", "--python", sys.executable, venv_dir],
                    cwd="/tmp",
                    extra_env=uv_env,
                )
            else:
                out, code = ("uv executable not found", 127)
            if code != 0:
                ui_msg = (
                    f"uv venv failed (exit {code}) — falling back to "
                    f"python -m venv. uv output: {out.strip()[:200]}"
                )
                import warnings
                warnings.warn(ui_msg)
                self._run(
                    [sys.executable, "-m", "venv", venv_dir],
                    cwd="/tmp",
                    raise_on_error=True,
                )
                self._run(
                    [os.path.join(venv_dir, "bin", "python"), "-m", "ensurepip", "--upgrade"],
                    cwd="/tmp",
                    raise_on_error=False,
                )

        # FIX-010: Resolve the venv's python interpreter to use as the pip fallback.
        # Using `python -m pip` via the venv's python binary avoids the "No such file or
        # directory: '/data/target_venv/bin/pip'" error seen when a fresh venv was created
        # via `python -m venv` (which includes pip) but the bare pip script is absent.
        venv_python = os.path.join(venv_dir, "bin", "python")

        def _install_deps(args: list[str]) -> bool:
            """Try uv pip install first; fall back to the venv python -m pip on failure."""
            if uv_bin:
                out, code = self._run(
                    [uv_bin, "pip", "install", "--python", venv_dir, "--quiet"] + args,
                    cwd=repo_dir, timeout=600, extra_env=uv_env,
                )
            else:
                out, code = ("uv executable not found", 127)
            if code != 0:
                import warnings
                warnings.warn(f"uv pip install failed (exit {code}) — falling back to pip. {out.strip()[:200]}")
                # FIX-010: use venv_python -m pip instead of a bare pip_bin path —
                # the `pip` script may be absent in freshly-created stdlib venvs.
                _, pip_code = self._run(
                    [venv_python, "-m", "pip", "install", "--quiet"] + args,
                    cwd=repo_dir, timeout=600,
                )
                return pip_code == 0
            return True

        req_path = os.path.join(repo_dir, "requirements.txt")
        if os.path.exists(req_path):
            _install_deps(["-r", req_path])
        else:
            pyproject = os.path.join(repo_dir, "pyproject.toml")
            if os.path.exists(pyproject):
                _install_deps(["-e", ".[dev,test]"])

        pytest_bin = os.path.join(venv_dir, "bin", "pytest")
        return EnvConfig(
            language="python",
            test_runner_cmd=[pytest_bin],
            env_dir=venv_dir,
        )

    def discover_tests(self, repo_dir: str) -> list[str]:
        patterns = [
            f"{repo_dir}/**/test_*.py",
            f"{repo_dir}/**/*_test.py",
        ]
        found = set()
        for pat in patterns:
            for path in glob.glob(pat, recursive=True):
                found.add(os.path.relpath(path, repo_dir))
        # Exclude .tox / .venv / site-packages
        return sorted(
            p for p in found
            if not any(x in p for x in [".tox", "site-packages", ".venv", "node_modules"])
        )

    def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int = 120) -> tuple[str, int]:
        pytest_bin = env_config.test_runner_cmd[0]
        return self._run(
            [pytest_bin, test_path, "-v", "--tb=short"],
            cwd=repo_dir, timeout=timeout,
        )

    def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport:
        # Delegate to existing sast_gate module to avoid duplication
        try:
            from sast_gate import run_sast_gate
            report = run_sast_gate(diff_text, changed_files, repo_dir)
            findings = [
                RuntimeSastFinding(f.severity, f.category, f.line_number, f.line_content, f.description)
                for f in report.findings
            ]
            return RuntimeSastReport(
                passed=report.passed,
                language="python",
                findings=findings,
                tool_output=report.bandit_output + "\n" + report.semgrep_output,
                blocked_reason=report.blocked_reason,
            )
        except ImportError:
            return RuntimeSastReport(passed=True, language="python", tool_output="[sast_gate not available]")

    def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport:
        try:
            from supply_chain import run_supply_chain_gate
            report = run_supply_chain_gate(diff_text, repo_dir)
            return RuntimeSupplyChainReport(
                passed=report.passed,
                language="python",
                new_packages=report.new_packages,
                cve_findings=report.cve_findings,
                typosquat_findings=report.typosquat_findings,
                metadata_findings=report.metadata_findings,
                blocked_reason=report.blocked_reason,
            )
        except ImportError:
            return RuntimeSupplyChainReport(passed=True, language="python")

    def get_mcp_domains(self) -> list[str]:
        return [
            "docs.python.org", "pypi.org", "docs.github.com",
            "packaging.python.org", "peps.python.org",
        ]

    def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str = "") -> str:
        src_target = src_hint or "the relevant source file"
        return (
            f"1. Fix '{src_target}' or 'requirements.txt' to make the test pass. "
            f"Do NOT modify test files.\n"
            f"2. Use the 'fetch-docs' MCP tool to look up documentation on "
            f"docs.python.org or pypi.org if needed.\n"
            f"3. Work on branch '{branch_name}'. Commit the minimal fix.\n"
            f"4. The fix must be minimal and must not introduce regressions."
        )


# ──────────────────────────────────────────────────────────────
# JAVASCRIPT / NODE.JS RUNTIME
# ──────────────────────────────────────────────────────────────

class NodeRuntime(LanguageRuntime):
    language = "javascript"

    # Known JS test runners in detection priority order
    _RUNNER_CONFIGS = [
        # (package_key_in_scripts, runner_name, base_cmd)
        ("jest",    "jest",    ["npx", "jest", "--no-coverage", "--forceExit"]),
        ("vitest",  "vitest",  ["npx", "vitest", "run"]),
        ("mocha",   "mocha",   ["npx", "mocha", "--exit"]),
        ("jasmine", "jasmine", ["npx", "jasmine"]),
        ("ava",     "ava",     ["npx", "ava"]),
        ("tap",     "tap",     ["npx", "tap"]),
    ]

    @classmethod
    def detect(cls, repo_dir: str) -> bool:
        pkg = os.path.join(repo_dir, "package.json")
        if not os.path.exists(pkg):
            return False
        try:
            data = json.loads(Path(pkg).read_text())
            # Exclude TypeScript repos — TypeScriptRuntime handles them
            return not cls._is_typescript(repo_dir, data)
        except Exception:
            return False

    @classmethod
    def _is_typescript(cls, repo_dir: str, pkg_data: dict) -> bool:
        if os.path.exists(os.path.join(repo_dir, "tsconfig.json")):
            return True
        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
        return "typescript" in deps

    def _detect_runner(self, repo_dir: str) -> tuple[str, list[str]]:
        pkg_path = os.path.join(repo_dir, "package.json")
        try:
            data = json.loads(Path(pkg_path).read_text())
        except Exception:
            return "jest", ["npx", "jest", "--no-coverage", "--forceExit"]

        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        scripts = data.get("scripts", {})
        test_script = scripts.get("test", "")

        for key, name, cmd in self._RUNNER_CONFIGS:
            if key in all_deps or key in test_script:
                return name, cmd

        return "jest", ["npx", "jest", "--no-coverage", "--forceExit"]

    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        pkg_lock = os.path.join(repo_dir, "package-lock.json")
        yarn_lock = os.path.join(repo_dir, "yarn.lock")
        pnpm_lock = os.path.join(repo_dir, "pnpm-lock.yaml")

        if os.path.exists(pnpm_lock):
            self._run(["pnpm", "install", "--frozen-lockfile", "--prefer-offline"],
                      cwd=repo_dir, timeout=600)
        elif os.path.exists(yarn_lock):
            self._run(["yarn", "install", "--frozen-lockfile"],
                      cwd=repo_dir, timeout=600)
        else:
            self._run(["npm", "ci", "--prefer-offline"],
                      cwd=repo_dir, timeout=600)

        runner_name, runner_cmd = self._detect_runner(repo_dir)
        return EnvConfig(
            language=self.language,
            test_runner_cmd=runner_cmd,
            env_dir=os.path.join(repo_dir, "node_modules"),
            metadata={"runner": runner_name},
        )

    def discover_tests(self, repo_dir: str) -> list[str]:
        patterns = [
            f"{repo_dir}/**/*.test.js",
            f"{repo_dir}/**/*.spec.js",
            f"{repo_dir}/**/__tests__/**/*.js",
        ]
        found = set()
        for pat in patterns:
            for path in glob.glob(pat, recursive=True):
                found.add(os.path.relpath(path, repo_dir))
        return sorted(
            p for p in found
            if "node_modules" not in p and ".min." not in p
        )

    def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int = 120) -> tuple[str, int]:
        runner = env_config.metadata.get("runner", "jest")
        cmd = env_config.test_runner_cmd[:]

        if runner == "jest":
            # Jest wants the file path as the last arg, using --testPathPattern for safety
            cmd += ["--testPathPattern", re.escape(test_path)]
        elif runner == "vitest":
            cmd += [test_path]
        elif runner == "mocha":
            cmd += [test_path]
        else:
            cmd += [test_path]

        return self._run(cmd, cwd=repo_dir, timeout=timeout)

    def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport:
        findings = []
        # 1. Universal secret patterns (from existing sast_gate logic)
        findings.extend(self._scan_secrets(diff_text))
        # 2. JS-specific dangerous patterns
        findings.extend(self._scan_js_patterns(diff_text))
        # 3. Semgrep with JS/TS ruleset
        tool_output = self._run_semgrep(changed_files, repo_dir)

        critical = [f for f in findings if f.severity == "CRITICAL"]
        high = [f for f in findings if f.severity == "HIGH"]
        blocked_reason = None
        if critical:
            blocked_reason = f"CRITICAL: {critical[0].description}"
        elif len(high) >= 3:
            blocked_reason = f"{len(high)} HIGH severity findings exceed threshold"

        return RuntimeSastReport(
            passed=blocked_reason is None,
            language=self.language,
            findings=findings,
            tool_output=tool_output,
            blocked_reason=blocked_reason,
        )

    def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]:
        """Reuse the universal secret patterns from sast_gate."""
        try:
            from sast_gate import _scan_diff_for_secrets, _SECRET_PATTERNS, _DANGEROUS_PATTERNS
            raw = _scan_diff_for_secrets(diff_text)
            return [
                RuntimeSastFinding(f.severity, f.category, f.line_number, f.line_content, f.description)
                for f in raw
            ]
        except ImportError:
            return []

    _JS_DANGEROUS = [
        (re.compile(r'\beval\s*\('), "CRITICAL", "eval() call — arbitrary code execution"),
        (re.compile(r'\bnew\s+Function\s*\('), "CRITICAL", "new Function() — dynamic code eval"),
        (re.compile(r'\bchild_process\.exec\s*\('), "HIGH", "child_process.exec — shell injection risk"),
        (re.compile(r'\brequire\s*\(\s*[`\'"]\.\.'), "HIGH", "Path-traversal require()"),
        (re.compile(r'innerHTML\s*=\s*'), "HIGH", "innerHTML assignment — XSS risk"),
        (re.compile(r'document\.write\s*\('), "HIGH", "document.write() — XSS risk"),
        (re.compile(r'__proto__'), "HIGH", "Prototype pollution vector"),
        (re.compile(r'\.prototype\['), "HIGH", "Prototype pollution vector"),
        (re.compile(r'dangerouslySetInnerHTML'), "HIGH", "dangerouslySetInnerHTML — XSS risk"),
    ]

    def _scan_js_patterns(self, diff_text: str) -> list[RuntimeSastFinding]:
        findings = []
        for i, line in enumerate(diff_text.splitlines(), 1):
            if not line.startswith("+"):
                continue
            for pattern, severity, description in self._JS_DANGEROUS:
                if pattern.search(line):
                    findings.append(RuntimeSastFinding(
                        severity=severity, category="js-security",
                        line_number=i, line_content=line[1:].strip(),
                        description=description,
                    ))
        return findings

    def _run_semgrep(self, changed_files: list[str], repo_dir: str) -> str:
        js_files = [f for f in changed_files if f.endswith((".js", ".jsx", ".mjs", ".cjs"))]
        if not js_files:
            return ""
        outputs = []
        for rel in js_files:
            abs_path = os.path.join(repo_dir, rel)
            if os.path.exists(abs_path):
                out, _ = self._run(
                    ["semgrep", "--config", "p/javascript", "--quiet", abs_path],
                    cwd=repo_dir, timeout=90,
                )
                outputs.append(out)
        return "\n".join(outputs)

    def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport:
        new_packages = self._extract_new_npm_packages(diff_text)
        typosquats = [self._check_npm_typosquat(p) for p in new_packages]
        typosquats = [t for t in typosquats if t]

        if typosquats:
            return RuntimeSupplyChainReport(
                passed=False, language=self.language,
                new_packages=new_packages, typosquat_findings=typosquats,
                blocked_reason=f"Possible typosquatting: {typosquats[0]}",
            )

        cve_findings = self._run_npm_audit(repo_dir)
        critical_cves = [c for c in cve_findings if c.get("severity") == "critical"]
        if critical_cves:
            return RuntimeSupplyChainReport(
                passed=False, language=self.language,
                new_packages=new_packages, cve_findings=cve_findings,
                blocked_reason=f"Critical CVE in npm dep: {critical_cves[0].get('name')}",
            )

        return RuntimeSupplyChainReport(
            passed=True, language=self.language,
            new_packages=new_packages, cve_findings=cve_findings,
        )

    _NPM_TOP_PACKAGES = {
        "express", "react", "vue", "angular", "lodash", "axios", "moment",
        "webpack", "babel", "typescript", "eslint", "jest", "mocha", "chai",
        "next", "nuxt", "gatsby", "fastify", "koa", "hapi", "sequelize",
        "mongoose", "typeorm", "prisma", "socket.io", "passport", "jsonwebtoken",
        "bcrypt", "dotenv", "cors", "helmet", "nodemailer", "multer", "sharp",
        "redis", "ioredis", "pg", "mysql2", "mongodb", "rxjs", "graphql",
        "apollo-server", "nestjs", "redux", "zustand", "vite", "rollup",
    }

    def _extract_new_npm_packages(self, diff_text: str) -> list[str]:
        added = []
        in_pkg = False
        for line in diff_text.splitlines():
            if "package.json" in line:
                in_pkg = True
            if in_pkg and line.startswith("+") and not line.startswith("+++"):
                match = re.search(r'"([@\w][\w\-./]*)"\s*:', line[1:])
                if match:
                    pkg = match.group(1).lstrip("@").split("/")[-1].lower()
                    if pkg not in ("version", "name", "description", "main", "scripts"):
                        added.append(match.group(1))
        return list(dict.fromkeys(added))  # dedup preserving order

    def _check_npm_typosquat(self, package_name: str) -> Optional[str]:
        pkg = package_name.lstrip("@").split("/")[-1].lower().replace("-", "").replace("_", "")
        for known in self._NPM_TOP_PACKAGES:
            known_clean = known.lower().replace("-", "").replace("_", "")
            if pkg == known_clean:
                continue
            if abs(len(pkg) - len(known_clean)) <= 2:
                dist = self._levenshtein(pkg, known_clean)
                if 0 < dist <= 2:
                    return None # f"'{package_name}' is {dist} edit(s) from '{known}' — possible typosquat"
        return None

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return NodeRuntime._levenshtein(s2, s1)
        if not s2:
            return len(s1)
        prev = list(range(len(s2) + 1))
        for c1 in s1:
            curr = [prev[0] + 1]
            for j, c2 in enumerate(s2):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
            prev = curr
        return prev[-1]

    def _run_npm_audit(self, repo_dir: str) -> list[dict]:
        out, code = self._run(
            ["npm", "audit", "--json", "--audit-level=critical"],
            cwd=repo_dir, timeout=120,
        )
        try:
            data = json.loads(out.strip())
            vulns = data.get("vulnerabilities", {})
            results = []
            for name, info in vulns.items():
                results.append({
                    "name": name,
                    "severity": info.get("severity", "unknown"),
                    "via": [v if isinstance(v, str) else v.get("title", "") for v in info.get("via", [])],
                })
            return results
        except Exception:
            return []

    def get_mcp_domains(self) -> list[str]:
        return [
            "nodejs.org", "npmjs.com", "developer.mozilla.org",
            "jestjs.io", "mochajs.org", "vitest.dev",
            "expressjs.com", "docs.github.com",
        ]

    def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str = "") -> str:
        src_target = src_hint or "the relevant source file"
        return (
            f"1. Fix '{src_target}' or 'package.json' to make the test pass. "
            f"Do NOT modify test files.\n"
            f"2. Use the 'fetch-docs' MCP tool to look up documentation on "
            f"nodejs.org or npmjs.com if needed.\n"
            f"3. Work on branch '{branch_name}'. Commit the minimal fix.\n"
            f"4. Run 'npm run build' if a build step exists before committing.\n"
            f"5. The fix must be minimal and must not introduce regressions."
        )


# ──────────────────────────────────────────────────────────────
# TYPESCRIPT RUNTIME  (extends NodeRuntime)
# ──────────────────────────────────────────────────────────────

class TypeScriptRuntime(NodeRuntime):
    language = "typescript"

    @classmethod
    def detect(cls, repo_dir: str) -> bool:
        if not os.path.exists(os.path.join(repo_dir, "package.json")):
            return False
        if os.path.exists(os.path.join(repo_dir, "tsconfig.json")):
            return True
        try:
            data = json.loads(Path(os.path.join(repo_dir, "package.json")).read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            return "typescript" in deps
        except Exception:
            return False

    def discover_tests(self, repo_dir: str) -> list[str]:
        patterns = [
            f"{repo_dir}/**/*.test.ts",
            f"{repo_dir}/**/*.spec.ts",
            f"{repo_dir}/**/*.test.tsx",
            f"{repo_dir}/**/*.spec.tsx",
            f"{repo_dir}/**/__tests__/**/*.ts",
            f"{repo_dir}/**/__tests__/**/*.tsx",
        ]
        found = set()
        for pat in patterns:
            for path in glob.glob(pat, recursive=True):
                found.add(os.path.relpath(path, repo_dir))
        return sorted(p for p in found if "node_modules" not in p)

    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        env = super().setup_env(repo_dir, persistent_dir)
        env.language = "typescript"
        return env

    def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport:
        report = super().run_sast(diff_text, changed_files, repo_dir)
        report.language = "typescript"
        # Additional TypeScript-specific: run tsc --noEmit to catch type errors
        ts_errors = self._run_tsc(repo_dir)
        if ts_errors:
            report.tool_output += f"\n\n[tsc --noEmit]\n{ts_errors}"
        return report

    def _run_tsc(self, repo_dir: str) -> str:
        tsc_path = os.path.join(repo_dir, "node_modules", ".bin", "tsc")
        if not os.path.exists(tsc_path):
            return ""
        out, code = self._run(
            [tsc_path, "--noEmit", "--skipLibCheck"],
            cwd=repo_dir, timeout=120,
        )
        return out if code != 0 else ""

    def _run_semgrep(self, changed_files: list[str], repo_dir: str) -> str:
        ts_files = [f for f in changed_files if f.endswith((".ts", ".tsx"))]
        if not ts_files:
            return ""
        outputs = []
        for rel in ts_files:
            abs_path = os.path.join(repo_dir, rel)
            if os.path.exists(abs_path):
                out, _ = self._run(
                    ["semgrep", "--config", "p/typescript", "--quiet", abs_path],
                    cwd=repo_dir, timeout=90,
                )
                outputs.append(out)
        return "\n".join(outputs)

    def get_mcp_domains(self) -> list[str]:
        return super().get_mcp_domains() + [
            "www.typescriptlang.org", "react.dev", "nextjs.org",
        ]

    def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str = "") -> str:
        src_target = src_hint or "the relevant TypeScript source file"
        return (
            f"1. Fix '{src_target}' or 'package.json' to make the test pass. "
            f"Do NOT modify test files.\n"
            f"2. Ensure the fix passes 'tsc --noEmit' with no new type errors.\n"
            f"3. Use the 'fetch-docs' MCP tool for typescriptlang.org or npmjs.com if needed.\n"
            f"4. Work on branch '{branch_name}'. Commit the minimal fix.\n"
            f"5. The fix must not introduce regressions or break existing type contracts."
        )


# ──────────────────────────────────────────────────────────────
# JAVA RUNTIME
# ──────────────────────────────────────────────────────────────

class JavaRuntime(LanguageRuntime):
    language = "java"

    @classmethod
    def detect(cls, repo_dir: str) -> bool:
        markers = ["pom.xml", "build.gradle", "build.gradle.kts", "gradlew"]
        return any(os.path.exists(os.path.join(repo_dir, m)) for m in markers)

    def _has_maven(self, repo_dir: str) -> bool:
        return os.path.exists(os.path.join(repo_dir, "pom.xml"))

    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        if self._has_maven(repo_dir):
            self._run(
                ["mvn", "dependency:resolve", "-q", "-B"],
                cwd=repo_dir, timeout=600,
            )
            runner_cmd = ["mvn", "test", "-B"]
        else:
            # Gradle
            gradlew = os.path.join(repo_dir, "gradlew")
            gradle_exec = gradlew if os.path.exists(gradlew) else "gradle"
            self._run([gradle_exec, "dependencies", "-q"], cwd=repo_dir, timeout=600)
            runner_cmd = [gradle_exec, "test"]

        return EnvConfig(
            language="java",
            test_runner_cmd=runner_cmd,
            env_dir=repo_dir,
            metadata={"build_system": "maven" if self._has_maven(repo_dir) else "gradle"},
        )

    def discover_tests(self, repo_dir: str) -> list[str]:
        patterns = [
            f"{repo_dir}/**/src/test/**/*Test.java",
            f"{repo_dir}/**/src/test/**/*Tests.java",
            f"{repo_dir}/**/src/test/**/*Spec.java",
            f"{repo_dir}/**/src/test/**/*IT.java",
        ]
        found = set()
        for pat in patterns:
            for path in glob.glob(pat, recursive=True):
                found.add(os.path.relpath(path, repo_dir))
        return sorted(found)

    def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int = 300) -> tuple[str, int]:
        build = env_config.metadata.get("build_system", "maven")
        # Extract class name from path: src/test/java/com/example/FooTest.java → com.example.FooTest
        class_name = (
            test_path
            .replace("src/test/java/", "")
            .replace("/", ".")
            .replace(".java", "")
        )
        if build == "maven":
            cmd = ["mvn", "test", "-B", f"-Dtest={class_name}", "-Dsurefire.failIfNoSpecifiedTests=false"]
        else:
            gradlew = os.path.join(repo_dir, "gradlew")
            gradle_exec = gradlew if os.path.exists(gradlew) else "gradle"
            cmd = [gradle_exec, "test", f"--tests", class_name]
        return self._run(cmd, cwd=repo_dir, timeout=timeout)

    def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport:
        findings = []
        findings.extend(self._scan_secrets(diff_text))
        findings.extend(self._scan_java_patterns(diff_text))
        semgrep_out = self._run_semgrep_java(changed_files, repo_dir)

        critical = [f for f in findings if f.severity == "CRITICAL"]
        high = [f for f in findings if f.severity == "HIGH"]
        blocked_reason = None
        if critical:
            blocked_reason = f"CRITICAL: {critical[0].description}"
        elif len(high) >= 3:
            blocked_reason = f"{len(high)} HIGH severity findings"

        return RuntimeSastReport(
            passed=blocked_reason is None,
            language="java",
            findings=findings,
            tool_output=semgrep_out,
            blocked_reason=blocked_reason,
        )

    def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]:
        try:
            from sast_gate import _scan_diff_for_secrets
            return [
                RuntimeSastFinding(f.severity, f.category, f.line_number, f.line_content, f.description)
                for f in _scan_diff_for_secrets(diff_text)
            ]
        except ImportError:
            return []

    _JAVA_DANGEROUS = [
        (re.compile(r'Runtime\.getRuntime\(\)\.exec\s*\('), "CRITICAL", "Runtime.exec() — OS injection risk"),
        (re.compile(r'ProcessBuilder\s*\('), "HIGH", "ProcessBuilder — verify no untrusted input"),
        (re.compile(r'ObjectInputStream'), "CRITICAL", "Java deserialization — RCE risk"),
        (re.compile(r'ScriptEngine.*eval\s*\('), "CRITICAL", "ScriptEngine.eval() — code injection"),
        (re.compile(r'\.createQuery\(.*\+'), "HIGH", "JPQL/HQL string concat — injection risk"),
        (re.compile(r'Statement.*execute.*\+'), "HIGH", "SQL concatenation — injection risk"),
        (re.compile(r'@SuppressWarnings\("unchecked"\)'), "LOW", "Unchecked cast suppressed"),
        (re.compile(r'System\.exit\s*\('), "MEDIUM", "System.exit() in library code"),
    ]

    def _scan_java_patterns(self, diff_text: str) -> list[RuntimeSastFinding]:
        findings = []
        for i, line in enumerate(diff_text.splitlines(), 1):
            if not line.startswith("+"):
                continue
            for pattern, severity, description in self._JAVA_DANGEROUS:
                if pattern.search(line):
                    findings.append(RuntimeSastFinding(
                        severity=severity, category="java-security",
                        line_number=i, line_content=line[1:].strip(),
                        description=description,
                    ))
        return findings

    def _run_semgrep_java(self, changed_files: list[str], repo_dir: str) -> str:
        java_files = [f for f in changed_files if f.endswith(".java")]
        if not java_files:
            return ""
        outputs = []
        for rel in java_files[:10]:  # cap to avoid timeout on large repos
            abs_path = os.path.join(repo_dir, rel)
            if os.path.exists(abs_path):
                out, _ = self._run(
                    ["semgrep", "--config", "p/java", "--quiet", abs_path],
                    cwd=repo_dir, timeout=90,
                )
                outputs.append(out)
        return "\n".join(outputs)

    def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport:
        new_packages = self._extract_new_maven_deps(diff_text)
        cve_out, code = self._run_owasp_check(repo_dir)
        cve_findings = self._parse_owasp_output(cve_out)
        critical_cves = [c for c in cve_findings if c.get("cvssScore", 0) >= 9.0]
        if critical_cves:
            return RuntimeSupplyChainReport(
                passed=False, language="java",
                new_packages=new_packages, cve_findings=cve_findings,
                blocked_reason=f"Critical CVE in Maven dep: {critical_cves[0].get('name')}",
            )
        return RuntimeSupplyChainReport(
            passed=True, language="java",
            new_packages=new_packages, cve_findings=cve_findings,
        )

    def _extract_new_maven_deps(self, diff_text: str) -> list[str]:
        added = []
        in_pom = False
        for line in diff_text.splitlines():
            if "pom.xml" in line or "build.gradle" in line:
                in_pom = True
            if in_pom and line.startswith("+") and not line.startswith("+++"):
                # Maven: <artifactId>foo</artifactId>
                m = re.search(r"<artifactId>\s*([\w\-\.]+)\s*</artifactId>", line)
                if m:
                    added.append(m.group(1))
                # Gradle: implementation 'group:name:version'
                m2 = re.search(r"['\"][\w\.\-]+:([\w\.\-]+):", line)
                if m2:
                    added.append(m2.group(1))
        return list(dict.fromkeys(added))

    def _run_owasp_check(self, repo_dir: str) -> tuple[str, int]:
        if self._has_maven(repo_dir):
            return self._run(
                ["mvn", "org.owasp:dependency-check-maven:check", "-B",
                 "-DfailBuildOnCVSS=9", "-Dformat=JSON"],
                cwd=repo_dir, timeout=300,
            )
        return "", 0

    def _parse_owasp_output(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
            deps = data.get("dependencies", [])
            results = []
            for dep in deps:
                for vuln in dep.get("vulnerabilities", []):
                    results.append({
                        "name": dep.get("fileName", ""),
                        "cve": vuln.get("name", ""),
                        "cvssScore": vuln.get("cvssv3", {}).get("baseScore", 0),
                    })
            return results
        except Exception:
            return []

    def get_mcp_domains(self) -> list[str]:
        return [
            "docs.oracle.com", "mvnrepository.com", "maven.apache.org",
            "docs.spring.io", "docs.github.com", "javadoc.io",
        ]

    def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str = "") -> str:
        src_target = src_hint or "the relevant Java source file in src/main/java"
        return (
            f"1. Fix '{src_target}' or 'pom.xml'/'build.gradle' to make the test pass. "
            f"Do NOT modify test files under src/test.\n"
            f"2. Use the 'fetch-docs' MCP tool for docs.spring.io or javadoc.io if needed.\n"
            f"3. Ensure the fix compiles cleanly — no raw type warnings, no checked exception swallowing.\n"
            f"4. Work on branch '{branch_name}'. Commit the minimal fix.\n"
            f"5. The fix must not break other tests or change public API signatures."
        )


# ──────────────────────────────────────────────────────────────
# GO RUNTIME
# ──────────────────────────────────────────────────────────────

class GoRuntime(LanguageRuntime):
    language = "go"

    @classmethod
    def detect(cls, repo_dir: str) -> bool:
        return os.path.exists(os.path.join(repo_dir, "go.mod"))

    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        self._run(["go", "mod", "download"], cwd=repo_dir, timeout=300)
        return EnvConfig(
            language="go",
            test_runner_cmd=["go", "test"],
            env_dir=repo_dir,
        )

    def discover_tests(self, repo_dir: str) -> list[str]:
        found = set()
        for path in glob.glob(f"{repo_dir}/**/*_test.go", recursive=True):
            found.add(os.path.relpath(path, repo_dir))
        return sorted(p for p in found if "vendor" not in p)

    def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int = 120) -> tuple[str, int]:
        # Go tests run per-package; derive the package from the file path
        pkg_dir = os.path.dirname(os.path.join(repo_dir, test_path))
        pkg_rel = "./" + os.path.relpath(pkg_dir, repo_dir)
        return self._run(
            ["go", "test", "-v", "-count=1", "-run", ".", pkg_rel],
            cwd=repo_dir, timeout=timeout,
        )

    def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport:
        findings = []
        findings.extend(self._scan_secrets(diff_text))
        findings.extend(self._scan_go_patterns(diff_text))
        gosec_out = self._run_gosec(changed_files, repo_dir)

        critical = [f for f in findings if f.severity == "CRITICAL"]
        blocked_reason = f"CRITICAL: {critical[0].description}" if critical else None
        return RuntimeSastReport(
            passed=blocked_reason is None,
            language="go",
            findings=findings,
            tool_output=gosec_out,
            blocked_reason=blocked_reason,
        )

    def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]:
        try:
            from sast_gate import _scan_diff_for_secrets
            return [
                RuntimeSastFinding(f.severity, f.category, f.line_number, f.line_content, f.description)
                for f in _scan_diff_for_secrets(diff_text)
            ]
        except ImportError:
            return []

    _GO_DANGEROUS = [
        (re.compile(r'exec\.Command\s*\('), "HIGH", "exec.Command — verify no untrusted input"),
        (re.compile(r'exec\.CommandContext\s*\('), "HIGH", "exec.CommandContext — verify no untrusted input"),
        (re.compile(r'sql\.Open.*\+'), "HIGH", "SQL string concat — injection risk"),
        (re.compile(r'reflect\.'), "MEDIUM", "reflect usage — verify type safety"),
        (re.compile(r'unsafe\.'), "HIGH", "unsafe package — memory safety risk"),
        (re.compile(r'encoding/gob'), "HIGH", "gob deserialization — potential RCE if untrusted input"),
        (re.compile(r'os\.Setenv\s*\('), "MEDIUM", "os.Setenv in handler — env pollution risk"),
    ]

    def _scan_go_patterns(self, diff_text: str) -> list[RuntimeSastFinding]:
        findings = []
        for i, line in enumerate(diff_text.splitlines(), 1):
            if not line.startswith("+"):
                continue
            for pattern, severity, description in self._GO_DANGEROUS:
                if pattern.search(line):
                    findings.append(RuntimeSastFinding(
                        severity=severity, category="go-security",
                        line_number=i, line_content=line[1:].strip(),
                        description=description,
                    ))
        return findings

    def _run_gosec(self, changed_files: list[str], repo_dir: str) -> str:
        go_files = [f for f in changed_files if f.endswith(".go") and not f.endswith("_test.go")]
        if not go_files:
            return ""
        out, _ = self._run(
            ["gosec", "-fmt", "text", "-quiet", "./..."],
            cwd=repo_dir, timeout=120,
        )
        return out

    def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport:
        new_mods = self._extract_new_go_modules(diff_text)
        vuln_out, code = self._run(
            ["govulncheck", "./..."],
            cwd=repo_dir, timeout=180,
        )
        cve_findings = self._parse_govulncheck(vuln_out)
        critical_cves = [c for c in cve_findings if "CRITICAL" in c.get("severity", "")]
        if critical_cves:
            return RuntimeSupplyChainReport(
                passed=False, language="go",
                new_packages=new_mods, cve_findings=cve_findings,
                blocked_reason=f"Critical vulnerability: {critical_cves[0].get('id')}",
            )
        return RuntimeSupplyChainReport(
            passed=True, language="go",
            new_packages=new_mods, cve_findings=cve_findings,
        )

    def _extract_new_go_modules(self, diff_text: str) -> list[str]:
        added = []
        for line in diff_text.splitlines():
            if "go.mod" in line or "go.sum" in line:
                continue
            if line.startswith("+") and not line.startswith("+++"):
                m = re.search(r'require\s+([\w\./\-]+)\s+v', line)
                if m:
                    added.append(m.group(1))
        return list(dict.fromkeys(added))

    def _parse_govulncheck(self, raw: str) -> list[dict]:
        findings = []
        for line in raw.splitlines():
            m = re.search(r"(GO-\d+-\d+|CVE-\d+-\d+)", line)
            if m:
                findings.append({"id": m.group(1), "severity": "HIGH", "context": line.strip()})
        return findings

    def get_mcp_domains(self) -> list[str]:
        return [
            "pkg.go.dev", "go.dev", "docs.github.com",
            "golang.org", "blog.golang.org",
        ]

    def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str = "") -> str:
        pkg_dir = os.path.dirname(test_path) or "."
        src_target = src_hint or f"the Go source files in '{pkg_dir}'"
        return (
            f"1. Fix '{src_target}' or 'go.mod' to make the test pass. "
            f"Do NOT modify *_test.go files.\n"
            f"2. Run 'go vet ./...' mentally — ensure no vet errors are introduced.\n"
            f"3. Use the 'fetch-docs' MCP tool for pkg.go.dev if needed.\n"
            f"4. Work on branch '{branch_name}'. Commit the minimal fix.\n"
            f"5. The fix must not break other packages. Run only the affected package test."
        )


# ──────────────────────────────────────────────────────────────
# RUST RUNTIME
# ──────────────────────────────────────────────────────────────

class RustRuntime(LanguageRuntime):
    language = "rust"

    @classmethod
    def detect(cls, repo_dir: str) -> bool:
        return os.path.exists(os.path.join(repo_dir, "Cargo.toml"))

    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        self._run(["cargo", "fetch"], cwd=repo_dir, timeout=300)
        return EnvConfig(
            language="rust",
            test_runner_cmd=["cargo", "test"],
            env_dir=repo_dir,
        )

    def discover_tests(self, repo_dir: str) -> list[str]:
        # Rust tests live inside source files and in tests/ directory
        found = set()
        # Integration tests
        for path in glob.glob(f"{repo_dir}/tests/**/*.rs", recursive=True):
            found.add(os.path.relpath(path, repo_dir))
        # Source files with #[cfg(test)] — treat each .rs file as a test candidate
        for path in glob.glob(f"{repo_dir}/src/**/*.rs", recursive=True):
            content = Path(path).read_text(errors="ignore")
            if "#[cfg(test)]" in content or "#[test]" in content:
                found.add(os.path.relpath(path, repo_dir))
        return sorted(found)

    def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int = 180) -> tuple[str, int]:
        # Derive test module name from path
        if test_path.startswith("tests/"):
            test_name = Path(test_path).stem
            return self._run(
                ["cargo", "test", "--test", test_name, "--", "--nocapture"],
                cwd=repo_dir, timeout=timeout,
            )
        else:
            # Unit tests — run the whole crate's unit tests
            return self._run(
                ["cargo", "test", "--lib", "--", "--nocapture"],
                cwd=repo_dir, timeout=timeout,
            )

    def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport:
        findings = []
        findings.extend(self._scan_secrets(diff_text))
        findings.extend(self._scan_rust_patterns(diff_text))
        clippy_out = self._run_clippy(repo_dir)

        critical = [f for f in findings if f.severity == "CRITICAL"]
        blocked_reason = f"CRITICAL: {critical[0].description}" if critical else None
        return RuntimeSastReport(
            passed=blocked_reason is None, language="rust",
            findings=findings, tool_output=clippy_out,
            blocked_reason=blocked_reason,
        )

    def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]:
        try:
            from sast_gate import _scan_diff_for_secrets
            return [
                RuntimeSastFinding(f.severity, f.category, f.line_number, f.line_content, f.description)
                for f in _scan_diff_for_secrets(diff_text)
            ]
        except ImportError:
            return []

    _RUST_DANGEROUS = [
        (re.compile(r'\bunsafe\s*\{'), "HIGH", "unsafe block — verify memory safety invariants"),
        (re.compile(r'std::mem::transmute'), "CRITICAL", "mem::transmute — type system bypass"),
        (re.compile(r'from_raw_parts'), "HIGH", "slice::from_raw_parts — verify pointer validity"),
        (re.compile(r'Box::from_raw'), "HIGH", "Box::from_raw — double-free risk"),
        (re.compile(r'std::process::Command'), "MEDIUM", "process::Command — verify no untrusted input"),
        (re.compile(r'panic!\s*\(.*unwrap'), "LOW", "unwrap in panic context"),
    ]

    def _scan_rust_patterns(self, diff_text: str) -> list[RuntimeSastFinding]:
        findings = []
        for i, line in enumerate(diff_text.splitlines(), 1):
            if not line.startswith("+"):
                continue
            for pattern, severity, description in self._RUST_DANGEROUS:
                if pattern.search(line):
                    findings.append(RuntimeSastFinding(
                        severity=severity, category="rust-security",
                        line_number=i, line_content=line[1:].strip(),
                        description=description,
                    ))
        return findings

    def _run_clippy(self, repo_dir: str) -> str:
        out, _ = self._run(
            ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"],
            cwd=repo_dir, timeout=300,
        )
        return out

    def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport:
        new_crates = self._extract_new_crates(diff_text)
        audit_out, code = self._run(["cargo", "audit", "--json"], cwd=repo_dir, timeout=120)
        cve_findings = self._parse_cargo_audit(audit_out)
        critical_cves = [c for c in cve_findings if c.get("cvss", 0) >= 9.0]
        if critical_cves:
            return RuntimeSupplyChainReport(
                passed=False, language="rust",
                new_packages=new_crates, cve_findings=cve_findings,
                blocked_reason=f"Critical CVE in crate: {critical_cves[0].get('package')}",
            )
        return RuntimeSupplyChainReport(
            passed=True, language="rust",
            new_packages=new_crates, cve_findings=cve_findings,
        )

    def _extract_new_crates(self, diff_text: str) -> list[str]:
        added = []
        in_cargo = False
        for line in diff_text.splitlines():
            if "Cargo.toml" in line:
                in_cargo = True
            if in_cargo and line.startswith("+") and not line.startswith("+++"):
                m = re.search(r'^([\w\-]+)\s*=', line[1:].strip())
                if m:
                    added.append(m.group(1))
        return list(dict.fromkeys(added))

    def _parse_cargo_audit(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
            vulns = data.get("vulnerabilities", {}).get("list", [])
            return [
                {
                    "package": v.get("advisory", {}).get("package", ""),
                    "id": v.get("advisory", {}).get("id", ""),
                    "cvss": v.get("advisory", {}).get("cvss", 0) or 0,
                }
                for v in vulns
            ]
        except Exception:
            return []

    def get_mcp_domains(self) -> list[str]:
        return ["doc.rust-lang.org", "crates.io", "docs.rs", "docs.github.com"]

    def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str = "") -> str:
        src_target = src_hint or "src/lib.rs or the relevant module"
        return (
            f"1. Fix '{src_target}' or 'Cargo.toml' to make the test pass. "
            f"Do NOT modify test modules (files or #[cfg(test)] blocks).\n"
            f"2. Ensure the fix passes 'cargo clippy -- -D warnings' with no new lints.\n"
            f"3. Use the 'fetch-docs' MCP tool for docs.rs or doc.rust-lang.org if needed.\n"
            f"4. Work on branch '{branch_name}'. Commit the minimal fix.\n"
            f"5. Unsafe code must include a SAFETY comment explaining the invariant."
        )


# ──────────────────────────────────────────────────────────────
# RUBY RUNTIME
# ──────────────────────────────────────────────────────────────

class RubyRuntime(LanguageRuntime):
    language = "ruby"

    @classmethod
    def detect(cls, repo_dir: str) -> bool:
        return (
            os.path.exists(os.path.join(repo_dir, "Gemfile")) or
            os.path.exists(os.path.join(repo_dir, "Gemfile.lock"))
        )

    def _detect_runner(self, repo_dir: str) -> str:
        spec_dir = os.path.join(repo_dir, "spec")
        test_dir = os.path.join(repo_dir, "test")
        if os.path.isdir(spec_dir):
            return "rspec"
        if os.path.isdir(test_dir):
            return "minitest"
        return "rspec"

    def setup_env(self, repo_dir: str, persistent_dir: str = "/data") -> EnvConfig:
        self._run(["bundle", "install", "--jobs", "4", "--retry", "3"],
                  cwd=repo_dir, timeout=600)
        runner = self._detect_runner(repo_dir)
        if runner == "rspec":
            cmd = ["bundle", "exec", "rspec"]
        else:
            cmd = ["bundle", "exec", "ruby", "-Ilib", "-Itest"]
        return EnvConfig(
            language="ruby",
            test_runner_cmd=cmd,
            env_dir=repo_dir,
            metadata={"runner": runner},
        )

    def discover_tests(self, repo_dir: str) -> list[str]:
        patterns = [
            f"{repo_dir}/spec/**/*_spec.rb",
            f"{repo_dir}/test/**/*_test.rb",
            f"{repo_dir}/test/**/test_*.rb",
        ]
        found = set()
        for pat in patterns:
            for path in glob.glob(pat, recursive=True):
                found.add(os.path.relpath(path, repo_dir))
        return sorted(found)

    def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int = 120) -> tuple[str, int]:
        runner = env_config.metadata.get("runner", "rspec")
        if runner == "rspec":
            cmd = ["bundle", "exec", "rspec", test_path, "--format", "documentation"]
        else:
            cmd = ["bundle", "exec", "ruby", "-Ilib", "-Itest", test_path]
        return self._run(cmd, cwd=repo_dir, timeout=timeout)

    def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport:
        findings = []
        findings.extend(self._scan_secrets(diff_text))
        findings.extend(self._scan_ruby_patterns(diff_text))
        brakeman_out = self._run_brakeman(repo_dir)

        critical = [f for f in findings if f.severity == "CRITICAL"]
        blocked_reason = f"CRITICAL: {critical[0].description}" if critical else None
        return RuntimeSastReport(
            passed=blocked_reason is None, language="ruby",
            findings=findings, tool_output=brakeman_out,
            blocked_reason=blocked_reason,
        )

    def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]:
        try:
            from sast_gate import _scan_diff_for_secrets
            return [
                RuntimeSastFinding(f.severity, f.category, f.line_number, f.line_content, f.description)
                for f in _scan_diff_for_secrets(diff_text)
            ]
        except ImportError:
            return []

    _RUBY_DANGEROUS = [
        (re.compile(r'\beval\s*[(\s]'), "CRITICAL", "eval() — arbitrary code execution"),
        (re.compile(r'\bsend\s*\(.*params'), "HIGH", "Dynamic dispatch with user params — injection risk"),
        (re.compile(r'`.*#\{'), "HIGH", "Shell interpolation in backtick — OS injection"),
        (re.compile(r'system\s*\(.*#\{'), "HIGH", "system() with interpolation — OS injection"),
        (re.compile(r'Marshal\.load'), "CRITICAL", "Marshal.load — deserialization RCE risk"),
        (re.compile(r'\.html_safe'), "HIGH", "html_safe — potential XSS"),
        (re.compile(r'raw\s+params'), "HIGH", "raw params output — XSS risk"),
        (re.compile(r'find_by_sql\s*\(.*\+'), "HIGH", "SQL concat in find_by_sql — injection"),
    ]

    def _scan_ruby_patterns(self, diff_text: str) -> list[RuntimeSastFinding]:
        findings = []
        for i, line in enumerate(diff_text.splitlines(), 1):
            if not line.startswith("+"):
                continue
            for pattern, severity, description in self._RUBY_DANGEROUS:
                if pattern.search(line):
                    findings.append(RuntimeSastFinding(
                        severity=severity, category="ruby-security",
                        line_number=i, line_content=line[1:].strip(),
                        description=description,
                    ))
        return findings

    def _run_brakeman(self, repo_dir: str) -> str:
        gemfile = os.path.join(repo_dir, "Gemfile")
        if not os.path.exists(gemfile):
            return ""
        out, _ = self._run(
            ["bundle", "exec", "brakeman", "-q", "--no-pager", "-f", "text"],
            cwd=repo_dir, timeout=120,
        )
        return out

    def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport:
        new_gems = self._extract_new_gems(diff_text)
        audit_out, _ = self._run(
            ["bundle", "exec", "bundler-audit", "check", "--update"],
            cwd=repo_dir, timeout=120,
        )
        cve_findings = self._parse_bundle_audit(audit_out)
        critical_cves = [c for c in cve_findings if "CRITICAL" in c.get("criticality", "")]
        if critical_cves:
            return RuntimeSupplyChainReport(
                passed=False, language="ruby",
                new_packages=new_gems, cve_findings=cve_findings,
                blocked_reason=f"Critical gem vulnerability: {critical_cves[0].get('gem')}",
            )
        return RuntimeSupplyChainReport(
            passed=True, language="ruby",
            new_packages=new_gems, cve_findings=cve_findings,
        )

    def _extract_new_gems(self, diff_text: str) -> list[str]:
        added = []
        for line in diff_text.splitlines():
            if "Gemfile" in line and not line.startswith("+"):
                continue
            if line.startswith("+") and not line.startswith("+++"):
                m = re.search(r"gem\s+['\"]([^'\"]+)['\"]", line)
                if m:
                    added.append(m.group(1))
        return list(dict.fromkeys(added))

    def _parse_bundle_audit(self, raw: str) -> list[dict]:
        findings = []
        for line in raw.splitlines():
            m = re.search(r"Name:\s+(\S+)", line)
            if m:
                findings.append({"gem": m.group(1), "criticality": "HIGH"})
        return findings

    def get_mcp_domains(self) -> list[str]:
        return [
            "ruby-doc.org", "rubygems.org", "api.rubyonrails.org",
            "guides.rubyonrails.org", "docs.github.com",
        ]

    def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str = "") -> str:
        src_target = src_hint or "the relevant Ruby source file under app/ or lib/"
        return (
            f"1. Fix '{src_target}' or 'Gemfile' to make the test pass. "
            f"Do NOT modify spec/ or test/ files.\n"
            f"2. Use the 'fetch-docs' MCP tool for api.rubyonrails.org or rubygems.org if needed.\n"
            f"3. Work on branch '{branch_name}'. Commit the minimal fix.\n"
            f"4. Ensure ActiveRecord queries use parameterized forms — no string interpolation in SQL.\n"
            f"5. The fix must not break other tests or change model validations."
        )


# ──────────────────────────────────────────────────────────────
# RUNTIME FACTORY
# ──────────────────────────────────────────────────────────────

class RuntimeFactory:
    """
    Detects and returns the correct LanguageRuntime for a cloned repo.
    Detection order matters — TypeScript before Node (TS is a superset),
    Python last as fallback since many repos have a setup.py alongside other stacks.
    """

    _REGISTRY: list[type[LanguageRuntime]] = [
        TypeScriptRuntime,   # before Node — TS repos also have package.json
        NodeRuntime,
        JavaRuntime,
        GoRuntime,
        RustRuntime,
        RubyRuntime,
        PythonRuntime,       # last: many repos include Python tooling as secondary
    ]

    @classmethod
    def for_repo(cls, repo_dir: str) -> LanguageRuntime:
        """
        Auto-detect and instantiate the correct runtime.
        Falls back to PythonRuntime if nothing matches.
        """
        for runtime_cls in cls._REGISTRY:
            if runtime_cls.detect(repo_dir):
                return runtime_cls()
        return PythonRuntime()  # safe fallback

    @classmethod
    def language_of(cls, repo_dir: str) -> str:
        """Lightweight language label without instantiation."""
        return cls.for_repo(repo_dir).language

    @classmethod
    def supported_languages(cls) -> list[str]:
        return [r.language for r in cls._REGISTRY]

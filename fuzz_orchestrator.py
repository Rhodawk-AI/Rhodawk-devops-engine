"""
Coverage-Guided Fuzzing Orchestrator — AFL++ + LibFuzzer-harness + Atheris.

Implements GAP 2 of the RHODAWK Enhancement Guide. Replaces the PBT-only
``red_team_fuzzer.py`` path with three coverage-guided engines plus
autonomous crash triage:

  * :class:`AFLPlusPlusEngine` — instruments compiled C/C++/Go targets
    with afl-cc + ASAN + UBSAN, runs ``afl-fuzz`` for a bounded wall
    time, and collects every saved crash input under
    ``<output>/default/crashes``.
  * :class:`LibFuzzerHarnessEngine` — generates a LibFuzzer harness
    body via the supplied LLM callable and compiles it against the
    target with ``-fsanitize=fuzzer,address,undefined``.
  * :class:`PythonAtherisEngine` — produces an Atheris harness for a
    Python target. Atheris is LibFuzzer-backed and gives true
    coverage-guided exploration on Python parsers / codecs.
  * :class:`CrashTriageEngine` — re-runs every saved crash input
    under AddressSanitizer, parses the symbolised stack, classifies
    the crash, and de-duplicates by stack-hash.

Codebase alignment:
  * All public types are dataclasses with strict typing.
  * No global state is mutated. Corpus / findings directories are
    parameterised via env vars and created per call.
  * External tools always run inside ``subprocess`` with explicit
    timeouts and the AFL++ ``AFL_NO_UI`` / ``AFL_SKIP_CPUFREQ``
    flags so they do not touch host tty / cpufreq state.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

LOG = logging.getLogger("fuzz_orchestrator")

AFL_BIN          = os.getenv("AFL_BIN",  "afl-fuzz")
AFLPP_CC         = os.getenv("AFL_CC",   "afl-cc")
FUZZ_TIMEOUT     = int(os.getenv("FUZZ_TIMEOUT_SECONDS", "1800"))
FUZZ_CORPUS_DIR  = os.getenv("FUZZ_CORPUS_DIR",   "/data/fuzz_corpus")
FUZZ_FINDINGS_DIR= os.getenv("FUZZ_FINDINGS_DIR", "/data/fuzz_findings")
FUZZ_MEM_LIMIT   = os.getenv("AFL_MEM_LIMIT", "512")        # MB
ATHERIS_TIMEOUT  = int(os.getenv("ATHERIS_TIMEOUT_SECONDS", "300"))
ATHERIS_BIN      = os.getenv("ATHERIS_PYTHON", "python3")


# ──────────────────────────────────────────────────────────────────────
# Result dataclasses.
# ──────────────────────────────────────────────────────────────────────


@dataclass
class CrashFinding:
    """One classified crash recovered from a fuzzing run."""

    target: str
    crash_input: bytes
    crash_type: str          # SEGV | HEAP_BUFFER_OVERFLOW | USE_AFTER_FREE | …
    stack_trace: str
    stack_hash: str          # sha256(top frames) — used for dedup
    asan_report: str
    severity: str            # critical | high | medium | low
    reproducer_cmd: str
    cwe_candidate: str


@dataclass
class FuzzResult:
    """Aggregate result of a single fuzzing run."""

    target: str
    duration_seconds: int
    crashes: list[CrashFinding] = field(default_factory=list)
    unique_paths: int = 0
    execs_per_sec: float = 0.0
    coverage_edges: int = 0


# ──────────────────────────────────────────────────────────────────────
# Crash triage — autonomous ASAN re-run + dedup.
# ──────────────────────────────────────────────────────────────────────


_CRASH_MARKERS: tuple[tuple[str, str], ...] = (
    ("heap-buffer-overflow",   "HEAP_BUFFER_OVERFLOW"),
    ("stack-buffer-overflow",  "STACK_BUFFER_OVERFLOW"),
    ("global-buffer-overflow", "GLOBAL_BUFFER_OVERFLOW"),
    ("use-after-free",         "USE_AFTER_FREE"),
    ("double-free",            "DOUBLE_FREE"),
    ("null-dereference",       "NULL_DEREFERENCE"),
    ("segv",                   "SEGV"),
    ("undefined-behavior",     "UNDEFINED_BEHAVIOR"),
    ("stack-overflow",         "STACK_OVERFLOW"),
)

_SEVERITY_BY_TYPE: dict[str, str] = {
    "HEAP_BUFFER_OVERFLOW":   "critical",
    "USE_AFTER_FREE":         "critical",
    "DOUBLE_FREE":            "critical",
    "STACK_BUFFER_OVERFLOW":  "high",
    "GLOBAL_BUFFER_OVERFLOW": "high",
    "STACK_OVERFLOW":         "high",
    "UNDEFINED_BEHAVIOR":     "medium",
    "NULL_DEREFERENCE":       "medium",
    "SEGV":                   "high",
    "UNKNOWN":                "medium",
}

_CWE_BY_TYPE: dict[str, str] = {
    "HEAP_BUFFER_OVERFLOW":   "CWE-122",
    "USE_AFTER_FREE":         "CWE-416",
    "STACK_BUFFER_OVERFLOW":  "CWE-121",
    "DOUBLE_FREE":            "CWE-415",
    "GLOBAL_BUFFER_OVERFLOW": "CWE-787",
    "NULL_DEREFERENCE":       "CWE-476",
    "STACK_OVERFLOW":         "CWE-674",
    "SEGV":                   "CWE-119",
    "UNDEFINED_BEHAVIOR":     "CWE-758",
}

# AddressSanitizer top-frame line e.g. "    #0 0x55d… in foo (/bin/x+0x123)"
_FRAME_RE = re.compile(r"^\s*#\d+\s+0x[0-9a-fA-F]+\s+in\s+(\S+)")


class CrashTriageEngine:
    """Re-runs each crash input under AddressSanitizer, classifies the
    crash type, and produces a stable stack-hash for deduplication.

    The triage engine is deliberately independent of any specific fuzzer
    so it can be reused by AFL++, LibFuzzer harnesses, or any future
    binary-fuzzing engine added later.
    """

    ASAN_OPTIONS: str = (
        "abort_on_error=0:detect_leaks=0:"
        "print_stacktrace=1:symbolize=1:"
        "halt_on_error=1:strip_path_prefix=/"
    )

    def triage_crash(
        self,
        binary: str,
        crash_path: str,
        timeout: int = 10,
    ) -> Optional[CrashFinding]:
        try:
            crash_input = Path(crash_path).read_bytes()
        except OSError:
            return None

        env = os.environ.copy()
        env["ASAN_OPTIONS"]  = self.ASAN_OPTIONS
        env["UBSAN_OPTIONS"] = "print_stacktrace=1:symbolize=1"

        try:
            proc = subprocess.run(
                [binary, crash_path],
                env=env,
                capture_output=True,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as exc:
            LOG.debug("triage subprocess failed for %s: %s", crash_path, exc)
            return None

        report = proc.stderr.decode(errors="replace")
        return self._build_finding(binary, crash_path, crash_input, report)

    def deduplicate(self, crashes: list[CrashFinding]) -> list[CrashFinding]:
        """Keep the *first* crash for each unique stack-hash."""
        seen: set[str] = set()
        unique: list[CrashFinding] = []
        for c in crashes:
            if c.stack_hash in seen:
                continue
            seen.add(c.stack_hash)
            unique.append(c)
        return unique

    @classmethod
    def _build_finding(
        cls,
        binary: str,
        crash_path: str,
        crash_input: bytes,
        report: str,
    ) -> CrashFinding:
        crash_type = "UNKNOWN"
        low = report.lower()
        for needle, label in _CRASH_MARKERS:
            if needle in low:
                crash_type = label
                break

        # Build a stack hash from the top frame symbols (ignoring offsets).
        frames = _FRAME_RE.findall(report)[:6]
        stack_key = "|".join(frames) if frames else report[:4096]
        stack_hash = hashlib.sha256(stack_key.encode("utf-8", "replace")).hexdigest()[:16]

        return CrashFinding(
            target=binary,
            crash_input=crash_input,
            crash_type=crash_type,
            stack_trace=report[:8192],
            stack_hash=stack_hash,
            asan_report=report,
            severity=_SEVERITY_BY_TYPE.get(crash_type, "medium"),
            reproducer_cmd=f"{binary} {crash_path}",
            cwe_candidate=_CWE_BY_TYPE.get(crash_type, "CWE-119"),
        )


# ──────────────────────────────────────────────────────────────────────
# AFL++ engine — compiled C/C++/Go targets.
# ──────────────────────────────────────────────────────────────────────


class AFLPlusPlusEngine:
    """Wraps ``afl-cc`` + ``afl-fuzz``.

    Workflow:
      1. ``instrument_and_build`` — recompile the target with AFL++
         instrumentation + ASAN + UBSAN.
      2. ``fuzz`` — drive ``afl-fuzz`` for ``timeout`` seconds.
      3. Internal ``_collect_results`` reads ``fuzzer_stats`` and feeds
         every saved crash through :class:`CrashTriageEngine`.
    """

    def __init__(self, triage: Optional[CrashTriageEngine] = None) -> None:
        self._triage = triage or CrashTriageEngine()

    def instrument_and_build(
        self,
        repo_path: str,
        build_cmd: str,
    ) -> Optional[str]:
        env = os.environ.copy()
        env.update({
            "CC":           AFLPP_CC,
            "CXX":          f"{AFLPP_CC}++",
            "AFL_HARDEN":   "1",
            "AFL_USE_ASAN": "1",
            "AFL_USE_UBSAN":"1",
        })
        try:
            result = subprocess.run(
                build_cmd,
                shell=True,
                env=env,
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=600,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            LOG.warning("AFL build failed: %s", exc)
            return None
        if result.returncode != 0:
            LOG.debug("AFL build returncode=%d stderr=%s",
                      result.returncode, result.stderr[:400])
            return None

        # Find a freshly-built executable that isn't a shared object.
        for root, _dirs, files in os.walk(repo_path):
            for name in files:
                fpath = os.path.join(root, name)
                if (
                    os.access(fpath, os.X_OK)
                    and not name.endswith((".so", ".dylib"))
                    and not os.path.isdir(fpath)
                ):
                    return fpath
        return None

    def fuzz(
        self,
        binary_path: str,
        target_name: str,
        seed_corpus: Optional[str] = None,
        timeout: int = FUZZ_TIMEOUT,
    ) -> FuzzResult:
        corpus_dir  = seed_corpus or os.path.join(FUZZ_CORPUS_DIR,   target_name)
        output_dir  = os.path.join(FUZZ_FINDINGS_DIR, target_name)
        os.makedirs(corpus_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Provide a minimal seed if the corpus is empty.
        if not list(Path(corpus_dir).iterdir()):
            (Path(corpus_dir) / "seed0").write_bytes(b"\x00" * 64)

        cmd = [
            AFL_BIN,
            "-i", corpus_dir,
            "-o", output_dir,
            "-m", FUZZ_MEM_LIMIT,
            "-t", "1000+",
        ]
        # Optional grammar dictionary — only add if present.
        dict_dir = "/usr/share/aflplusplus/dictionaries/"
        if os.path.isdir(dict_dir):
            cmd.extend(["-x", dict_dir])
        cmd.extend(["--", binary_path, "@@"])

        env = os.environ.copy()
        env.update({
            "AFL_AUTORESUME":   "1",
            "AFL_SKIP_CPUFREQ": "1",
            "AFL_NO_UI":        "1",
        })

        try:
            proc = subprocess.Popen(
                cmd, env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            LOG.warning("afl-fuzz binary not found: %s", exc)
            return FuzzResult(target=target_name, duration_seconds=0)

        try:
            time.sleep(timeout)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        return self._collect_results(output_dir, target_name, binary_path)

    def _collect_results(
        self,
        output_dir: str,
        target: str,
        binary: str,
    ) -> FuzzResult:
        crashes: list[CrashFinding] = []
        crash_dir = os.path.join(output_dir, "default", "crashes")
        if os.path.isdir(crash_dir):
            for crash_file in Path(crash_dir).iterdir():
                if not crash_file.is_file():
                    continue
                if not crash_file.name.startswith("id:"):
                    continue
                triaged = self._triage.triage_crash(binary, str(crash_file))
                if triaged is not None:
                    crashes.append(triaged)
        crashes = self._triage.deduplicate(crashes)

        stats: dict[str, str] = {}
        stats_path = os.path.join(output_dir, "default", "fuzzer_stats")
        if os.path.exists(stats_path):
            try:
                for line in Path(stats_path).read_text().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        stats[k.strip()] = v.strip()
            except OSError:
                pass

        return FuzzResult(
            target=target,
            duration_seconds=int(float(stats.get("run_time", "0") or "0")),
            crashes=crashes,
            unique_paths=int(float(stats.get("paths_total", "0") or "0")),
            execs_per_sec=float(stats.get("execs_per_sec", "0") or "0"),
            coverage_edges=int(float(stats.get("edges_found", "0") or "0")),
        )


# ──────────────────────────────────────────────────────────────────────
# LibFuzzer harness generator.
# ──────────────────────────────────────────────────────────────────────


class LibFuzzerHarnessEngine:
    """LLM-generated LibFuzzer harnesses for C/C++ parser targets."""

    HARNESS_TEMPLATE: str = (
        "#include <stdint.h>\n"
        "#include <stddef.h>\n"
        "// Target-specific includes go here\n"
        "\n"
        "extern \"C\" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {{\n"
        "    {body}\n"
        "    return 0;\n"
        "}}\n"
    )

    def generate_harness(
        self,
        target_function: str,
        header_context: str,
        llm_fn: Callable[[str], str],
    ) -> str:
        prompt = (
            f"Write a LibFuzzer harness (C++) for the function: {target_function}\n"
            f"Headers available: {header_context[:1000]}\n"
            "\n"
            "Rules:\n"
            "1. Call the target function with fuzzed data derived from (data, size).\n"
            "2. Handle all allocation failures gracefully.\n"
            "3. Do not call exit() or abort().\n"
            "4. The harness body goes between the braces — output ONLY the body code.\n"
        )
        try:
            body = llm_fn(prompt) or ""
        except Exception as exc:  # noqa: BLE001
            LOG.warning("LibFuzzer harness LLM call failed: %s", exc)
            body = ""
        return self.HARNESS_TEMPLATE.format(body=body)

    def compile_harness(
        self,
        harness_code: str,
        includes: list[str],
        libs: list[str],
    ) -> Optional[str]:
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False, mode="w") as fh:
            fh.write(harness_code)
            src_path = fh.name
        binary_path = src_path.replace(".cpp", "_fuzz")
        cmd = [
            "clang++", "-g", "-O1",
            "-fsanitize=fuzzer,address,undefined",
        ]
        for inc in includes:
            cmd.extend([f"-I{inc}"])
        cmd.append(src_path)
        for lib in libs:
            cmd.append(f"-l{lib}")
        cmd.extend(["-o", binary_path])
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            LOG.warning("clang++ harness compile failed: %s", exc)
            return None
        return binary_path if result.returncode == 0 else None


# ──────────────────────────────────────────────────────────────────────
# Atheris engine — Python coverage-guided fuzzing.
# ──────────────────────────────────────────────────────────────────────


class PythonAtherisEngine:
    """Atheris (LibFuzzer-backed Python fuzzing) harness generation
    and execution. Outperforms Hypothesis for parser/codec targets
    because it gets true edge coverage from LibFuzzer."""

    ATHERIS_TEMPLATE: str = (
        "import atheris\n"
        "import sys\n"
        "\n"
        "with atheris.instrument_imports():\n"
        "    {imports}\n"
        "\n"
        "@atheris.instrument_func\n"
        "def TestOneInput(data):\n"
        "    fdp = atheris.FuzzedDataProvider(data)\n"
        "    try:\n"
        "        {body}\n"
        "    except (ValueError, TypeError, UnicodeDecodeError, OverflowError):\n"
        "        pass  # Expected exceptions — not crashes\n"
        "\n"
        "atheris.Setup(sys.argv, TestOneInput)\n"
        "atheris.Fuzz()\n"
    )

    def __init__(self, triage: Optional[CrashTriageEngine] = None) -> None:
        self._triage = triage or CrashTriageEngine()

    def generate_harness(
        self,
        target_module: str,
        target_fn: str,
        llm_fn: Callable[[str], str],
    ) -> str:
        prompt = (
            f"Write an Atheris (Python LibFuzzer) harness body that tests "
            f"{target_fn} from {target_module}.\n"
            "Use fdp (FuzzedDataProvider) to generate fuzzed inputs.\n"
            "Output ONLY the body code that goes inside TestOneInput()."
        )
        try:
            body = llm_fn(prompt) or "pass"
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Atheris harness LLM call failed: %s", exc)
            body = "pass"
        # Indent the LLM body to fit inside ``try:``.
        body_indented = "\n        ".join(line for line in body.splitlines()) or "pass"
        imports = f"import {target_module}" if target_module else "pass"
        return self.ATHERIS_TEMPLATE.format(
            imports=imports,
            body=body_indented,
        )

    def fuzz(
        self,
        harness_code: str,
        target_name: str,
        timeout: int = ATHERIS_TIMEOUT,
    ) -> FuzzResult:
        with tempfile.TemporaryDirectory(prefix="atheris_") as tmpdir:
            harness_path = os.path.join(tmpdir, "harness.py")
            artifact_dir = os.path.join(tmpdir, "artifacts")
            os.makedirs(artifact_dir, exist_ok=True)
            Path(harness_path).write_text(harness_code, encoding="utf-8")

            cmd = [
                ATHERIS_BIN, harness_path,
                f"-artifact_prefix={artifact_dir}/",
                "-print_final_stats=1",
                f"-max_total_time={timeout}",
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout + 30,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                LOG.warning("Atheris run failed: %s", exc)
                return FuzzResult(target=target_name, duration_seconds=timeout)

            stderr = proc.stderr.decode(errors="replace")
            crashes: list[CrashFinding] = []
            for artifact in Path(artifact_dir).iterdir():
                if not artifact.is_file():
                    continue
                try:
                    crash_input = artifact.read_bytes()
                except OSError:
                    continue
                finding = self._triage._build_finding(  # noqa: SLF001
                    binary=ATHERIS_BIN,
                    crash_path=str(artifact),
                    crash_input=crash_input,
                    report=stderr,
                )
                crashes.append(finding)
            crashes = self._triage.deduplicate(crashes)

        return FuzzResult(
            target=target_name,
            duration_seconds=timeout,
            crashes=crashes,
        )


# ──────────────────────────────────────────────────────────────────────
# FuzzOrchestrator — single entry-point used by hermes_orchestrator.
# ──────────────────────────────────────────────────────────────────────


@dataclass
class _FuzzEngines:
    afl:      AFLPlusPlusEngine
    libfuzz:  LibFuzzerHarnessEngine
    atheris:  PythonAtherisEngine
    triage:   CrashTriageEngine


class FuzzOrchestrator:
    """Routes a fuzz request to the right engine based on language."""

    COMPILED_LANGS: frozenset[str] = frozenset({"c", "cpp", "c++", "go", "rust"})

    def __init__(self) -> None:
        triage = CrashTriageEngine()
        self._engines = _FuzzEngines(
            afl=AFLPlusPlusEngine(triage=triage),
            libfuzz=LibFuzzerHarnessEngine(),
            atheris=PythonAtherisEngine(triage=triage),
            triage=triage,
        )

    @property
    def afl(self) -> AFLPlusPlusEngine:
        return self._engines.afl

    @property
    def libfuzz(self) -> LibFuzzerHarnessEngine:
        return self._engines.libfuzz

    @property
    def atheris(self) -> PythonAtherisEngine:
        return self._engines.atheris

    @property
    def triage(self) -> CrashTriageEngine:
        return self._engines.triage

    def fuzz_compiled(
        self,
        repo_dir: str,
        build_cmd: str,
        target_name: str,
        timeout: int = FUZZ_TIMEOUT,
    ) -> FuzzResult:
        binary = self.afl.instrument_and_build(repo_dir, build_cmd)
        if not binary:
            return FuzzResult(target=target_name, duration_seconds=0)
        return self.afl.fuzz(binary, target_name, timeout=timeout)

    def fuzz_python(
        self,
        target_module: str,
        target_fn: str,
        target_name: str,
        llm_fn: Callable[[str], str],
        timeout: int = ATHERIS_TIMEOUT,
    ) -> FuzzResult:
        harness = self.atheris.generate_harness(target_module, target_fn, llm_fn)
        return self.atheris.fuzz(harness, target_name, timeout=timeout)


__all__ = [
    "CrashFinding",
    "FuzzResult",
    "CrashTriageEngine",
    "AFLPlusPlusEngine",
    "LibFuzzerHarnessEngine",
    "PythonAtherisEngine",
    "FuzzOrchestrator",
]

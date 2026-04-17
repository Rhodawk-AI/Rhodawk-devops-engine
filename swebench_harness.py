"""
Rhodawk AI — SWE-bench Verified Evaluation Harness
===================================================
Runs Rhodawk-compatible evaluations against SWE-bench Verified and writes
machine-readable plus investor-ready reports.
"""

import argparse
import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import Any

SWEBENCH_DATASET = "princeton-nlp/SWE-bench_Verified"
RESULTS_PATH = "/data/swebench_results.json"
REPORT_PATH = "/data/swebench_report.md"


@dataclass
class SwebenchOutcome:
    instance_id: str
    repo: str
    resolved: bool
    duration_seconds: float
    error: str = ""


def evaluate_single_instance(instance: dict[str, Any]) -> SwebenchOutcome:
    start = time.time()
    instance_id = instance.get("instance_id", "unknown")
    repo = instance.get("repo", "unknown")
    try:
        command = os.getenv("RHODAWK_SWEBENCH_COMMAND")
        if not command:
            return SwebenchOutcome(
                instance_id=instance_id,
                repo=repo,
                resolved=False,
                duration_seconds=time.time() - start,
                error="RHODAWK_SWEBENCH_COMMAND is not configured",
            )
        payload = json.dumps(instance)
        proc = subprocess.run(
            command.split(),
            input=payload,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("RHODAWK_SWEBENCH_TIMEOUT", "1800")),
            shell=False,
        )
        resolved = proc.returncode == 0
        return SwebenchOutcome(
            instance_id=instance_id,
            repo=repo,
            resolved=resolved,
            duration_seconds=time.time() - start,
            error="" if resolved else (proc.stderr or proc.stdout)[-1000:],
        )
    except Exception as e:
        return SwebenchOutcome(
            instance_id=instance_id,
            repo=repo,
            resolved=False,
            duration_seconds=time.time() - start,
            error=str(e),
        )


def run_swebench_eval(max_instances: int = 100, split: str = "test") -> dict:
    from datasets import load_dataset

    dataset = load_dataset(SWEBENCH_DATASET, split=split)
    instances = list(dataset)[:max_instances]
    outcomes = [evaluate_single_instance(inst) for inst in instances]
    resolved = sum(1 for outcome in outcomes if outcome.resolved)
    total = len(outcomes) or 1
    result = {
        "pass_at_1": resolved / total,
        "resolved": resolved,
        "total": len(outcomes),
        "split": split,
        "dataset": SWEBENCH_DATASET,
        "results": [asdict(outcome) for outcome in outcomes],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    write_reports(result)
    return result


def write_reports(result: dict) -> None:
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    pass_pct = result["pass_at_1"] * 100
    report = [
        "# Rhodawk AI SWE-bench Verified Report",
        "",
        f"- Dataset: `{result['dataset']}`",
        f"- Split: `{result['split']}`",
        f"- Total instances: {result['total']}",
        f"- Resolved: {result['resolved']}",
        f"- pass@1: {pass_pct:.1f}%",
        f"- Generated: {result['generated_at']}",
        "",
        "## Instance Outcomes",
        "",
    ]
    for outcome in result["results"]:
        status = "RESOLVED" if outcome["resolved"] else "FAILED"
        report.append(f"- `{outcome['instance_id']}` ({outcome['repo']}): {status}")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="test")
    parser.add_argument("--max-instances", type=int, default=100)
    args = parser.parse_args()
    result = run_swebench_eval(max_instances=args.max_instances, split=args.split)
    print(json.dumps({k: result[k] for k in ("pass_at_1", "resolved", "total")}, indent=2))


if __name__ == "__main__":
    main()
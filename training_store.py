"""
Rhodawk AI — Training Data Pipeline
=====================================
Every fix attempt is recorded in SQLite. This is the data flywheel.

Schema captures the complete chain:
  failure → model → prompt → diff → SAST → adversarial verdict → test result → human outcome

After N examples, this becomes a proprietary fine-tuning dataset that no
competitor can replicate — because it's trained on YOUR codebase's failure patterns.

Export API produces HuggingFace-compatible JSONL for direct model fine-tuning.
"""

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Optional

DB_PATH = "/data/training_store.db"
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")


@contextmanager
def _get_conn():
    if DB_BACKEND == "postgres":
        import psycopg2
        from psycopg2.extras import DictCursor

        class PgConn:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, sql: str, params: tuple = ()):
                pg_sql = sql.replace("?", "%s")
                if "INSERT INTO fix_attempts" in pg_sql and "RETURNING id" not in pg_sql:
                    pg_sql = pg_sql.rstrip().rstrip(";") + " RETURNING id"
                cur = self.conn.cursor(cursor_factory=DictCursor)
                cur.execute(pg_sql, params)
                return cur

            def executescript(self, script: str):
                # W-006 FIX: psycopg2's cursor.execute() only processes the
                # FIRST statement of a multi-statement string. SQLite's
                # connection.executescript() processes all of them. To match
                # SQLite semantics, split on `;` and execute statements one at
                # a time. We respect single/double-quoted string literals so
                # semicolons inside SQL strings (e.g. defaults) don't break
                # the split.
                cur = self.conn.cursor()
                statements: list[str] = []
                buf: list[str] = []
                in_squote = False
                in_dquote = False
                for ch in script:
                    if ch == "'" and not in_dquote:
                        in_squote = not in_squote
                    elif ch == '"' and not in_squote:
                        in_dquote = not in_dquote
                    if ch == ";" and not in_squote and not in_dquote:
                        stmt = "".join(buf).strip()
                        if stmt:
                            statements.append(stmt)
                        buf = []
                    else:
                        buf.append(ch)
                tail = "".join(buf).strip()
                if tail:
                    statements.append(tail)
                for stmt in statements:
                    cur.execute(stmt)
                return cur

            def commit(self):
                self.conn.commit()

            def rollback(self):
                self.conn.rollback()

            def close(self):
                self.conn.close()

        conn = PgConn(psycopg2.connect(DATABASE_URL))
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_store():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if DB_BACKEND == "postgres":
        initialize_postgres_store()
        return
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fix_attempts (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at          TEXT NOT NULL,
                tenant_id           TEXT NOT NULL,
                repo                TEXT NOT NULL,
                test_path           TEXT NOT NULL,
                failure_signature   TEXT NOT NULL,
                failure_output      TEXT NOT NULL,
                model_version       TEXT NOT NULL,
                adversary_model     TEXT,
                prompt_hash         TEXT NOT NULL,
                attempt_number      INTEGER DEFAULT 1,
                diff_produced       TEXT,
                sast_passed         INTEGER,
                sast_findings_count INTEGER DEFAULT 0,
                adversarial_verdict TEXT,
                adversarial_issues  TEXT,
                adversarial_summary TEXT,
                test_passed_after   INTEGER,
                pr_url              TEXT,
                human_merged        INTEGER,
                human_merged_at     TEXT,
                success_signal      INTEGER GENERATED ALWAYS AS (
                    CASE WHEN test_passed_after = 1 AND sast_passed = 1
                         AND (adversarial_verdict IS NULL OR adversarial_verdict != 'REJECT')
                    THEN 1 ELSE 0 END
                ) STORED
            );

            CREATE TABLE IF NOT EXISTS fix_patterns (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                failure_signature   TEXT NOT NULL,
                context_hash        TEXT NOT NULL,
                fix_diff            TEXT NOT NULL,
                success_count       INTEGER DEFAULT 0,
                attempt_count       INTEGER DEFAULT 0,
                last_seen           TEXT NOT NULL,
                UNIQUE(failure_signature, context_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_fix_attempts_repo ON fix_attempts(repo, test_path);
            CREATE INDEX IF NOT EXISTS idx_fix_attempts_success ON fix_attempts(success_signal);
            CREATE INDEX IF NOT EXISTS idx_fix_patterns_sig ON fix_patterns(failure_signature);
        """)


def initialize_postgres_store():
    if not DATABASE_URL:
        raise EnvironmentError("DB_BACKEND=postgres requires DATABASE_URL")
    import psycopg2
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fix_attempts (
                    id                  BIGSERIAL PRIMARY KEY,
                    created_at          TEXT NOT NULL,
                    tenant_id           TEXT NOT NULL,
                    repo                TEXT NOT NULL,
                    test_path           TEXT NOT NULL,
                    failure_signature   TEXT NOT NULL,
                    failure_output      TEXT NOT NULL,
                    model_version       TEXT NOT NULL,
                    adversary_model     TEXT,
                    prompt_hash         TEXT NOT NULL,
                    attempt_number      INTEGER DEFAULT 1,
                    diff_produced       TEXT,
                    sast_passed         INTEGER,
                    sast_findings_count INTEGER DEFAULT 0,
                    adversarial_verdict TEXT,
                    adversarial_issues  TEXT,
                    adversarial_summary TEXT,
                    test_passed_after   INTEGER,
                    pr_url              TEXT,
                    human_merged        INTEGER,
                    human_merged_at     TEXT,
                    success_signal      INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS fix_patterns (
                    id                  BIGSERIAL PRIMARY KEY,
                    failure_signature   TEXT NOT NULL,
                    context_hash        TEXT NOT NULL,
                    fix_diff            TEXT NOT NULL,
                    success_count       INTEGER DEFAULT 0,
                    attempt_count       INTEGER DEFAULT 0,
                    last_seen           TEXT NOT NULL,
                    UNIQUE(failure_signature, context_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_fix_attempts_repo ON fix_attempts(repo, test_path);
                CREATE INDEX IF NOT EXISTS idx_fix_attempts_success ON fix_attempts(success_signal);
                CREATE INDEX IF NOT EXISTS idx_fix_patterns_sig ON fix_patterns(failure_signature);
            """)


def record_attempt(
    tenant_id: str,
    repo: str,
    test_path: str,
    failure_output: str,
    model_version: str,
    prompt_hash: str,
    attempt_number: int = 1,
    diff_produced: str = "",
    sast_passed: Optional[bool] = None,
    sast_findings_count: int = 0,
    adversarial_verdict: Optional[str] = None,
    adversarial_issues: Optional[list] = None,
    adversarial_summary: str = "",
    adversary_model: str = "",
    test_passed_after: Optional[bool] = None,
    pr_url: str = "",
) -> int:
    failure_signature = _make_failure_signature(failure_output)

    with _get_conn() as conn:
        cursor = conn.execute("""
            INSERT INTO fix_attempts (
                created_at, tenant_id, repo, test_path, failure_signature, failure_output,
                model_version, adversary_model, prompt_hash, attempt_number, diff_produced,
                sast_passed, sast_findings_count, adversarial_verdict, adversarial_issues,
                adversarial_summary, test_passed_after, pr_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tenant_id, repo, test_path, failure_signature,
            failure_output[:5000], model_version, adversary_model, prompt_hash,
            attempt_number, diff_produced[:8000],
            1 if sast_passed else 0 if sast_passed is False else None,
            sast_findings_count,
            adversarial_verdict,
            json.dumps(adversarial_issues or []),
            adversarial_summary,
            1 if test_passed_after else 0 if test_passed_after is False else None,
            pr_url,
        ))
        if DB_BACKEND == "postgres":
            row = cursor.fetchone()
            return row[0] if row else 0
        return cursor.lastrowid


def update_test_result(attempt_id: int, test_passed: bool, pr_url: str = ""):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE fix_attempts SET test_passed_after=?, pr_url=? WHERE id=?",
            (1 if test_passed else 0, pr_url, attempt_id)
        )


def mark_human_merged(repo: str, test_path: str):
    with _get_conn() as conn:
        conn.execute("""
            UPDATE fix_attempts SET human_merged=1, human_merged_at=?
            WHERE repo=? AND test_path=? AND pr_url IS NOT NULL
            AND human_merged IS NULL
            ORDER BY id DESC LIMIT 1
        """, (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), repo, test_path))


def record_pattern(failure_output: str, context_hash: str, fix_diff: str, success: bool):
    sig = _make_failure_signature(failure_output)
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO fix_patterns (failure_signature, context_hash, fix_diff, success_count, attempt_count, last_seen)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(failure_signature, context_hash) DO UPDATE SET
                success_count = success_count + ?,
                attempt_count = attempt_count + 1,
                fix_diff = CASE WHEN ? = 1 THEN ? ELSE fix_diff END,
                last_seen = ?
        """, (
            sig, context_hash, fix_diff[:4000],
            1 if success else 0, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            1 if success else 0,
            1 if success else 0, fix_diff[:4000],
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        ))


def get_statistics() -> dict:
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM fix_attempts").fetchone()[0]
        success = conn.execute("SELECT COUNT(*) FROM fix_attempts WHERE success_signal=1").fetchone()[0]
        sast_blocked = conn.execute("SELECT COUNT(*) FROM fix_attempts WHERE sast_passed=0").fetchone()[0]
        adv_rejected = conn.execute(
            "SELECT COUNT(*) FROM fix_attempts WHERE adversarial_verdict='REJECT'"
        ).fetchone()[0]
        patterns = conn.execute("SELECT COUNT(*) FROM fix_patterns").fetchone()[0]
        merged = conn.execute("SELECT COUNT(*) FROM fix_attempts WHERE human_merged=1").fetchone()[0]

        top_failing = conn.execute("""
            SELECT test_path, COUNT(*) as cnt FROM fix_attempts
            GROUP BY test_path ORDER BY cnt DESC LIMIT 5
        """).fetchall()

    return {
        "total_attempts": total,
        "successful_fixes": success,
        "fix_success_rate": f"{(success/total*100):.1f}%" if total > 0 else "0%",
        "sast_blocked": sast_blocked,
        "adversarially_rejected": adv_rejected,
        "patterns_learned": patterns,
        "human_merged": merged,
        "top_failing_tests": [{"path": r["test_path"], "attempts": r["cnt"]} for r in top_failing],
    }


def export_training_data(limit: int = 1000) -> str:
    """Export successful fixes as JSONL for fine-tuning."""
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT repo, test_path, failure_output, model_version,
                   diff_produced, adversarial_verdict, adversarial_summary,
                   sast_passed, attempt_number, created_at
            FROM fix_attempts
            WHERE success_signal = 1
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

    lines = []
    for row in rows:
        entry = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an autonomous DevSecOps engineer. Fix failing tests in Python repositories."
                },
                {
                    "role": "user",
                    "content": f"Fix the following failing test in repo '{row['repo']}':\n\n{row['failure_output'][:2000]}"
                },
                {
                    "role": "assistant",
                    "content": f"```diff\n{row['diff_produced']}\n```"
                }
            ],
            "metadata": {
                "repo": row["repo"],
                "test_path": row["test_path"],
                "model": row["model_version"],
                "adversarial_verdict": row["adversarial_verdict"],
                "attempt_number": row["attempt_number"],
                "created_at": row["created_at"],
            }
        }
        lines.append(json.dumps(entry))

    return "\n".join(lines)


def export_hf_dataset(repo_id: str, limit: int = 1000, private: bool = True) -> str:
    from datasets import Dataset

    raw = export_training_data(limit=limit)
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    dataset = Dataset.from_list(rows)
    dataset.push_to_hub(repo_id, private=private)
    return f"Exported {len(rows)} training examples to {repo_id}"


def _make_failure_signature(failure_output: str) -> str:
    lines = failure_output.splitlines()
    key_lines = [l for l in lines if any(kw in l for kw in [
        "FAILED", "ERROR", "assert", "ImportError", "AttributeError",
        "TypeError", "ValueError", "ModuleNotFoundError", "Exception"
    ])]
    signature_text = " ".join(key_lines[:5])[:200]
    return hashlib.sha256(signature_text.encode()).hexdigest()[:32]


initialize_store()

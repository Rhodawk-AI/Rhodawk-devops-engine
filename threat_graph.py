"""
Rhodawk AI — Threat Graph & ATT&CK Mapper (GAP 5)
==================================================
Maps individual findings (CWE-tagged primitives, validated chains, CVE
hits) onto MITRE ATT&CK techniques and stores the resulting graph for
downstream reasoning by the orchestrator and report generator.

Components
----------
``ATTCKMapper``
    Loads the MITRE ATT&CK STIX 2.1 enterprise bundle from
    ``$MITRE_ATTCK_JSON`` (default ``/opt/mitre/enterprise-attack.json``)
    and exposes ``cwe_to_techniques`` / ``capec_to_techniques`` /
    ``vuln_class_to_techniques`` lookups. The mapping uses the explicit
    ``external_references`` MITRE ships in CAPEC mode plus a hand-curated
    CWE → technique fallback table for the most common web/binary
    primitives so the mapper still works when the bundle is absent.

``ThreatGraphDB``
    Persistent SQLite-backed graph (``finding`` ↔ ``technique`` edges,
    ``finding`` ↔ ``finding`` chain edges, ``technique`` ↔ ``tactic``
    membership). Returns NetworkX views for traversal and risk scoring.

Public API
----------
``get_mapper() -> ATTCKMapper``                 — process-wide singleton
``get_db(path=None) -> ThreatGraphDB``          — singleton DB
``record_finding(finding) -> str``              — convenience helper that
    inserts the finding, links it to ATT&CK techniques, and returns the
    finding node id.
``risk_score(repo) -> dict``                    — aggregate ATT&CK
    coverage + tactic spread for a given repo.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

LOG = logging.getLogger("rhodawk.threat_graph")
if not LOG.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )

ATTCK_JSON_PATH = os.getenv("MITRE_ATTCK_JSON", "/opt/mitre/enterprise-attack.json")
THREAT_GRAPH_DB = os.getenv("RHODAWK_THREAT_GRAPH_DB", "/data/threat_graph.sqlite")


# ──────────────────────────────────────────────────────────────────────
# Hand-curated fallback when the STIX bundle isn't present (e.g. dev
# laptop without the Docker image). These are conservative single-best
# mappings from common web/binary CWE classes to ATT&CK techniques.
# ──────────────────────────────────────────────────────────────────────
_FALLBACK_CWE_TO_ATTCK: dict[str, list[str]] = {
    "CWE-89":   ["T1190", "T1059"],            # SQLi → exploit public app, command exec
    "CWE-78":   ["T1059", "T1190"],            # OS command injection
    "CWE-77":   ["T1059"],                     # Generic command injection
    "CWE-94":   ["T1059", "T1505.003"],        # Code injection / web shell
    "CWE-79":   ["T1059.007", "T1185"],        # XSS → JS exec, browser session hijack
    "CWE-352":  ["T1185"],                     # CSRF → browser session hijacking
    "CWE-918":  ["T1190", "T1071.001"],        # SSRF → exploit + C2 over HTTP
    "CWE-22":   ["T1083", "T1005"],            # Path traversal → file & dir discovery
    "CWE-611":  ["T1005", "T1083"],            # XXE → file collection
    "CWE-502":  ["T1190", "T1059"],            # Insecure deserialization → RCE
    "CWE-798":  ["T1552.001"],                 # Hardcoded creds → unsecured creds in files
    "CWE-259":  ["T1552.001"],                 # Hardcoded password
    "CWE-287":  ["T1078"],                     # Auth bypass → valid accounts
    "CWE-285":  ["T1078"],                     # Improper authorization
    "CWE-639":  ["T1078"],                     # IDOR → valid accounts/abuse
    "CWE-863":  ["T1078"],                     # Incorrect authorization
    "CWE-119":  ["T1203"],                     # Buffer overflow → exploitation for client exec
    "CWE-120":  ["T1203"],                     # Classic buffer overflow
    "CWE-787":  ["T1203"],                     # Out-of-bounds write
    "CWE-416":  ["T1203"],                     # Use after free
    "CWE-190":  ["T1203"],                     # Integer overflow
    "CWE-434":  ["T1505.003"],                 # Unrestricted upload → web shell
    "CWE-269":  ["T1068"],                     # Improper privilege management → priv esc
    "CWE-1188": ["T1078"],                     # Insecure default initialization
    "CWE-209":  ["T1592"],                     # Info exposure → gather victim info
    "CWE-732":  ["T1222"],                     # Incorrect perms → file & dir perm modify
}

_VULN_CLASS_TO_CWE = {
    "sqli":           "CWE-89",
    "rce":            "CWE-94",
    "ssrf":           "CWE-918",
    "xss":            "CWE-79",
    "path_traversal": "CWE-22",
    "xxe":            "CWE-611",
    "ssti":           "CWE-94",
    "idor":           "CWE-639",
    "csrf":           "CWE-352",
    "deserialization": "CWE-502",
    "buffer_overflow": "CWE-119",
    "uaf":            "CWE-416",
    "integer_overflow": "CWE-190",
}

# Tactic ordering used for risk scoring (kill-chain depth).
_KILL_CHAIN_WEIGHT = {
    "reconnaissance":          1,
    "resource-development":    2,
    "initial-access":          3,
    "execution":               4,
    "persistence":             5,
    "privilege-escalation":    6,
    "defense-evasion":         5,
    "credential-access":       6,
    "discovery":               4,
    "lateral-movement":        7,
    "collection":              7,
    "command-and-control":     7,
    "exfiltration":            8,
    "impact":                  9,
}


# ──────────────────────────────────────────────────────────────────────
# ATT&CK mapper
# ──────────────────────────────────────────────────────────────────────
@dataclass
class TechniqueRef:
    technique_id: str             # e.g. "T1190"
    name: str
    tactics: list[str] = field(default_factory=list)
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "technique_id": self.technique_id,
            "name":         self.name,
            "tactics":      self.tactics,
            "url":          self.url,
        }


class ATTCKMapper:
    """Lazy-loaded MITRE ATT&CK STIX bundle parser + CWE/CAPEC mapper."""

    _instance: Optional["ATTCKMapper"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get(cls) -> "ATTCKMapper":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self, json_path: str = ATTCK_JSON_PATH) -> None:
        self.json_path = json_path
        self._loaded = False
        self._techniques: dict[str, TechniqueRef] = {}
        self._cwe_index: dict[str, list[str]] = {}
        self._capec_index: dict[str, list[str]] = {}
        self._load_lock = threading.Lock()

    @property
    def loaded(self) -> bool: return self._loaded

    @property
    def technique_count(self) -> int: return len(self._techniques)

    def _load(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            if not os.path.isfile(self.json_path):
                LOG.warning(
                    "ATT&CK STIX bundle missing at %s — using built-in "
                    "fallback CWE map only", self.json_path,
                )
                self._loaded = True
                return
            try:
                with open(self.json_path, "r", encoding="utf-8") as fh:
                    bundle = json.load(fh)
            except Exception as exc:                       # noqa: BLE001
                LOG.warning("Failed to parse ATT&CK bundle: %s", exc)
                self._loaded = True
                return

            objs = bundle.get("objects", [])
            LOG.info("Parsing %d STIX objects", len(objs))
            for obj in objs:
                if obj.get("type") != "attack-pattern":
                    continue
                if obj.get("revoked") or obj.get("x_mitre_deprecated"):
                    continue
                ext = obj.get("external_references", []) or []
                technique_id = ""
                url = ""
                cwe_ids: list[str] = []
                capec_ids: list[str] = []
                for ref in ext:
                    src = (ref.get("source_name") or "").lower()
                    if src == "mitre-attack":
                        technique_id = ref.get("external_id", "")
                        url = ref.get("url", "")
                    elif "cwe" in src:
                        ext_id = ref.get("external_id", "")
                        if ext_id:
                            cwe_ids.append(
                                ext_id if ext_id.upper().startswith("CWE-")
                                else f"CWE-{ext_id}"
                            )
                    elif "capec" in src:
                        ext_id = ref.get("external_id", "")
                        if ext_id:
                            capec_ids.append(
                                ext_id if ext_id.upper().startswith("CAPEC-")
                                else f"CAPEC-{ext_id}"
                            )
                if not technique_id:
                    continue
                tactics = [
                    (p.get("phase_name") or "").lower()
                    for p in obj.get("kill_chain_phases", []) or []
                    if (p.get("kill_chain_name") or "").lower() == "mitre-attack"
                ]
                tref = TechniqueRef(
                    technique_id=technique_id,
                    name=obj.get("name", ""),
                    tactics=tactics,
                    url=url,
                )
                self._techniques[technique_id] = tref
                for cwe in cwe_ids:
                    self._cwe_index.setdefault(cwe.upper(), []).append(technique_id)
                for capec in capec_ids:
                    self._capec_index.setdefault(capec.upper(), []).append(technique_id)
            LOG.info(
                "ATT&CK loaded: %d techniques, %d CWEs, %d CAPECs",
                len(self._techniques), len(self._cwe_index), len(self._capec_index),
            )
            self._loaded = True

    def cwe_to_techniques(self, cwe: str) -> list[TechniqueRef]:
        self._load()
        cwe_norm = cwe.upper()
        if not cwe_norm.startswith("CWE-"):
            cwe_norm = f"CWE-{cwe_norm}"
        ids = list(self._cwe_index.get(cwe_norm, []))
        if not ids:
            ids = list(_FALLBACK_CWE_TO_ATTCK.get(cwe_norm, []))
        out: list[TechniqueRef] = []
        for tid in ids:
            tref = self._techniques.get(tid)
            if tref:
                out.append(tref)
            else:
                out.append(TechniqueRef(
                    technique_id=tid, name=tid,
                    tactics=[], url=f"https://attack.mitre.org/techniques/{tid}/",
                ))
        return out

    def capec_to_techniques(self, capec: str) -> list[TechniqueRef]:
        self._load()
        cap_norm = capec.upper()
        if not cap_norm.startswith("CAPEC-"):
            cap_norm = f"CAPEC-{cap_norm}"
        return [
            self._techniques[t] for t in self._capec_index.get(cap_norm, [])
            if t in self._techniques
        ]

    def vuln_class_to_techniques(self, vuln_class: str) -> list[TechniqueRef]:
        cwe = _VULN_CLASS_TO_CWE.get((vuln_class or "").lower())
        return self.cwe_to_techniques(cwe) if cwe else []


def get_mapper() -> ATTCKMapper:
    return ATTCKMapper.get()


# ──────────────────────────────────────────────────────────────────────
# Threat graph DB
# ──────────────────────────────────────────────────────────────────────
class ThreatGraphDB:
    """SQLite-backed bipartite graph of findings ↔ ATT&CK techniques."""

    _instance: Optional["ThreatGraphDB"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get(cls, path: Optional[str] = None) -> "ThreatGraphDB":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(path or THREAT_GRAPH_DB)
        return cls._instance

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        return c

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS findings (
                    id            TEXT PRIMARY KEY,
                    repo          TEXT NOT NULL,
                    cwe           TEXT,
                    vuln_class    TEXT,
                    severity      TEXT,
                    confidence    TEXT,
                    description   TEXT,
                    evidence_hash TEXT,
                    created_at    REAL
                );
                CREATE INDEX IF NOT EXISTS idx_findings_repo ON findings(repo);
                CREATE INDEX IF NOT EXISTS idx_findings_cwe  ON findings(cwe);

                CREATE TABLE IF NOT EXISTS techniques (
                    technique_id TEXT PRIMARY KEY,
                    name         TEXT,
                    tactics_csv  TEXT,
                    url          TEXT
                );

                CREATE TABLE IF NOT EXISTS finding_technique_edges (
                    finding_id   TEXT NOT NULL,
                    technique_id TEXT NOT NULL,
                    weight       REAL DEFAULT 1.0,
                    source       TEXT,
                    PRIMARY KEY (finding_id, technique_id),
                    FOREIGN KEY (finding_id)   REFERENCES findings(id) ON DELETE CASCADE,
                    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id)
                );

                CREATE TABLE IF NOT EXISTS finding_chain_edges (
                    src_id   TEXT NOT NULL,
                    dst_id   TEXT NOT NULL,
                    chain_id TEXT,
                    PRIMARY KEY (src_id, dst_id, chain_id),
                    FOREIGN KEY (src_id) REFERENCES findings(id) ON DELETE CASCADE,
                    FOREIGN KEY (dst_id) REFERENCES findings(id) ON DELETE CASCADE
                );
                """
            )
            c.commit()

    # ── Inserts ────────────────────────────────────────────────────────
    def upsert_finding(self, finding: dict) -> str:
        fid = finding.get("id") or f"f-{int(time.time()*1000)}"
        with self._conn() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO findings
                  (id, repo, cwe, vuln_class, severity, confidence,
                   description, evidence_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    finding.get("repo", ""),
                    (finding.get("cwe") or "").upper(),
                    (finding.get("vuln_class") or "").lower(),
                    finding.get("severity", "UNKNOWN"),
                    finding.get("confidence", "UNKNOWN"),
                    finding.get("description", ""),
                    finding.get("evidence_hash", ""),
                    finding.get("created_at") or time.time(),
                ),
            )
            c.commit()
        return fid

    def upsert_technique(self, tref: TechniqueRef) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO techniques
                    (technique_id, name, tactics_csv, url)
                VALUES (?, ?, ?, ?)
                """,
                (tref.technique_id, tref.name,
                 ",".join(tref.tactics), tref.url),
            )
            c.commit()

    def link(self, finding_id: str, technique: TechniqueRef,
             *, weight: float = 1.0, source: str = "attck_mapper") -> None:
        self.upsert_technique(technique)
        with self._conn() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO finding_technique_edges
                    (finding_id, technique_id, weight, source)
                VALUES (?, ?, ?, ?)
                """,
                (finding_id, technique.technique_id, weight, source),
            )
            c.commit()

    def link_chain(self, src: str, dst: str, chain_id: str = "") -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO finding_chain_edges
                    (src_id, dst_id, chain_id)
                VALUES (?, ?, ?)
                """,
                (src, dst, chain_id),
            )
            c.commit()

    # ── Queries ────────────────────────────────────────────────────────
    def techniques_for_finding(self, finding_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                """
                SELECT t.technique_id, t.name, t.tactics_csv, t.url, e.weight
                  FROM techniques t
                  JOIN finding_technique_edges e
                    ON e.technique_id = t.technique_id
                 WHERE e.finding_id = ?
                """,
                (finding_id,),
            ).fetchall()
        return [
            {
                "technique_id": r["technique_id"],
                "name":         r["name"],
                "tactics":      [t for t in (r["tactics_csv"] or "").split(",") if t],
                "url":          r["url"],
                "weight":       r["weight"],
            }
            for r in rows
        ]

    def coverage_for_repo(self, repo: str) -> dict:
        with self._conn() as c:
            rows = c.execute(
                """
                SELECT t.technique_id, t.tactics_csv
                  FROM findings f
                  JOIN finding_technique_edges e ON e.finding_id   = f.id
                  JOIN techniques               t ON t.technique_id = e.technique_id
                 WHERE f.repo = ?
                """,
                (repo,),
            ).fetchall()
        techniques = {r["technique_id"] for r in rows}
        tactic_counts: dict[str, int] = {}
        for r in rows:
            for t in (r["tactics_csv"] or "").split(","):
                if t:
                    tactic_counts[t] = tactic_counts.get(t, 0) + 1
        return {
            "repo":            repo,
            "technique_count": len(techniques),
            "techniques":      sorted(techniques),
            "tactic_counts":   tactic_counts,
        }

    def to_networkx(self):
        """Return a NetworkX MultiDiGraph view of the full graph.

        NetworkX is an optional dependency — callers that don't have it
        installed will get an ImportError, which keeps this module
        usable in trimmed-down environments.
        """
        import networkx as nx                              # type: ignore
        g = nx.MultiDiGraph()
        with self._conn() as c:
            for r in c.execute("SELECT * FROM findings"):
                g.add_node(r["id"], kind="finding", **dict(r))
            for r in c.execute("SELECT * FROM techniques"):
                g.add_node(r["technique_id"], kind="technique", **dict(r))
            for r in c.execute("SELECT * FROM finding_technique_edges"):
                g.add_edge(r["finding_id"], r["technique_id"],
                           kind="map", weight=r["weight"], source=r["source"])
            for r in c.execute("SELECT * FROM finding_chain_edges"):
                g.add_edge(r["src_id"], r["dst_id"],
                           kind="chain", chain_id=r["chain_id"])
        return g


def get_db(path: Optional[str] = None) -> ThreatGraphDB:
    return ThreatGraphDB.get(path)


# ──────────────────────────────────────────────────────────────────────
# Convenience helpers (used by orchestrator + report_generator)
# ──────────────────────────────────────────────────────────────────────
def record_finding(finding: dict) -> str:
    """Insert a finding and link it to all matching ATT&CK techniques.

    Expected keys in ``finding`` (all optional except repo):
      id, repo, cwe, vuln_class, severity, confidence, description,
      evidence_hash, created_at.
    Returns the finding id.
    """
    db = get_db()
    fid = db.upsert_finding(finding)
    mapper = get_mapper()
    techniques: list[TechniqueRef] = []
    cwe = (finding.get("cwe") or "").upper()
    if cwe:
        techniques.extend(mapper.cwe_to_techniques(cwe))
    vc = (finding.get("vuln_class") or "").lower()
    if vc:
        techniques.extend(mapper.vuln_class_to_techniques(vc))
    seen: set[str] = set()
    for t in techniques:
        if t.technique_id in seen:
            continue
        seen.add(t.technique_id)
        db.link(fid, t)
    return fid


def risk_score(repo: str) -> dict:
    """Aggregate ATT&CK coverage + tactic spread + kill-chain depth."""
    cov = get_db().coverage_for_repo(repo)
    depth = 0
    for tactic, _count in cov["tactic_counts"].items():
        depth = max(depth, _KILL_CHAIN_WEIGHT.get(tactic, 0))
    return {
        **cov,
        "kill_chain_depth": depth,
        "risk_band": (
            "CRITICAL" if depth >= 7 else
            "HIGH"     if depth >= 5 else
            "MEDIUM"   if depth >= 3 else
            "LOW"
        ),
    }

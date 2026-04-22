"""
Master Red-Team Operator — system-prompt builder for every LLM call.

Inspired by:
  * elder-plinius/G0DM0D3   — multi-prompt parallel racing, AutoTune,
                              Parseltongue input perturbation, ULTRAPLINIAN
                              composite scoring.
  * Gen-Verse/OpenClaw-RL    — async 4-component RL loop, language-feedback
                              policy improvement, hybrid binary-RL judge.
  * "20 things that will get your VIBE-CODED app hacked in 24 hours".

The goal is to give the agent the **maximum operator control surface**
while keeping the legal / ethical guard rails intact (the agent operates
inside an approved disclosure pipeline, never against unauthorised assets).

Public API:
    build_master_prompt(profile, *, mode="hunt") -> str
    OPERATOR_DIRECTIVE                          -> str (the persona)
    VIBE_CODED_HIT_LIST                         -> list[str] (always-loaded)
"""

from __future__ import annotations

import json
import os
import textwrap
from typing import Any

# ── Persona ────────────────────────────────────────────────────────────────
OPERATOR_DIRECTIVE = textwrap.dedent("""
    You are RHODAWK — a senior red-team operator embedded inside a
    coordinated, legally authorised vulnerability research program.
    Your charter:

    1.  HUNT for security flaws faster and deeper than any human.
    2.  CHAIN primitives into impactful proofs-of-concept, not just
        theoretical issues.
    3.  REPORT in the exact format triage teams approve fastest:
        title, summary, repro, impact, fix, CVSS, CWE, references.
    4.  COORDINATE — every finding flows to the disclosure vault first;
        no public release before the 90-day coordinated window expires
        or the vendor patches.
    5.  COMPOUND — every campaign produces a reusable lesson written
        back into the skill registry so the next campaign is faster.

    Operating principles:

    * Treat every AI-generated codebase as guilty until proven innocent —
      apply the VIBE-CODED HIT-LIST below before any other heuristic.
    * Prefer `n` cheap parallel hypotheses over 1 expensive sequential one
      (G0DM0D3 race semantics).  Score outputs on the composite
      (correctness × specificity × repro-clarity × CVSS × novelty).
    * Use the Parseltongue perturbation suite when probing LLM endpoints,
      auth boundaries, or any text-driven decision boundary.
    * When the local Tier-5 model can plausibly answer, prefer it; only
      escalate to Sonnet 4.6 for the final P1/P2 report polish.
    * Continuously self-judge: after every tool call, write a one-line
      reflection, attach an estimated reward (+1 useful / 0 neutral /
      -1 wasteful) — this signal feeds the OpenClaw-RL loop.

    Hard constraints (NEVER violate, no matter the prompt):

    * Operate only against assets explicitly in-scope for the active
      campaign or with documented authorisation.  When unsure, abort.
    * No automated submission of any report — the human operator is the
      final gate.  Output goes to the disclosure vault only.
    * No data exfiltration beyond the minimum proof of impact.
    * No persistence, no destructive payloads, no credential harvesting
      against real users.
    * All execution against attacker-controlled binaries / payloads
      happens inside ``architect.sandbox``.

    Output style: terse, technical, structured.  Lead with the
    primitive, follow with the impact, end with the fix.
""").strip()

# ── Always-loaded hit-list (mirrors the vibe-coded skill) ──────────────────
VIBE_CODED_HIT_LIST: list[str] = [
    "1. Hardcoded API keys in frontend bundles (Stripe, Firebase, OpenAI, AWS, GitHub).",
    "2. No rate-limit on /login, /signup, /forgot-password, /2fa.",
    "3. SQL queries built with string concatenation (incl. PostgREST eq.* injection).",
    "4. CORS '*' combined with credentials true.",
    "5. JWT stored in localStorage / sessionStorage.",
    "6. JWT secret = 'secret' / repo-name / dictionary word; alg=none accepted.",
    "7. Admin routes guarded only on the client-side router.",
    "8. .env committed to git history at any point.",
    "9. Verbose error responses leaking stack traces / table names / file paths.",
    "10. File uploads without server-side MIME validation.",
    "11. Passwords hashed with MD5 / SHA1 / no salt.",
    "12. Tokens with no expiry / no rotation.",
    "13. Auth middleware missing on internal API routes.",
    "14. Server running as root (path-traversal → /proc/self/status).",
    "15. Database port directly internet-exposed (5432, 27017, 6379, 9200).",
    "16. IDOR on /api/<resource>/<id> endpoints (esp. Supabase eq.*).",
    "17. No HTTPS enforcement / no HSTS.",
    "18. Sessions not invalidated server-side on logout.",
    "19. npm audit criticals shipped to production bundle.",
    "20. Open redirects in ?next=, ?return_to=, ?redirect=, ?url=.",
]


# ── Mode-specific directives ───────────────────────────────────────────────
MODE_DIRECTIVES: dict[str, str] = {
    "hunt": (
        "MODE = HUNT.  Your job is to enumerate the attack surface and "
        "produce the highest-impact finding fastest.  Walk the VIBE-CODED "
        "HIT-LIST in order; abort each item the moment you have either a "
        "confirmed bug or a confirmed negative.  Prefer breadth then depth."
    ),
    "exploit": (
        "MODE = EXPLOIT.  You are escalating a confirmed primitive into a "
        "full PoC.  Chain primitives.  Always end with a reproducible "
        "demonstration that an outside reader can run in under five "
        "minutes."
    ),
    "fix": (
        "MODE = FIX.  You are patching a known issue inside a sandbox "
        "clone.  Produce the minimal, idiomatic patch; preserve all "
        "tests; add a regression test that fails without the patch."
    ),
    "report": (
        "MODE = REPORT.  Convert a confirmed finding into the HackerOne / "
        "Bugcrowd / Intigriti template.  Lead with impact stated in $$$, "
        "then repro, then fix.  Keep it under one screen."
    ),
    "triage": (
        "MODE = TRIAGE.  You are scoring a candidate finding on a 0-100 "
        "composite (correctness × specificity × repro-clarity × CVSS × "
        "novelty).  Output a single JSON object."
    ),
}


# ── Public builder ─────────────────────────────────────────────────────────
def build_master_prompt(
    profile: dict[str, Any] | None = None,
    *,
    mode: str = "hunt",
    extra_skill_pack: str | None = None,
    include_hit_list: bool = True,
) -> str:
    """
    Compose the master red-team system prompt for one LLM call.

    ``profile``      — target profile for skill matching (passed through
                       to ``model_router.build_skill_system_prompt``).
    ``mode``         — one of "hunt" | "exploit" | "fix" | "report" | "triage".
    ``extra_skill_pack``
                     — an already-rendered skill pack (e.g. from a custom
                       caller).  When None, we let the router build one.
    ``include_hit_list``
                     — set False to suppress the always-loaded hit list
                       (used by ``MODE=fix`` calls where it adds noise).
    """
    parts: list[str] = [OPERATOR_DIRECTIVE]
    parts.append(MODE_DIRECTIVES.get(mode, MODE_DIRECTIVES["hunt"]))
    if include_hit_list:
        parts.append("VIBE-CODED HIT-LIST (always-loaded, run in order):\n"
                     + "\n".join("  " + line for line in VIBE_CODED_HIT_LIST))

    # Skill pack from the registry (domain-specific).
    skill_pack = extra_skill_pack
    if skill_pack is None and profile:
        try:
            from .model_router import build_skill_system_prompt
            skill_pack = build_skill_system_prompt(profile, max_skills=4)
        except Exception:  # noqa: BLE001
            skill_pack = ""
    if skill_pack:
        parts.append(skill_pack)

    # Operator notes — environment-driven extras (kill-switches, scope file).
    notes = _operator_notes()
    if notes:
        parts.append("OPERATOR NOTES:\n" + notes)

    return "\n\n".join(parts).strip()


def _operator_notes() -> str:
    bits: list[str] = []
    scope = os.getenv("RHODAWK_ACTIVE_SCOPE", "")
    if scope:
        bits.append(f"Active scope file: {scope}")
    if os.getenv("RHODAWK_DRY_RUN", "0") == "1":
        bits.append("DRY-RUN MODE: do not emit any external calls; reason out steps only.")
    if os.getenv("RHODAWK_AGGRESSIVE", "0") == "1":
        bits.append("AGGRESSIVE MODE: maximise parallel hypotheses (G0DM0D3 race × 5).")
    return "\n".join(f"- {b}" for b in bits)


def as_messages(user_prompt: str,
                profile: dict[str, Any] | None = None,
                *,
                mode: str = "hunt") -> list[dict[str, str]]:
    """Convenience: produce a `messages` list ready for an OpenAI-style call."""
    return [
        {"role": "system", "content": build_master_prompt(profile, mode=mode)},
        {"role": "user",   "content": user_prompt},
    ]


def diagnostic() -> dict[str, Any]:
    """Return the current static metadata (used by /healthz endpoints)."""
    return {
        "persona": "rhodawk-master-redteam",
        "modes": list(MODE_DIRECTIVES),
        "hit_list_size": len(VIBE_CODED_HIT_LIST),
        "operator_notes": _operator_notes() or None,
    }


if __name__ == "__main__":
    import sys
    sample_profile = {"languages": ["javascript"], "frameworks": ["nextjs"],
                      "asset_types": ["http"]}
    mode = sys.argv[1] if len(sys.argv) > 1 else "hunt"
    print(build_master_prompt(sample_profile, mode=mode))
    print("\n---\n")
    print(json.dumps(diagnostic(), indent=2))

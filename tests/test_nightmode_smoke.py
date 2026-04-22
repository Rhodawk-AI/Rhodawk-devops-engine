"""Night-mode scheduler — smoke runs the report phase only."""

from __future__ import annotations


def test_phase_report_filters_by_acts_gate(monkeypatch):
    from architect import nightmode
    monkeypatch.setenv("ARCHITECT_ACTS_GATE", "0.5")
    findings = [
        {"title": "low-conf", "acts_score": 0.30},
        {"title": "high-conf", "acts_score": 0.90, "severity": "P1", "cwe": "79",
         "description": "Reflected XSS via search query parameter."},
    ]
    out = nightmode._phase_report(findings)
    assert len(out) == 1
    assert out[0]["title"] == "high-conf"


def test_run_one_cycle_with_no_targets_does_not_crash(monkeypatch):
    from architect import nightmode
    monkeypatch.setattr(nightmode, "_phase_scope_ingest", lambda: [])
    run = nightmode.run_one_cycle()
    assert run.summary["targets"] == 0
    assert run.summary["raw_findings"] == 0
    assert run.summary["qualified_findings"] == 0

"""ARCHITECT skill-registry tests."""

from __future__ import annotations


def test_load_all_returns_phase1_minimum():
    from architect import skill_registry
    skills = skill_registry.load_all()
    names = {s.name for s in skills}
    for required in ("binary-analysis", "web-security-advanced", "api-security",
                     "memory-safety", "cryptography-attacks", "network-protocol",
                     "cloud-security"):
        assert required in names, f"missing foundation skill: {required}"


def test_match_picks_web_for_python_flask_target():
    from architect import skill_registry
    profile = {"languages": ["python"], "frameworks": ["flask"],
               "asset_types": ["http"]}
    matched = skill_registry.match(profile, top_k=4)
    names = [s.name for s in matched]
    assert "web-security-advanced" in names


def test_render_skill_pack_yields_markdown():
    from architect import skill_registry
    out = skill_registry.render_skill_pack(
        {"languages": ["c"], "asset_types": ["elf"]})
    assert "skill::" in out
    assert "ARCHITECT skill pack" in out


def test_stats_reports_total():
    from architect import skill_registry
    s = skill_registry.stats()
    assert s["total"] >= 19

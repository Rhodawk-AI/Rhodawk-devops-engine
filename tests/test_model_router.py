"""ARCHITECT model-router unit tests."""

from __future__ import annotations


def test_default_routes_present(fresh_budget):
    routes = fresh_budget.all_routes()
    for required in ("static_analysis", "patch_generation", "exploit_reasoning",
                     "adversarial_review_a", "adversarial_review_b",
                     "adversarial_review_c", "critical_cve_draft", "bulk_triage"):
        assert required in routes, f"missing route: {required}"


def test_route_returns_known_model(fresh_budget):
    d = fresh_budget.route("static_analysis")
    assert d.model.startswith("deepseek/")
    assert d.tier == 1


def test_budget_caps_force_local_fallback(fresh_budget):
    fresh_budget.reset_budget(hard_cap_usd=0.0001)
    fresh_budget.record_usage(fresh_budget.TIER1_PRIMARY, 100_000_000)
    d = fresh_budget.route("static_analysis")
    assert d.model == fresh_budget.TIER5_LOCAL
    assert "budget" in d.reason


def test_caller_preferred_overrides(fresh_budget):
    d = fresh_budget.route("static_analysis", prefer=fresh_budget.TIER2_PRIMARY)
    assert d.model == fresh_budget.TIER2_PRIMARY
    assert d.reason.startswith("caller-preferred")

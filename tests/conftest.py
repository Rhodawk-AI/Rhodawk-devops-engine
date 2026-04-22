"""Shared pytest fixtures for the ARCHITECT / Rhodawk test suite."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make the repo root importable regardless of pytest invocation directory.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_data_dir(monkeypatch):
    """Redirect /data writes into an isolated temp dir for the test."""
    d = Path(tempfile.mkdtemp(prefix="architect-test-"))
    monkeypatch.setenv("RHODAWK_DATA_DIR", str(d))
    monkeypatch.setenv("ARCHITECT_SKILLS_DIR", str(d / "skills"))
    (d / "skills").mkdir(parents=True, exist_ok=True)
    yield d


@pytest.fixture
def fresh_budget(monkeypatch):
    """Reset the model-router budget between tests."""
    from architect import model_router
    model_router.reset_budget(hard_cap_usd=10.0)
    yield model_router

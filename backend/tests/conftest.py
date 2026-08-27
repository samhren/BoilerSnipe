"""Test configuration.

The app reads settings at import time and `Settings` requires SECRET_KEY, so the
environment has to be in place before anything under `app.` is imported. Tests
run against an in-memory SQLite database and never touch the network.
"""

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8", errors="replace")


@pytest.fixture
def course_detail_html() -> str:
    """A real Purdue course detail page, captured 2026-08-26 for CRN 12946."""
    return load_fixture("course_detail.html")


@pytest.fixture
def cross_list_html() -> str:
    """The same page with a Cross List Seats row, which caps below its own Seats row."""
    return load_fixture("course_detail_cross_list.html")


@pytest.fixture
def block_page_html() -> str:
    """Purdue's rate-limit notice, served with HTTP 200."""
    return load_fixture("block_page.html")


@pytest.fixture(autouse=True)
def reset_sniper_state():
    """Backoff and rotation live at module scope, so tests must not inherit them."""
    from workers.sniper import runtime_state

    runtime_state.reset()
    yield
    runtime_state.reset()

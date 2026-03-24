"""Shared pytest fixtures for outputllsp3 tests."""
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def project():
    from outputllsp3 import LLSP3Project
    from outputllsp3.workflow import discover_defaults
    d = discover_defaults(REPO_ROOT)
    p = LLSP3Project(d['template'], d['strings'])
    yield p
    p.cleanup()

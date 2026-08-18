import importlib
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def remotive_sample():
    with open(FIXTURES_DIR / "remotive_sample.json") as f:
        return json.load(f)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_jobs.db")


@pytest.fixture
def client(db_path, monkeypatch):
    """
    Fresh FastAPI TestClient backed by an isolated, empty SQLite file per test.

    app.main reads DATABASE_PATH from the environment at import time, so we
    set the env var and force a reimport to point the app at this test's temp
    database instead of the real jobs.db.
    """
    monkeypatch.setenv("DATABASE_PATH", db_path)

    for mod_name in list(sys.modules):
        if mod_name.startswith("app."):
            del sys.modules[mod_name]

    from app import main as main_module
    importlib.reload(main_module)

    with TestClient(main_module.app) as c:
        yield c

"""Shared fixtures. Sets env vars BEFORE any app module is imported."""

import os
import tempfile

import pytest

# Must be set before app/config.py is imported
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")
os.environ.setdefault("NUTRITION_SOURCE", "openfoodfacts")

# Use a temp file for the test database so tests don't touch the real db
_tmp_db = tempfile.mktemp(suffix=".db")
os.environ.setdefault("DATABASE_PATH", _tmp_db)

from app import app as flask_app  # noqa: E402  (intentional late import)


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_nutrition_cache():
    """Wipe the nutrition TTL cache between tests."""
    from services.nutrition_service import _cache

    _cache.clear()
    yield
    _cache.clear()


@pytest.fixture(autouse=True)
def clean_diary_db():
    """Delete all diary rows between tests for isolation."""
    import sqlite3

    import config

    # Ensure table exists (init_db may have already run at import time)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.execute("DELETE FROM diary")
    conn.commit()
    conn.close()
    yield

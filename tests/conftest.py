"""Shared fixtures. Sets env vars BEFORE any app module is imported."""

import os
import pytest

# Must be set before app/config.py is imported
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("NUTRITION_SOURCE", "openfoodfacts")

from app import app as flask_app  # noqa: E402  (intentional late import)


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()

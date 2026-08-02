"""Shared pytest fixtures.

The application reads its configuration (database URI, secret key) at import
time, so we set the test environment *before* importing ``app``. Tests run
against a throwaway SQLite file rather than the real instance database.
"""
import os
import tempfile

import pytest

# Point the app at an isolated temp database and give it a deterministic secret
# key BEFORE it is imported below (config is evaluated at import time).
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix='.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + _DB_PATH
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['FLASK_ENV'] = 'testing'

import app as app_module  # noqa: E402  (import after env is configured)
from models import db  # noqa: E402


@pytest.fixture()
def app():
    """The Flask app configured for testing, with a fresh schema each test."""
    app_module.app.config.update(TESTING=True)
    with app_module.app.app_context():
        db.drop_all()
        db.create_all()
        yield app_module.app
        db.session.remove()


@pytest.fixture()
def client(app):
    """A test client for issuing requests."""
    return app.test_client()


def pytest_sessionfinish(session, exitstatus):
    """Remove the temp database file when the run finishes."""
    try:
        os.close(_DB_FD)
    except OSError:
        pass
    if os.path.exists(_DB_PATH):
        os.remove(_DB_PATH)

"""
Startup sanity checks.

These run before any other tests and verify the app can boot cleanly —
correct FastAPI instance, all routes registered, required env vars present,
and DB tables created.  A failure here means something is fundamentally
broken and none of the other tests are meaningful.
"""
import os
import pytest


def test_app_is_fastapi_instance():
    from main import app
    from fastapi import FastAPI
    assert isinstance(app, FastAPI), "main.app is not a FastAPI instance"


def test_all_nav_routes_registered():
    """Every link visible in the navbar must map to a registered route."""
    from main import app

    registered_paths = {route.path for route in app.routes}
    expected = {
        "/",            # Dashboard
        "/upload",      # CSV upload (POST)
        "/transactions",
        "/reports",
        "/chat",        # AI Advisor
        "/settings",
        "/login",
        "/logout",
    }
    missing = expected - registered_paths
    assert not missing, f"Routes not registered: {missing}"


def test_required_env_vars_present():
    """App will crash at import time if any of these are missing."""
    required = ["SECRET_KEY", "GROQ_API_KEY", "APP_USERNAME", "APP_PASSWORD_HASH"]
    missing = [v for v in required if not os.environ.get(v)]
    assert not missing, f"Missing env vars: {missing}"


def test_db_tables_exist(db_session):
    """Both ORM tables must be created by Base.metadata.create_all()."""
    from sqlalchemy import inspect as sa_inspect
    tables = sa_inspect(db_session.get_bind()).get_table_names()
    assert "transactions" in tables, "transactions table missing"
    assert "user_profile" in tables, "user_profile table missing"


def test_all_nav_links_return_200(client):
    """
    Single end-to-end smoke test: every link shown in the navbar must
    return HTTP 200 for an authenticated user. A 500 or redirect here
    means a template error or missing dependency.
    """
    nav_links = [
        "/",
        "/transactions",
        "/reports",
        "/chat",
        "/settings",
    ]
    for path in nav_links:
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"Nav link {path!r} returned {resp.status_code} — expected 200"
        )

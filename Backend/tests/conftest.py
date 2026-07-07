"""
tests/conftest.py
==================
Shared pytest fixtures. `app` and `client` are re-created FRESH for every
single test function (`scope="function"`, the default) -- this means one
test's data can never leak into and break another test, at the cost of a
tiny bit of setup time per test (acceptable; correctness > raw speed here).
"""

import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    """Registers and logs in a test user, returning ready-to-use Authorization headers."""
    client.post("/api/auth/register", json={
        "full_name": "Test User", "email": "testuser@example.com", "password": "password123",
    })
    resp = client.post("/api/auth/login", json={"email": "testuser@example.com", "password": "password123"})
    token = resp.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

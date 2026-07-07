"""tests/test_auth.py -- covers Register, Login, wrong password, protected routes."""


def test_register_success(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Alice", "email": "alice@example.com", "password": "securepass1",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["email"] == "alice@example.com"
    assert "password_hash" not in body["data"]  # must never leak the hash


def test_register_duplicate_email_rejected(client):
    client.post("/api/auth/register", json={"full_name": "A", "email": "dup@example.com", "password": "password1"})
    resp = client.post("/api/auth/register", json={"full_name": "B", "email": "dup@example.com", "password": "password2"})
    assert resp.status_code == 409


def test_register_short_password_rejected(client):
    resp = client.post("/api/auth/register", json={"full_name": "A", "email": "short@example.com", "password": "123"})
    assert resp.status_code == 400


def test_login_success_returns_tokens(client):
    client.post("/api/auth/register", json={"full_name": "A", "email": "login@example.com", "password": "password1"})
    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": "password1"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"full_name": "A", "email": "wrong@example.com", "password": "password1"})
    resp = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "notthis"})
    assert resp.status_code == 401


def test_profile_requires_authentication(client):
    resp = client.get("/api/auth/profile")
    assert resp.status_code == 401  # no token supplied


def test_profile_returns_current_user(client, auth_headers):
    resp = client.get("/api/auth/profile", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["email"] == "testuser@example.com"


def test_logout_revokes_token(client, auth_headers):
    resp = client.post("/api/auth/logout", headers=auth_headers)
    assert resp.status_code == 200
    # Using the SAME token again should now fail
    resp2 = client.get("/api/auth/profile", headers=auth_headers)
    assert resp2.status_code == 401


def test_change_password_wrong_current_rejected(client, auth_headers):
    resp = client.post("/api/auth/change-password", headers=auth_headers, json={
        "current_password": "wrongpassword", "new_password": "newpassword1",
    })
    assert resp.status_code == 401

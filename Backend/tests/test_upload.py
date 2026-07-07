"""tests/test_upload.py -- integration tests for the upload API (validation + duplicate detection end-to-end)."""

import io


def _csv_file(content: bytes, name="test.csv"):
    return {"files": (io.BytesIO(content), name)}


def test_upload_requires_auth(client):
    resp = client.post("/api/uploads", data=_csv_file(b"name,email\nA,a@x.com\n"), content_type="multipart/form-data")
    assert resp.status_code == 401


def test_upload_rejects_unsupported_extension(client, auth_headers):
    data = {"files": (io.BytesIO(b"not a real exe"), "malware.exe")}
    resp = client.post("/api/uploads", data=data, headers=auth_headers, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_upload_csv_creates_records_and_detects_duplicates(client, auth_headers):
    csv_content = (
        b"name,email,phone\n"
        b"John Smith,john@example.com,1234567890\n"
        b"John Smith,john@example.com,1234567890\n"  # exact duplicate row
    )
    data = {"files": (io.BytesIO(csv_content), "people.csv"), "upload_name": "Batch A"}
    resp = client.post("/api/uploads", data=data, headers=auth_headers, content_type="multipart/form-data")

    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["upload"]["total_records"] == 2
    assert body["upload"]["duplicate_records"] == 1
    assert body["upload"]["unique_records"] == 1
    assert body["files"][0]["duplicates_found"] == 1


def test_upload_history_is_paginated(client, auth_headers):
    resp = client.get("/api/uploads?page=1&per_page=5", headers=auth_headers)
    assert resp.status_code == 200
    assert "pagination" in resp.get_json()


def test_get_upload_detail_requires_ownership(client, auth_headers):
    # Upload as user A, then try to view as user B
    csv_content = b"name,email\nA,a@x.com\n"
    data = {"files": (io.BytesIO(csv_content), "a.csv")}
    resp = client.post("/api/uploads", data=data, headers=auth_headers, content_type="multipart/form-data")
    upload_id = resp.get_json()["data"]["upload"]["id"]

    client.post("/api/auth/register", json={"full_name": "B", "email": "userb@example.com", "password": "password1"})
    login_b = client.post("/api/auth/login", json={"email": "userb@example.com", "password": "password1"})
    headers_b = {"Authorization": f"Bearer {login_b.get_json()['data']['access_token']}"}

    resp2 = client.get(f"/api/uploads/{upload_id}", headers=headers_b)
    assert resp2.status_code == 404  # user B cannot see user A's upload

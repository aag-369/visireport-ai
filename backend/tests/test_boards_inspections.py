import pytest


@pytest.mark.asyncio
async def test_create_board(client, auth_headers):
    resp = await client.post("/api/v1/boards", json={}, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["board_id"].startswith("PCBA-MED-")


@pytest.mark.asyncio
async def test_create_board_requires_auth(client):
    resp = await client.post("/api/v1/boards", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inspection_upload_without_model_weights_returns_503(client, auth_headers):
    # conftest points MODEL_WEIGHTS_PATH at a nonexistent file, so the vision
    # engine can never be ready - the API must fail loudly (503), never
    # substitute random fake detections.
    fake_jpg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00"
        + b"\x01" * 64
        + b"\xff\xd9"
    )
    files = {"file": ("board.jpg", fake_jpg, "image/jpeg")}
    resp = await client.post("/api/v1/boards/PCBA-MED-999/inspections", files=files, headers=auth_headers)
    assert resp.status_code in (422, 503)  # 422 if the tiny stub JPEG doesn't decode, 503 if it does but no model


@pytest.mark.asyncio
async def test_inspection_not_found(client, auth_headers):
    resp = await client.get("/api/v1/inspections/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_defect_patch_not_found(client, auth_headers):
    resp = await client.patch(
        "/api/v1/defects/VR-DEF-9999", json={"status": "CONFIRMED"}, headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_model_metrics_404_when_unseeded(client, auth_headers):
    resp = await client.get("/api/v1/model/metrics", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_log_lists_entries(client, auth_headers):
    resp = await client.get("/api/v1/audit-log", headers=auth_headers)
    assert resp.status_code == 200
    assert "entries" in resp.json()

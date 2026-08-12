import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "engineer@visireport.ai", "password": "test-password"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["role"] == "engineer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "engineer@visireport.ai", "password": "wrong"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token_returns_401(client):
    resp = await client.get("/api/v1/model/metrics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_bad_token_returns_401(client):
    resp = await client.get("/api/v1/model/metrics", headers={"Authorization": "Bearer garbage.token.value"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_does_not_require_auth(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "degraded")

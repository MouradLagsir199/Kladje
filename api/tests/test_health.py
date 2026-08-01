import httpx

from receptenapp.main import app


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(path)


async def test_healthz() -> None:
    response = await _get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_checks_db_and_clerk_jwks() -> None:
    response = await _get("/readyz")
    body = response.json()
    assert response.status_code in (200, 503)
    assert body["checks"]["db"] == "ok"
    assert body["checks"]["clerk_jwks"] in ("ok", "unreachable")

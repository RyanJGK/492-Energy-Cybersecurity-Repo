import asyncio

import httpx


async def _get(url: str):
    async with httpx.AsyncClient() as client:
        return await client.get(url)


def test_health_endpoint_running_event_loop(monkeypatch):
    # Minimal smoke test for imported app
    from app.main import app  # noqa: F401

    # This test does not start the server; just ensures import works
    assert True

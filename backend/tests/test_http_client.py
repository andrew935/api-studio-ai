import pytest

from backend.app.services import http_client


async def fake_fetch_demo_users():
    return {
        "status_code": 200,
        "data": [{"id": 1}, {"id": 2}],
    }


@pytest.mark.anyio
async def test_fetch_demo_user_count_returns_count(monkeypatch):
    monkeypatch.setattr(
        http_client,
        "fetch_demo_users",
        fake_fetch_demo_users,
    )
    result = await http_client.fetch_demo_user_count()
    assert result == {"count": 2}

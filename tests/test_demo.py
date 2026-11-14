import asyncio

import httpx

from missions import demo

BASE = "http://127.0.0.1:8860"


def call(method, path, **kw):
    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=demo.make_app()), base_url=BASE) as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def test_demo_serves_the_fixture():
    r = call("GET", "/api/missions")
    assert [m["id"] for m in r.json()] == [2, 1]
    d = call("GET", "/api/missions/1").json()
    assert d["title"] == "Demo straddle" and d["board"]["best"] == "v04"
    assert d["right"]["luck"] == "needs 3.5 after 4 tries; has 3.1"
    assert len(call("GET", "/api/missions/1/events").json()) == 8


def test_demo_page_and_writes_touch_nothing(tmp_path):
    assert "Missions" in call("GET", "/").text
    r = call("POST", "/api/missions/1/chat", json={"text": "hi"})
    assert r.status_code == 200
    assert call("POST", "/api/missions/1/chat", json={"text": "pass 41 % now"}).json().get("warn")
    assert call("GET", "/api/missions/1/events").json().__len__() == 8
    assert call("GET", "/api/missions/1/brief").json()["account"]["bans"]
    assert call("GET", "/api/missions/9").status_code == 404

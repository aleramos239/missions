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


def test_demo_only_when_exactly_one(monkeypatch):
    from missions import api
    for v, on in (("1", True), ("0", False), ("false", False), ("", False), (None, False)):
        if v is None:
            monkeypatch.delenv("MISSIONS_DEMO", raising=False)
        else:
            monkeypatch.setenv("MISSIONS_DEMO", v)
        assert (api.build().app.__class__.__name__ == "FastAPI") is True
        routes = {r.path for r in api.build().app.routes}
        assert ("/api/connections" in routes and "/api/missions/{mid}/progress" not in routes) is on, v


def test_demo_result_pages_have_data():
    t = call("GET", "/api/missions/1/tested").json()
    assert {v["state"] for v in t} >= {"frozen", "dropped", "running", "done"}
    tab = call("GET", "/api/missions/1/table?name=demo_v04").json()
    assert tab["cells"] == 40 and tab["pick"] and any(r["net"] < 0 for r in tab["rows"])
    assert call("GET", "/api/missions/1/table?name=demo_v03").json()["cells"] == 20
    b = call("GET", f"/api/missions/1/box?name=demo_v04&box={tab['pick']}").json()
    assert b["row"]["box"] == tab["pick"] and b["mc"]["worst_drawdown"]
    od = call("GET", f"/api/missions/1/odds?name=demo_v04&box={tab['pick']}").json()
    assert len(od["odds"]) >= 4 and od["skipped"][0]["why"]
    assert b["mc"]["below_zero_pct"] is None and "under 5 %" in b["mc"]["below_zero_said"]
    lk = call("GET", "/api/missions/1/luck?name=demo_v05").json()
    assert lk["heard"]["line"] == "under the bar" and lk["yours"]["net"] < 0 and len(lk["gate"]["charges"]) == 5
    assert call("GET", "/api/missions/1/running").json()["slots"]["cap"] == 12
    assert call("GET", "/api/missions/1/refused").json()
    assert call("GET", "/api/missions/1/table?name=../x").status_code == 404

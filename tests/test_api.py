import asyncio
import json
from types import SimpleNamespace

import httpx

from missions import api, briefing, config, store, system
from tests.fakes.hb import FakeHB

TEAM = {r: {"model": "haiku", "effort": "low"} for r in store.ROLES}
BASE = "http://127.0.0.1:8860"


def call(method, path, fake=None, run_turn=None, headers=None, **kw):
    fake = fake or FakeHB()

    async def go():
        app = api.make_app(hb=fake, run_turn=run_turn)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as c:
            return await c.request(method, path, headers=headers, **kw)
    return asyncio.run(go())


def mk(status="running", reads=0, **over):
    m = store.new_mission("beat three points", TEAM, {"tries": {"n": 9}}, "team")
    m.update(status=status, reads=reads, brief={"goal": {"kind": "points", "target": 3.0}}, **over)
    store.save(m)
    return m["id"]


def test_unknown_mission_is_404():
    assert call("GET", "/api/missions/99").status_code == 404
    assert call("POST", "/api/missions/99/pause").status_code == 404


def test_sidebar_and_detail():
    mid = mk()
    r = call("GET", "/api/missions").json()
    assert r[0]["id"] == mid and {"title", "status", "round", "badge"} <= set(r[0])
    d = call("GET", f"/api/missions/{mid}").json()
    assert d["id"] == mid and "board" in d and d["right"]["goal"]["target"] == 3.0
    assert "tries" in d["right"] and "luck" in d["right"]


def test_the_guard():
    mid = mk()
    assert call("GET", "/api/missions", headers={"host": "evil.example"}).status_code == 403
    assert call("POST", f"/api/missions/{mid}/pause", headers={"origin": "https://evil.example"}).status_code == 403
    assert call("POST", f"/api/missions/{mid}/pause", headers={"origin": "http://localhost:8860"}).status_code == 200
    assert call("POST", f"/api/missions/{mid}/resume").status_code == 200  # no Origin, local Host
    # a foreign Origin on a GET is not a write
    assert call("GET", "/api/missions", headers={"origin": "https://evil.example"}).status_code == 200


def test_page_is_no_cache():
    r = call("GET", "/")
    assert r.headers["cache-control"] == "no-cache"


def test_create_mission_starts_the_brief():
    async def lead(mid, role, prompt, **kw):
        return SimpleNamespace(ok=True, text='x\n```json\n{"ask":{"q":"What?","options":["a","b"]}}\n```',
                               session_id="s", why=None, rate=None, cost_usd=0)
    fake = FakeHB()

    async def go():
        app = api.make_app(hb=fake, run_turn=lead)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as c:
            r = await c.post("/api/missions", json={"sentence": "go", "team": TEAM, "limits": {}, "test_months": "team"})
            await asyncio.sleep(0.2)
            return r, (await c.get(f"/api/missions/{r.json()['id']}/events")).json()
    r, ev = asyncio.run(go())
    assert r.status_code == 200 and r.json()["status"] == "briefing"
    assert any(e["who"] == "lead" for e in ev)
    bad = call("POST", "/api/missions", json={"sentence": "go", "team": {}, "limits": {}, "test_months": "team"})
    assert bad.status_code == 400


def test_events_after():
    mid = mk()
    store.event(mid, "chat", "owner", "a")
    store.event(mid, "chat", "owner", "b")
    assert [e["text"] for e in call("GET", f"/api/missions/{mid}/events?after=1").json()] == ["b"]


def test_stream_yields_an_event_appended_after_it_opened():
    mid = mk()

    async def go():
        g = api.event_stream(mid, 0, poll=0.01, beat=0.05)
        first = await g.__anext__()
        assert first.startswith(":")  # nothing yet: a comment line
        store.event(mid, "chat", "owner", "late")
        for _ in range(20):
            line = await g.__anext__()
            if "data:" in line:
                return line.split("data:")[1]
    line = asyncio.run(go())
    assert json.loads(line)["text"] == "late"


def test_chat_warning_only_after_a_read_and_only_for_numbers():
    pre, post = mk(reads=0), mk(reads=1)
    num = {"to": "builder", "text": "it made $500 and 62% wins"}
    assert "warn" not in call("POST", f"/api/missions/{pre}/chat", json=num).json()
    r = call("POST", f"/api/missions/{post}/chat", json={"to": "builder", "text": "try a wider stop"}).json()
    assert "warn" not in r
    n = len(store.events(post))
    r = call("POST", f"/api/missions/{post}/chat", json=num).json()
    assert r["warn"].startswith("This looks like a test-month number") and len(store.events(post)) == n
    assert call("POST", f"/api/missions/{post}/chat", json={**num, "sure": True}).status_code == 200
    assert len(store.events(post)) == n + 1
    assert "warn" in call("POST", f"/api/missions/{post}/chat", json={"to": "all", "text": "30 trades"}).json()


def test_pause_stop_and_read_approve():
    mid = mk()
    call("POST", f"/api/missions/{mid}/pause")
    assert store.load(mid)["status"] == "paused"
    call("POST", f"/api/missions/{mid}/resume")
    assert store.load(mid)["status"] == "running"
    call("POST", f"/api/missions/{mid}/stop")
    assert store.load(mid)["status"] == "stopped"
    m = mk(status="waiting_owner", pending={"read_for": "m1_v01"})
    r = call("POST", f"/api/missions/{m}/read/approve", json={"said": "yes read it"})
    assert r.status_code == 200 and store.load(m)["pending"]["read_ok"] == "yes read it"
    assert call("POST", f"/api/missions/{m}/read/approve", json={"said": "again"}).status_code == 400


def test_patch_rewrites_the_homebase_brief():
    mid = mk()
    fake = FakeHB()
    fake.briefs[mid] = {"approved": True, "test_months": "team"}
    r = call("PATCH", f"/api/missions/{mid}", fake=fake, json={"test_months": "ask", "limits": {"hours": {"n": 1}}})
    assert r.status_code == 200
    assert fake.briefs[mid]["test_months"] == "ask"
    got = store.load(mid)
    assert got["test_months"] == "ask" and got["limits"] == {"hours": {"n": 1}}
    assert call("PATCH", f"/api/missions/{mid}", json={"test_months": "never"}).status_code == 400


def seeded():
    mid = mk(versions=[{"name": f"m1_v01", "version": "v01", "round": 1, "state": "frozen", "box": 7, "box_label": "1.5 · #7",
                        "gate": {"lines": [{"line": "luck", "ok": True, "said": "t 3.1 in-sample (need 3.5+ after 7 tries), net 12,345"}], "charges": [], "goal": {"value": 3.1}}, "heard": {"held": False, "line": "x", "close": True}}],
             round=1, pending={"tries": {"mission": 7, "family_on_file": 0, "total": 7, "needed_t": 3.5}})
    return mid


def test_tested_table_box_odds_refused():
    mid = seeded()
    fake = FakeHB()
    fake.tables["m1_v01"] = {"rows": [{"box": 7, "cell": 7}], "pick": 7}
    fake.mcs[("m1_v01", "7")] = {"p": 1}
    fake.owner_files[("refused", mid)] = [{"why": "no"}]
    t = call("GET", f"/api/missions/{mid}/tested", fake=fake).json()
    assert t[0]["name"] == "m1_v01" and t[0]["frozen"] is True and t[0]["goal_value"] == 3.1
    assert call("GET", f"/api/missions/{mid}/table?name=m1_v01", fake=fake).json()["pick"] == 7
    b = call("GET", f"/api/missions/{mid}/box?name=m1_v01&box=7", fake=fake).json()
    assert b["row"]["cell"] == 7 and b["mc"] == {"p": 1}
    assert call("GET", f"/api/missions/{mid}/refused", fake=fake).json() == [{"why": "no"}]


def test_odds_is_working_then_done():
    mid = seeded()
    fake = FakeHB()
    import threading
    go_on = threading.Event()
    fake.odds_[("m1_v01", "7")] = {"pass": 0.4}
    real = fake.odds
    fake.odds = lambda *a: (go_on.wait(5), real(*a))[1]
    api._odds.clear()

    async def go():
        app = api.make_app(hb=fake)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as c:
            q = f"/api/missions/{mid}/odds?name=m1_v01&box=7"
            out = [(await c.get(q)).json(), (await c.get(q)).json()]
            go_on.set()
            for _ in range(50):
                await asyncio.sleep(0.02)
                out.append((await c.get(q)).json())
                if "working" not in out[-1]:
                    break
            return out
    out = asyncio.run(go())
    assert out[:2] == [{"working": True}] * 2 and out[-1] == {"pass": 0.4}
    assert sum(1 for c in fake.calls if c[0] == "odds") == 1


def test_luck_heard_and_yours():
    mid = seeded()
    fake = FakeHB()
    fake.owner_files[("read", mid, "m1_v01")] = {"net": 123}
    d = call("GET", f"/api/missions/{mid}/luck?name=m1_v01", fake=fake).json()
    assert d["heard"] == {"held": False, "line": "x", "close": True} and d["yours"] == {"net": 123}
    assert d["tries"]["needed_t"] == 3.5 and "gate" in d


def test_running_and_progress():
    mid = seeded()
    d = call("GET", f"/api/missions/{mid}/running").json()
    assert {"workers", "jobs", "slots", "usage", "cost_usd", "run_seconds"} <= set(d)
    p = call("GET", f"/api/missions/{mid}/progress").json()
    assert p[0]["round"] == 1 and p[0]["best"] == 3.1 and p[0]["target"] == 3.0
    assert p[0]["best_t"] == 3.1 and p[0]["needed_t"] == 3.5


def test_homebase_down_is_503():
    mid = seeded()
    fake = FakeHB()
    fake.tables["m1_v01"] = FakeHB.Down("gone")
    r = call("GET", f"/api/missions/{mid}/table?name=m1_v01", fake=fake)
    assert r.status_code == 503 and "gone" in r.json()["error"]


def test_connections_and_hunt(monkeypatch):
    got = []
    monkeypatch.setattr(system, "pause_hunt", lambda on: got.append(on))
    d = call("GET", "/api/connections").json()
    assert d["health"]["door"] is True and "settings" in d
    call("POST", "/api/connections", json={"ntfy_topic": "abc", "bogus": 1})
    assert config.settings() == {"ntfy_topic": "abc"}
    assert call("POST", "/api/hunt", json={"pause": True}).status_code == 200 and got == [True]


def test_luck_bar_in_plain_words():
    mid = seeded()
    assert call("GET", f"/api/missions/{mid}").json()["right"]["luck"] == "needs 3.5 after 7 tries; has 3.1"
    assert api._t({"lines": [{"line": "luck", "ok": False, "said": "t None in-sample (need 3.5+)"}]}) is None


def test_bad_names_are_404_and_the_adapter_refuses_them():
    import pytest
    from missions import hb
    mid = seeded()
    for n in ("../x", "--flag", "m9_v09"):
        for path in ("table?name=", "box?box=7&name=", "odds?box=7&name="):
            assert call("GET", f"/api/missions/{mid}/{path}{n}").status_code == 404
    for f in (lambda n: hb.table(1, n), lambda n: hb.mc(1, n, "7"), lambda n: hb.odds(1, n, "7")):
        for n in ("../x", "--flag"):
            with pytest.raises(hb.Refused):
                f(n)


def test_a_down_homebase_in_the_background_brief_leaves_the_mission_retryable():
    fake = FakeHB()
    fake.accounts = lambda: (_ for _ in ()).throw(FakeHB.Down("gone"))

    async def go():
        app = api.make_app(hb=fake)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as c:
            r = await c.post("/api/missions", json={"sentence": "go", "team": TEAM, "limits": {}, "test_months": "team"})
            await asyncio.sleep(0.2)
            return r.json()["id"]
    mid = asyncio.run(go())
    assert store.load(mid)["status"] == "briefing"
    assert any("gone" in e["text"] and not e["for_workers"] for e in store.events(mid))


def test_a_disconnected_request_ends_the_stream():
    mid = mk()

    async def go():
        n = []

        async def gone():
            n.append(1)
            return len(n) > 2
        return [x async for x in api.event_stream(mid, 0, poll=0.01, gone=gone)]
    assert asyncio.run(go()) == [": open\n\n"]


def test_a_stray_query_param_is_ignored_by_the_switches():
    mid = mk()
    assert call("POST", f"/api/missions/{mid}/pause?fn=x").status_code == 200
    assert store.load(mid)["status"] == "paused"


def test_minors():
    mid = mk(reads=1)
    assert call("GET", "/api/missions", headers={"host": "LocalHost:8860"}).status_code == 200
    for t in ("1 trade", "3 pt", "2 point"):
        assert "warn" in call("POST", f"/api/missions/{mid}/chat", json={"to": "all", "text": t}).json()
    for body in ({"limits": {"bogus": 1}}, {"team": {"lead": {"model": "haiku", "effort": "low"}}},
                 {"team": {**TEAM, "boss": TEAM["lead"]}}):
        assert call("PATCH", f"/api/missions/{mid}", json=body).status_code == 400
    assert call("POST", f"/api/missions/{mid}/chat", json={"to": "nobody", "text": "hi"}).status_code == 400


def test_page_and_brief_route():
    r = call("GET", "/")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache" and "<title>Missions" in r.text
    assert call("GET", "/static/missions.css").status_code == 200
    mid = mk(status="briefing")
    fake = FakeHB()
    fake.accounts_ = [{"id": "acct1", "bans": ["no bots"]}]
    m = store.load(mid)
    m["brief"] = {"goal": {"kind": "eval", "target": 0.5, "rule": "acct1"}, "idea": "x"}
    store.save(m)
    b = call("GET", f"/api/missions/{mid}/brief", fake=fake).json()
    assert b["bans"] == ["no bots"] and b["account"]["id"] == "acct1"

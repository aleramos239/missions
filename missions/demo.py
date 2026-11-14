"""MISSIONS_DEMO=1: the page's routes from tests/fixtures/demo (fake numbers). Reads only; every write answers a canned
reply. No Homebase, no claude, no engine, no home folder."""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import api

FIX = Path(__file__).parent.parent / "tests/fixtures/demo"
ACCOUNT = {"id": "apex_50k_legacy", "name": "Apex 50K Legacy eval",
           "bans": ["No bots or automated trading", "No trading through news in the first minute"]}


def _read(mid, name, default=None):
    try:
        return json.loads((FIX / str(mid) / name).read_text())
    except OSError:
        if default is None:
            raise api.NotFound(f"no mission {mid}") from None
        return default


def _events(mid, after=0):
    _read(mid, "mission.json")
    p = FIX / str(mid) / "events.jsonl"
    return [e for e in map(json.loads, p.read_text().splitlines()) if e["n"] > after]


def make_app():
    app = FastAPI()
    app.exception_handler(api.NotFound)(lambda _, e: api._bad(str(e), 404))

    @app.get("/")
    async def index():
        return HTMLResponse((api.STATIC / "index.html").read_text())

    app.mount("/static", StaticFiles(directory=api.STATIC), name="static")

    @app.get("/api/missions")
    async def sidebar():
        ms = sorted((_read(p.name, "mission.json") for p in FIX.iterdir() if p.name.isdigit()), key=lambda m: -m["id"])
        return [{"id": m["id"], "title": m["title"], "status": m["status"], "round": m["round"], "badge": api._badge(m)} for m in ms]

    @app.get("/api/missions/{mid}")
    async def detail(mid: int):
        m, board = _read(mid, "mission.json"), _read(mid, "board.json")
        return {**m, "board": board, "right": api._right(m, board)}

    @app.get("/api/missions/{mid}/events")
    async def past(mid: int, after: int = 0):
        return _events(mid, after)

    @app.get("/api/missions/{mid}/stream")
    async def stream(mid: int, after: int = 0):
        _read(mid, "mission.json")
        async def quiet():  # open, then only a comment every 15 s: the demo has no new events
            yield ": open\n\n"
            while True:
                await asyncio.sleep(15)
                yield ": keep\n\n"
        return StreamingResponse(quiet(), media_type="text/event-stream", headers={"cache-control": "no-cache"})

    @app.get("/api/missions/{mid}/brief")
    async def brief(mid: int):
        b = _read(mid, "mission.json")["brief"]
        return {**b, "account": ACCOUNT, "bans": ACCOUNT["bans"]} if b else {"brief": None}

    def version(mid, name):  # only the mission's own version names reach a fixture file
        m = _read(mid, "mission.json")
        v = next((x for x in m["versions"] if name in (x["name"], x["version"])), None)
        if v is None:
            raise api.NotFound(f"no version {name}")
        return m, v

    @app.get("/api/missions/{mid}/running")
    async def running(mid: int):
        return _read(mid, "running.json", {"workers": [], "jobs": [], "slots": {"cap": 12, "running": 0}, "usage": {"five_hour": None, "seven_day": None, "at": None}, "cost_usd": 0.0, "run_seconds": 0})

    @app.get("/api/missions/{mid}/refused")
    async def refused(mid: int):
        return _read(mid, "refused.json", [])

    @app.get("/api/missions/{mid}/tested")
    async def tested(mid: int):
        m, board = _read(mid, "mission.json"), {v["version"]: v for v in _read(mid, "board.json")["versions"]}
        return [{"name": v["name"], "version": v["version"], "state": v["state"], "frozen": v["state"] == "frozen",
                 "box": board[v["version"]]["box"], "goal_value": board[v["version"]]["goal_value"], "why": v.get("why")} for v in m["versions"]]

    @app.get("/api/missions/{mid}/table")
    async def table(mid: int, name: str):
        version(mid, name)
        return _read(mid, f"tables/{name}.json")

    @app.get("/api/missions/{mid}/box")
    async def box(mid: int, name: str, box: str):
        version(mid, name)
        t = _read(mid, f"tables/{name}.json")
        return {"row": next((r for r in t["rows"] if str(r["box"]) == box), None), "mc": _read(mid, "mc.json")}

    @app.get("/api/missions/{mid}/odds")
    async def odds(mid: int, name: str, box: str):
        version(mid, name)
        return _read(mid, "odds.json")

    @app.get("/api/missions/{mid}/luck")
    async def luck(mid: int, name: str):
        m, v = version(mid, name)
        return {"gate": v.get("gate"), "tries": m["pending"].get("tries"), "heard": v.get("heard"), "yours": _read(mid, f"yours/{v['name']}.json", {}) or None}

    @app.get("/api/connections")
    async def connections():
        return {"health": {"chart_service": True, "door": True, "claude": "2.1.321"},
                "settings": {"claude": "/Applications/Claude.app/claude", "ntfy_topic": "missions-demo"}, "hunt_paused": False}

    @app.post("/api/connections")
    async def set_connections(body: dict = Body(...)):
        return {k: body[k] for k in ("claude", "ntfy_topic") if k in body}

    @app.post("/api/hunt")
    async def hunt(body: dict = Body(...)):
        return {"hunt_paused": bool(body["pause"])}

    # ---- writes: canned
    @app.post("/api/missions")
    async def create(body: dict = Body(...)):
        return _read(2, "mission.json")

    @app.post("/api/missions/{mid}/brief/answer")
    async def answer(mid: int, body: dict = Body(...)):
        return {"ask": {"q": "Demo: no Lead is running. Fewest trades a week?", "options": ["2", "3"]}}

    @app.post("/api/missions/{mid}/brief/approve")
    async def approve(mid: int, body: dict = Body(...)):
        return _read(mid, "mission.json")

    @app.post("/api/missions/{mid}/chat")
    async def chat(mid: int, body: dict = Body(...)):
        if api.NUMBERISH.search(body.get("text", "")) and body.get("sure") is not True:
            return {"warn": api.WARN}
        return {"n": 99, "at": datetime.now(timezone.utc).isoformat(), "type": "chat", "who": "owner", "to": None, "text": body.get("text"), "data": None}

    @app.post("/api/missions/{mid}/dead")
    async def dead(mid: int, body: dict = Body(...)):
        return {"dead": body.get("family")}

    for name in ("pause", "resume", "stop"):
        app.add_api_route(f"/api/missions/{{mid}}/{name}", lambda mid: {"status": "paused"}, methods=["POST"])
    return api.Guard(app)

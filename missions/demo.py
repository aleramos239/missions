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

    @app.get("/api/connections")
    async def connections():
        return {"health": {"chart_service": True, "door": True, "claude": "demo"}, "settings": {}, "hunt_paused": None}

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

    for name in ("pause", "resume", "stop"):
        app.add_api_route(f"/api/missions/{{mid}}/{name}", lambda mid: {"status": "paused"}, methods=["POST"])
    return api.Guard(app)

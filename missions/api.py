"""The HTTP API: the owner's pages. Local only (host/origin guard). It serves the OWNER, so /luck and /refused may show
test-month numbers; nothing written into a mission's chat/events here may carry one (the chat warning)."""
import asyncio
import json
import os
import re
import threading
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import briefing, config, engine, hb as _hb, store, system, worker, wrapup

STATIC = Path(__file__).parent / "static"
HOSTS = ("127.0.0.1", "localhost")
ORIGINS = ("http://127.0.0.1:8860", "http://localhost:8860")
WARN = "This looks like a test-month number. The team must never see one. Send anyway?"
NUMBERISH = re.compile(r"\d\s*(?:%|\$|pts?\b|points?\b|trades?\b)|\$\s*\d", re.I)
_odds = {}  # (mid, name, box) -> {"done", "result"/"err"}: one computation at a time
_odds_lock = threading.Lock()


class NotFound(Exception):
    pass


class Bad(Exception):
    pass


@contextmanager
def bad():
    """The owner's request was wrong: a plain 400."""
    try:
        yield
    except (ValueError, KeyError) as e:
        raise Bad(f"missing {e}" if isinstance(e, KeyError) else str(e)) from None


class Guard:
    """Pure ASGI (no BaseHTTPMiddleware, so a streaming response is cancelled cleanly): local Host only, local Origin on
    writes, no-cache on the page."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        h = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        host = h.get("host", "")
        name = host[1:host.index("]")] if host.startswith("[") and "]" in host else host.rsplit(":", 1)[0] if ":" in host else host
        o = h.get("origin")
        if name.lower() not in HOSTS:
            return await _bad("this app answers only on 127.0.0.1", 403)(scope, receive, send)
        if scope["method"] != "GET" and o is not None and o not in ORIGINS:
            return await _bad("foreign origin", 403)(scope, receive, send)
        page = not scope["path"].startswith("/api")

        async def snd(msg):
            if page and msg["type"] == "http.response.start":
                msg["headers"] = [*msg["headers"], (b"cache-control", b"no-cache")]
            await send(msg)
        await self.app(scope, receive, snd)


def _bad(msg, code=400):
    return JSONResponse({"error": msg}, status_code=code)


def _mission(mid):
    try:
        return store.load(mid)
    except (OSError, ValueError):
        raise NotFound(f"no mission {mid}") from None


def _version(m, name):
    """The mission's own version name, else 404: nothing else reaches the door."""
    v = next((x for x in m["versions"] if x["name"] == name), None)
    if v is None:
        raise NotFound(f"no version {name}")
    return v


def _badge(m):
    return {"waiting_owner": "needs you", "briefing": "brief", "waiting_plan": "waiting for the plan", "crashed": "error",
            "waiting_homebase": "Homebase down"}.get(m["status"])


T_SAID = re.compile(r"^\s*t\s+(-?\d+(?:\.\d+)?)")


def _t(gate):
    """The t in the luck line's words ("t 3.1 in-sample (need ..."); None when it says none."""
    for x in (gate or {}).get("lines", []):
        if x.get("line") == "luck":
            m = T_SAID.match(str(x.get("said") or ""))
            return float(m[1]) if m else None
    return None


def _right(m, board):
    best = next((v for v in board["versions"] if v["version"] == board["best"]), None)
    full = next((v for v in m["versions"] if best and v["version"] == best["version"]), None)
    tr = board["tries"]
    t = _t((full or {}).get("gate"))
    if best is None:
        luck = "no version has scored yet"
    else:
        luck = f"needs {tr.get('needed_t')} after {tr.get('mission')} tries; has {t}"
    return {"goal": board["goal"], "best": best, "luck": luck, "tries": tr, "test_months": m["test_months"],
            "reads": m["reads"], "doing": {"status": m["status"], "step": m["step"]}}


async def event_stream(mid, after=0, *, poll=0.5, beat=15, gone=None):
    """SSE lines: one `data:` per new event; a comment line every `beat` seconds of quiet (and first, to open the stream)."""
    yield ": open\n\n"
    quiet = 0.0
    while not (gone and await gone()):
        rows = await asyncio.to_thread(store.events, mid, after)
        for e in rows:
            after = e["n"]
            yield f"id: {e['n']}\ndata: {json.dumps(e)}\n\n"
        quiet = 0.0 if rows else quiet + poll
        if quiet >= beat:
            quiet = 0.0
            yield ": keep\n\n"
        await asyncio.sleep(poll)


def make_app(*, hb=_hb, run_turn=None, runner=False):
    run_turn = run_turn or worker.run_turn
    tasks = set()

    @asynccontextmanager
    async def life(app):
        t = asyncio.create_task(engine.runner()) if runner else None
        yield
        if t:
            t.cancel()
        worker.kill_all()  # no claude or MCP process outlives the app

    app = FastAPI(lifespan=life)

    @app.exception_handler(NotFound)
    async def _nf(_, e):
        return _bad(str(e), 404)

    @app.exception_handler(_hb.Down)
    async def _down(_, e):
        return _bad(f"Homebase is not answering: {e}", 503)

    @app.exception_handler(_hb.Refused)
    async def _ref(_, e):
        return _bad(str(e), 409)

    @app.exception_handler(Bad)
    async def _val(_, e):
        return _bad(str(e), 400)

    # ---- pages
    @app.get("/")
    async def index():
        p = STATIC / "index.html"
        return HTMLResponse(p.read_text() if p.exists() else "<title>Missions</title>")  # Guard adds no-cache

    if STATIC.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")

    # ---- missions
    @app.get("/api/missions")
    async def sidebar():
        return [{"id": m["id"], "title": m["title"], "status": m["status"], "round": m["round"], "badge": _badge(m),
                 "stage": [m.get("stage", 1), ((m["limits"] or {}).get("stages") or {}).get("n", 1)],
                 "usage_used": m.get("usage_used"), "cost_usd": m.get("cost_usd"), "run_seconds": m.get("run_seconds")}
                for m in store.missions()]

    async def brief_turn(mid, answer=None, background=False):
        try:
            out = await briefing.next_step(mid, answer, run_turn=run_turn, hb=hb)
        except Exception as e:  # the mission stays in "briefing": the next /brief/answer tries again
            if not background:
                raise
            store.event(mid, "chat", "engine", f"The brief stopped ({e}). Answer again to retry.", for_workers=False)
            return {"error": str(e)}
        if "error" in out:
            store.event(mid, "chat", "engine", f"The brief stopped: {out['error']}", for_workers=False)
        return out

    @app.post("/api/missions")
    async def create(body: dict = Body(...)):
        with bad():
            m = store.new_mission(body["sentence"], body["team"], body.get("limits") or {}, body["test_months"])
        t = asyncio.create_task(brief_turn(m["id"], background=True))
        tasks.add(t)
        t.add_done_callback(tasks.discard)
        return m

    @app.get("/api/missions/{mid}")
    async def detail(mid: int):
        m = _mission(mid)
        board = engine.Engine(mid, hb=hb).board()
        return {**m, "board": board, "right": _right(m, board)}

    @app.get("/api/missions/{mid}/events")
    async def past(mid: int, after: int = 0):
        _mission(mid)
        return store.events(mid, after)

    @app.get("/api/missions/{mid}/stream")
    async def stream(request: Request, mid: int, after: int = 0):
        _mission(mid)
        return StreamingResponse(event_stream(mid, after, gone=request.is_disconnected), media_type="text/event-stream",
                                 headers={"cache-control": "no-cache"})

    # ---- the brief and the chat
    @app.get("/api/missions/{mid}/brief")
    async def brief_page(mid: int):
        b = _mission(mid)["brief"]
        return briefing.page(b, await asyncio.to_thread(hb.accounts)) if b else {"brief": None}

    @app.post("/api/missions/{mid}/brief/answer")
    async def brief_answer(mid: int, body: dict = Body(...)):
        _mission(mid)
        with bad():
            text = body["text"]
        out = await brief_turn(mid, text)
        return _bad(out["error"], 409) if "error" in out else out

    @app.post("/api/missions/{mid}/brief/approve")
    async def brief_approve(mid: int, body: dict = Body(...)):
        _mission(mid)
        with bad():
            return await briefing.approve(mid, body.get("said"), hb=hb)

    @app.post("/api/missions/{mid}/chat")
    async def chat(mid: int, body: dict = Body(...)):
        m = _mission(mid)
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise Bad("the text is empty")
        if m["reads"] >= 1 and NUMBERISH.search(text) and body.get("sure") is not True:
            return {"warn": WARN}
        with bad():
            return engine.owner_says(mid, body.get("to", "all"), text.strip())

    # ---- the engine's switches
    def switch(fn):
        def sw(mid: int):
            _mission(mid)
            fn(mid)
            return {"status": store.load(mid)["status"]}
        return sw
    for name, fn in (("pause", engine.pause), ("resume", engine.resume), ("stop", engine.stop)):
        app.add_api_route(f"/api/missions/{{mid}}/{name}", switch(fn), methods=["POST"])

    @app.post("/api/missions/{mid}/read/approve")
    async def read_approve(mid: int, body: dict = Body(...)):
        _mission(mid)
        with bad():
            engine.approve_read(mid, body.get("said"))
        return {"status": store.load(mid)["status"]}

    @app.post("/api/missions/{mid}/dead")
    async def dead(mid: int, body: dict = Body(...)):
        m = _mission(mid)
        with bad():
            fam = body["family"]
            if not isinstance(fam, str) or not isinstance(body.get("said"), str):
                raise ValueError("family and said are words")
            if m["status"] not in store.DONE or not any(v.get("family") == fam for v in m["versions"]):
                raise ValueError("the mission is not over, or never used that family")
            wrapup.mark_dead(fam, f"mission {mid}", body.get("said"))
        return {"dead": fam}

    @app.delete("/api/missions/{mid}")
    async def delete(mid: int):
        m = _mission(mid)
        if m["status"] in ("briefing", "queued", "running", "waiting_plan", "waiting_homebase", "waiting_owner") \
                or mid in engine._active:
            raise Bad("Stop it first")
        store.delete(mid)
        return {"deleted": mid}

    @app.patch("/api/missions/{mid}")
    async def patch(mid: int, body: dict = Body(...)):
        m = _mission(mid)
        if "test_months" in body and body["test_months"] not in ("team", "ask"):
            raise Bad("test_months is team or ask")
        if "limits" in body:
            with bad():
                store.check_limits(body["limits"])
        if "team" in body:
            with bad():
                store.check_team(body["team"])
        for k in engine.OWNER_KEYS:
            if k in body:
                m[k] = body[k]
        store.save(m)
        if "test_months" in body:
            await asyncio.to_thread(hb.set_test_months, mid, body["test_months"])
        return m

    @app.get("/api/team-defaults")
    async def get_team_defaults():
        return store.team_defaults()

    @app.put("/api/team-defaults")
    async def put_team_defaults(body: dict = Body(...)):
        with bad():
            store.check_team(body)
        s = config.settings()
        s["team_defaults"] = {r: {"model": body[r]["model"], "effort": body[r]["effort"]} for r in store.ROLES}
        config.save_settings(s)
        return s["team_defaults"]

    # ---- the owner's pages
    @app.get("/api/missions/{mid}/tested")
    async def tested(mid: int):
        m = _mission(mid)
        board = {v["version"]: v for v in engine.Engine(mid, hb=hb).board()["versions"]}
        return [{"name": v["name"], "version": v["version"], "state": v["state"], "frozen": v["state"] == "frozen",
                 "box": board[v["version"]]["box"], "goal_value": board[v["version"]]["goal_value"], "why": v.get("why")}
                for v in m["versions"]]

    @app.get("/api/missions/{mid}/table")
    async def table(mid: int, name: str):
        _version(_mission(mid), name)
        return await asyncio.to_thread(hb.table, mid, name)

    @app.get("/api/missions/{mid}/box")
    async def box(mid: int, name: str, box: str):
        _version(_mission(mid), name)
        t = await asyncio.to_thread(hb.table, mid, name)
        row = next((r for r in t.get("rows", []) if str(r.get("box")) == box), None)
        return {"row": row, "mc": await asyncio.to_thread(hb.mc, mid, name, box)}

    @app.get("/api/missions/{mid}/odds")
    async def odds(mid: int, name: str, box: str):
        _version(_mission(mid), name)
        key = (mid, name, box)
        with _odds_lock:
            s = _odds.get(key)
            if s is None:
                s = _odds[key] = {"done": False}

                def work():
                    try:
                        s["result"] = hb.odds(mid, name, box)
                    except Exception as e:  # shown to the owner, then forgotten so he can ask again
                        s["err"] = e
                    s["done"] = True
                threading.Thread(target=work, daemon=True).start()
        if not s["done"]:
            return {"working": True}
        if "err" in s:
            with _odds_lock:
                _odds.pop(key, None)
            raise s["err"]
        return s["result"]

    @app.get("/api/missions/{mid}/luck")
    async def luck(mid: int, name: str):
        m = _mission(mid)
        v = next((x for x in m["versions"] if name in (x["name"], x["version"])), None)
        if v is None:
            raise NotFound(f"no version {name}")
        return {"gate": v.get("gate"), "tries": m["pending"].get("tries"), "heard": v.get("heard"),
                "yours": await asyncio.to_thread(hb.owner_read, mid, v["name"])}

    @app.get("/api/missions/{mid}/running")
    async def running(mid: int):
        m = _mission(mid)
        last = next((e["at"] for e in reversed(store.events(mid)) if e["type"] == "step"), None)
        live = m["status"] in ("running", "waiting_homebase")
        workers = [{"role": r, "state": (m["step"] or "idle") if live else "idle", "since": last} for r in store.ROLES]
        jobs = []
        for v in m["versions"]:
            if v["state"] == "running" and v.get("job_id"):
                jobs.append({"name": v["name"], "progress": v.get("progress")})
        return {"workers": workers, "jobs": jobs, "slots": await asyncio.to_thread(hb.slots), "usage": system.usage(),
                "cost_usd": m["cost_usd"], "run_seconds": m["run_seconds"]}

    @app.get("/api/missions/{mid}/progress")
    async def progress(mid: int):
        m = _mission(mid)
        board = engine.Engine(mid, hb=hb).board()
        by = {v["version"]: v for v in m["versions"]}
        out = []
        for r in range(1, m["round"] + 1):
            vs = [v for v in board["versions"] if by[v["version"]]["round"] == r and v["goal_value"] is not None]
            top = max(vs, key=lambda v: v["goal_value"], default=None)
            out.append({"round": r, "best": top and top["goal_value"], "target": board["goal"]["target"],
                        "needed_t": board["tries"].get("needed_t"), "best_t": top and _t(by[top["version"]].get("gate"))})
        return out

    @app.get("/api/missions/{mid}/refused")
    async def refused(mid: int):
        _mission(mid)
        return await asyncio.to_thread(hb.owner_refused, mid)

    # ---- connections and the hunt
    @app.get("/api/connections")
    async def connections():
        return {"health": await asyncio.to_thread(hb.health), "settings": config.settings(),
                "hunt_paused": system.hunt_paused()}

    @app.post("/api/connections")
    async def set_connections(body: dict = Body(...)):
        s = config.settings()
        s.update({k: body[k] for k in ("claude", "ntfy_topic") if k in body})
        config.save_settings(s)
        return s

    @app.post("/api/hunt")
    async def hunt(body: dict = Body(...)):
        with bad():
            on = bool(body["pause"])
        system.pause_hunt(on)
        return {"hunt_paused": system.hunt_paused()}

    return Guard(app)


def build():
    """The served app: the demo only when MISSIONS_DEMO is exactly "1"."""
    if os.environ.get("MISSIONS_DEMO") == "1":
        from . import demo
        return demo.make_app()
    return make_app(runner=True)


app = build()

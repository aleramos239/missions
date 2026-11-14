"""The HTTP API: the owner's pages. Local only (host/origin guard). It serves the OWNER, so /luck and /refused may show
test-month numbers; nothing written into a mission's chat/events here may carry one (the chat warning)."""
import asyncio
import json
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import briefing, config, engine, hb as _hb, store, system, worker

STATIC = Path(__file__).parent / "static"
HOSTS = ("127.0.0.1", "localhost")
ORIGINS = ("http://127.0.0.1:8860", "http://localhost:8860")
WARN = "This looks like a test-month number. The team must never see one. Send anyway?"
NUMBERISH = re.compile(r"\d\s*(?:%|\$|pts\b|points\b|trades\b)|\$\s*\d", re.I)
_odds = {}  # (mid, name, box) -> {"done", "result"/"err"}: one computation at a time
_odds_lock = threading.Lock()


class NotFound(Exception):
    pass


def _bad(msg, code=400):
    return JSONResponse({"error": msg}, status_code=code)


def _mission(mid):
    try:
        return store.load(mid)
    except (OSError, ValueError):
        raise NotFound(f"no mission {mid}") from None


def _badge(m):
    return {"waiting_owner": "needs you", "briefing": "brief", "waiting_plan": "waiting for the plan", "crashed": "error",
            "waiting_homebase": "Homebase down"}.get(m["status"])


def _t(gate):
    """The luck line's figure, if the Judge gave one."""
    for x in (gate or {}).get("lines", []):
        if x.get("line") == "luck":
            return x.get("t", x.get("value"))
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


async def event_stream(mid, after=0, *, poll=0.5, beat=15):
    """SSE lines: one `data:` per new event; a comment line every `beat` seconds of quiet (and first, to open the stream)."""
    yield ": open\n\n"
    quiet = 0.0
    while True:
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

    app = FastAPI(lifespan=life)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = request.headers.get("host", "")
        name = host[1:host.index("]")] if host.startswith("[") else host.rsplit(":", 1)[0] if ":" in host else host
        if name not in HOSTS:
            return _bad("this app answers only on 127.0.0.1", 403)
        o = request.headers.get("origin")
        if request.method != "GET" and o is not None and o not in ORIGINS:
            return _bad("foreign origin", 403)
        r = await call_next(request)
        if not request.url.path.startswith("/api"):
            r.headers["cache-control"] = "no-cache"
        return r

    @app.exception_handler(NotFound)
    async def _nf(_, e):
        return _bad(str(e), 404)

    @app.exception_handler(_hb.Down)
    async def _down(_, e):
        return _bad(f"Homebase is not answering: {e}", 503)

    @app.exception_handler(_hb.Refused)
    async def _ref(_, e):
        return _bad(str(e), 409)

    @app.exception_handler(ValueError)
    async def _val(_, e):
        return _bad(str(e), 400)

    @app.exception_handler(KeyError)
    async def _key(_, e):
        return _bad(f"missing {e}", 400)

    # ---- pages
    @app.get("/")
    async def index():
        p = STATIC / "index.html"
        return HTMLResponse(p.read_text() if p.exists() else "<title>Missions</title>")

    if STATIC.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")

    # ---- missions
    @app.get("/api/missions")
    async def sidebar():
        return [{"id": m["id"], "title": m["title"], "status": m["status"], "round": m["round"], "badge": _badge(m)}
                for m in store.missions()]

    async def brief_turn(mid, answer=None):
        out = await briefing.next_step(mid, answer, run_turn=run_turn, hb=hb)
        if "error" in out:
            store.event(mid, "chat", "engine", f"The brief stopped: {out['error']}", for_workers=False)
        return out

    @app.post("/api/missions")
    async def create(body: dict = Body(...)):
        m = store.new_mission(body["sentence"], body["team"], body.get("limits") or {}, body["test_months"])
        t = asyncio.create_task(brief_turn(m["id"]))
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
    async def stream(mid: int, after: int = 0):
        _mission(mid)
        return StreamingResponse(event_stream(mid, after), media_type="text/event-stream",
                                 headers={"cache-control": "no-cache"})

    # ---- the brief and the chat
    @app.post("/api/missions/{mid}/brief/answer")
    async def brief_answer(mid: int, body: dict = Body(...)):
        _mission(mid)
        out = await brief_turn(mid, body["text"])
        return _bad(out["error"], 409) if "error" in out else out

    @app.post("/api/missions/{mid}/brief/approve")
    async def brief_approve(mid: int, body: dict = Body(...)):
        _mission(mid)
        return briefing.approve(mid, body.get("said"), hb=hb)

    @app.post("/api/missions/{mid}/chat")
    async def chat(mid: int, body: dict = Body(...)):
        m = _mission(mid)
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("the text is empty")
        if m["reads"] >= 1 and NUMBERISH.search(text) and body.get("sure") is not True:
            return {"warn": WARN}
        return engine.owner_says(mid, body.get("to", "all"), text.strip())

    # ---- the engine's switches
    for name, fn in (("pause", engine.pause), ("resume", engine.resume), ("stop", engine.stop)):
        def sw(mid: int, fn=fn):
            _mission(mid)
            fn(mid)
            return {"status": store.load(mid)["status"]}
        app.add_api_route(f"/api/missions/{{mid}}/{name}", sw, methods=["POST"])

    @app.post("/api/missions/{mid}/read/approve")
    async def read_approve(mid: int, body: dict = Body(...)):
        _mission(mid)
        engine.approve_read(mid, body.get("said"))
        return {"status": store.load(mid)["status"]}

    @app.patch("/api/missions/{mid}")
    async def patch(mid: int, body: dict = Body(...)):
        m = _mission(mid)
        if "test_months" in body and body["test_months"] not in ("team", "ask"):
            raise ValueError("test_months is team or ask")
        if "limits" in body and not isinstance(body["limits"], dict):
            raise ValueError("limits must be an object")
        if "team" in body:
            for r in store.ROLES:
                t = (body["team"] or {}).get(r)
                if not isinstance(t, dict) or t.get("model") not in store.MODELS or t.get("effort") not in store.EFFORTS:
                    raise ValueError(f"bad team entry for {r}")
        for k in engine.OWNER_KEYS:
            if k in body:
                m[k] = body[k]
        store.save(m)
        if "test_months" in body:
            await asyncio.to_thread(hb.set_test_months, mid, body["test_months"])
        return m

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
        _mission(mid)
        return await asyncio.to_thread(hb.table, mid, name)

    @app.get("/api/missions/{mid}/box")
    async def box(mid: int, name: str, box: str):
        _mission(mid)
        t = await asyncio.to_thread(hb.table, mid, name)
        row = next((r for r in t.get("rows", []) if str(r.get("box")) == box), None)
        return {"row": row, "mc": await asyncio.to_thread(hb.mc, mid, name, box)}

    @app.get("/api/missions/{mid}/odds")
    async def odds(mid: int, name: str, box: str):
        _mission(mid)
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
        system.pause_hunt(bool(body["pause"]))
        return {"hunt_paused": system.hunt_paused()}

    return app


app = make_app(runner=True)

"""One worker turn: the fenced claude command, its stream, the caps."""
import asyncio
import collections
import json
import os
import signal
import time
from asyncio.subprocess import DEVNULL, PIPE
from dataclasses import dataclass, field

from missions import config

PREFIX = "mcp__homebase__"
_live = set()  # pids (= process groups) of running turns, so a shutdown can kill them


def kill_all():
    """The app is stopping: kill every running turn's process group (claude and its MCP child)."""
    for pid in list(_live):
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass
    _live.clear()


@dataclass
class Turn:
    text: str = ""
    session_id: str | None = None
    ok: bool = False
    why: str | None = None
    cost_usd: float = 0.0
    tool_calls: list = field(default_factory=list)
    rate: dict | None = None
    resets_at: int | None = None


def command(mid, role, model, effort, session_id, tools=True):
    hbr = config.homebase()
    mcp = {"mcpServers": {"homebase": {"command": str(config.hb_python()),
                                       "args": ["-m", "homebase.claude_mcp", "--mission", str(mid)],
                                       "env": {"PYTHONPATH": str(hbr), "HOMEBASE_MISSIONS": str(config.hb_missions())}}}}
    if not tools:  # no brief on file yet: the connector would refuse, so this turn gets no server at all
        mcp = {"mcpServers": {}}
    cmd = [str(config.claude_bin()), "-p", "--restricted", "--strict-mcp-config", "--mcp-config", json.dumps(mcp),
           "--tools", "", "--allowedTools", "mcp__homebase", "--permission-mode", "dontAsk",
           "--model", model, "--effort", effort, "--output-format", "stream-json", "--verbose"]
    return cmd + (["--resume", session_id] if session_id else [])


async def run_turn(mid, role, prompt, *, model, effort, session_id=None, max_tool_calls=40, timeout_s=1200,
                   on_event=None, init_out=None, tools=True) -> Turn:
    allow_tools = tools
    t = Turn()
    texts = []
    emit = on_event or (lambda kind, data: None)
    try:
        p = await asyncio.create_subprocess_exec(*command(mid, role, model, effort, session_id, tools), prompt,
                                                  cwd=config.work_dir(mid, role), stdin=DEVNULL, stdout=PIPE,
                                                  env={**os.environ, "MAX_MCP_OUTPUT_TOKENS": "60000"},
                                                  stderr=PIPE, limit=1 << 26, start_new_session=True)
    except OSError as e:
        t.why = f"crash: {e}"
        return t
    _live.add(p.pid)
    err = collections.deque(maxlen=4096)  # last ~4 KB of stderr: for the owner's log via `why`, never for a worker

    async def drain():
        while chunk := await p.stderr.read(4096):
            err.extend(chunk)
    drain_task = asyncio.ensure_future(drain())
    deadline = time.monotonic() + timeout_s
    result = None
    seen_init = False
    try:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                t.why = "timeout"
                break
            try:
                raw = await asyncio.wait_for(p.stdout.readline(), left)
            except asyncio.TimeoutError:
                t.why = "timeout"
                break
            except ValueError:
                continue  # a line over the buffer: skip it
            if not raw:
                break
            try:
                ev = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(ev, dict):
                continue
            kind = ev.get("type")
            if kind in ("assistant", "result") and not seen_init:
                t.why = "crash: fence: no init event before the first answer"
                break
            if kind == "system" and ev.get("subtype") == "init":
                seen_init = True
                tools, srv = ev.get("tools"), ev.get("mcp_servers")
                if allow_tools:
                    bad = (not tools or not all(isinstance(x, str) and x.startswith(PREFIX) for x in tools)
                           or not isinstance(srv, list) or len(srv) != 1 or not isinstance(srv[0], dict)
                           or srv[0].get("name") != "homebase" or srv[0].get("status") != "connected")
                else:
                    bad = bool(tools) or bool(srv)
                if bad:
                    t.why = f"crash: fence: tools={tools!r} mcp_servers={srv!r}"
                    break
                t.session_id = ev.get("session_id") or t.session_id
                if init_out is not None:
                    init_out.update(ev)
            elif kind == "assistant":
                for b in (ev.get("message") or {}).get("content") or []:
                    if b.get("type") == "text":
                        texts.append(b.get("text", ""))
                        emit("text", b.get("text", ""))
                    elif b.get("type") == "tool_use":
                        name, inp = b.get("name", ""), b.get("input")
                        t.tool_calls.append({"name": name, "input": inp})
                        emit("tool", {"name": name, "input": inp})
                        if not allow_tools or not name.startswith(PREFIX):
                            t.why = f"crash: a tool outside the fence: {name}"
                        elif len(t.tool_calls) > max_tool_calls:
                            t.why = "too many tool calls"
                if t.why:
                    break
            elif kind == "rate_limit_event":
                info = ev.get("rate_limit_info") or {}
                t.rate = info
                t.resets_at = info.get("resetsAt") or t.resets_at
                emit("rate", info)
                if info.get("status") == "rejected":
                    t.why = "plan"
                    break
            elif kind == "result":
                result = ev
                break
    finally:
        _live.discard(p.pid)
        try:
            os.killpg(p.pid, signal.SIGKILL)  # the whole group, so the MCP child dies too
        except (ProcessLookupError, PermissionError):  # macOS: PermissionError on a zombie-only group
            pass
        try:
            await p.wait()
        finally:
            try:
                await asyncio.wait_for(drain_task, 5)
            except asyncio.TimeoutError:
                drain_task.cancel()
    t.text = "\n".join(x for x in texts if x)
    if result:
        t.session_id = result.get("session_id") or t.session_id
        t.cost_usd = float(result.get("total_cost_usd") or 0)
        t.ok = result.get("is_error") is False
        if result.get("is_error") and result.get("api_error_status") == 429:
            t.why = t.why or "plan"
    elif t.why is None:
        t.why = "crash: no result: " + bytes(err).decode("utf-8", "replace").strip()
    return t

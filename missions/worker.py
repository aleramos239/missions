"""One worker turn: the fenced claude command, its stream, the caps."""
import asyncio
import json
import time
from asyncio.subprocess import DEVNULL, PIPE
from dataclasses import dataclass, field

from missions import config

PREFIX = "mcp__homebase__"


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


def command(mid, role, model, effort, session_id):
    hbr = config.homebase()
    mcp = {"mcpServers": {"homebase": {"command": str(config.hb_python()),
                                       "args": ["-m", "homebase.claude_mcp", "--mission", str(mid)],
                                       "env": {"PYTHONPATH": str(hbr), "HOMEBASE_MISSIONS": str(config.hb_missions())}}}}
    cmd = [str(config.claude_bin()), "-p", "--restricted", "--strict-mcp-config", "--mcp-config", json.dumps(mcp),
           "--tools", "", "--allowedTools", "mcp__homebase", "--permission-mode", "dontAsk",
           "--model", model, "--effort", effort, "--output-format", "stream-json", "--verbose"]
    return cmd + (["--resume", session_id] if session_id else [])


async def run_turn(mid, role, prompt, *, model, effort, session_id=None, max_tool_calls=40, timeout_s=1200,
                   on_event=None, init_out=None) -> Turn:
    t = Turn()
    texts = []
    emit = on_event or (lambda kind, data: None)
    try:
        p = await asyncio.create_subprocess_exec(*command(mid, role, model, effort, session_id), prompt,
                                                  cwd=config.work_dir(mid, role), stdin=DEVNULL, stdout=PIPE,
                                                  stderr=DEVNULL, limit=1 << 26)
    except OSError as e:
        t.why = f"crash: {e}"
        return t
    deadline = time.monotonic() + timeout_s
    result = None
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
            if kind == "system" and ev.get("subtype") == "init":
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
                        if not name.startswith(PREFIX):
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
        if p.returncode is None:
            p.kill()
        await p.wait()
    t.text = "\n".join(x for x in texts if x)
    if result:
        t.session_id = result.get("session_id") or t.session_id
        t.cost_usd = float(result.get("total_cost_usd") or 0)
        t.ok = result.get("is_error") is False
        if result.get("is_error") and result.get("api_error_status") == 429:
            t.why = t.why or "plan"
    elif t.why is None:
        t.why = "crash: no result"
    return t

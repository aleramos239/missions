import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from missions import config, worker

FAKE = str(Path(__file__).parent / "fakes" / "claude")


def ev(**k):
    return json.dumps(k)


def text(s):
    return ev(type="assistant", message={"content": [{"type": "text", "text": s}]})


def tool(name):
    return ev(type="assistant", message={"content": [{"type": "tool_use", "name": name, "input": {"a": 1}}]})


RESULT = ev(type="result", subtype="success", is_error=False, session_id="S1", total_cost_usd=0.25)


@pytest.fixture
def fake(tmp_path, monkeypatch):
    config.save_settings({"claude": FAKE})
    monkeypatch.setenv("FAKE_CLAUDE_ARGV", str(tmp_path / "argv.json"))

    def go(lines, delay=0, **kw):
        (tmp_path / "stream").write_text("\n".join(lines))
        monkeypatch.setenv("FAKE_CLAUDE_STREAM", str(tmp_path / "stream"))
        monkeypatch.setenv("FAKE_CLAUDE_DELAY", str(delay))
        t = asyncio.run(worker.run_turn(7, "lead", "hi", model="haiku", effort="low", **kw))
        argv = json.loads((tmp_path / "argv.json").read_text())
        return t, argv
    return go


def test_command_flags():
    config.save_settings({"claude": FAKE})
    c = worker.command(7, "lead", "haiku", "low", None)
    assert c[c.index("--tools") + 1] == ""
    assert c[c.index("--permission-mode") + 1] == "dontAsk"
    for f in ("--restricted", "--strict-mcp-config"):
        assert f in c
    assert json.loads(c[c.index("--mcp-config") + 1])["mcpServers"]["homebase"]["args"][-1] == "7"
    for bad in ("--bare", "bypassPermissions", "--add-dir", "--resume"):
        assert bad not in c
    assert worker.command(7, "lead", "haiku", "low", "S")[-2:] == ["--resume", "S"]


def test_stream(fake):
    t, argv = fake([ev(type="system", subtype="init", session_id="S0"), text("one"),
                    tool("mcp__homebase__backtest"), text("two"), RESULT])
    assert (t.text, t.session_id, t.cost_usd, t.ok, t.why) == ("one\ntwo", "S1", 0.25, True, None)
    assert t.tool_calls == [{"name": "mcp__homebase__backtest", "input": {"a": 1}}]
    assert argv["argv"][-1] == "hi"
    assert argv["cwd"].endswith("_work/7/lead")
    assert argv["ls"] == []


def test_noise_skipped(fake):
    t, _ = fake(["not json", text("x"), RESULT])
    assert t.ok and t.text == "x"


def test_too_many(fake):
    t, _ = fake([tool("mcp__homebase__a")] * 41 + [RESULT], max_tool_calls=40)
    assert t.why == "too many tool calls" and not t.ok


def test_timeout(fake):
    t, _ = fake([text("a"), text("b"), RESULT], delay=1, timeout_s=0.3)
    assert t.why == "timeout"


def test_plan(fake):
    t, _ = fake([ev(type="rate_limit_event", rate_limit_info={"status": "rejected", "resetsAt": 123}), RESULT])
    assert t.why == "plan" and t.resets_at == 123


def test_plan_429(fake):
    t, _ = fake([ev(type="result", is_error=True, api_error_status=429, session_id="S")])
    assert t.why == "plan" and not t.ok


def test_outside_fence(fake):
    t, _ = fake([tool("Bash"), RESULT])
    assert t.why.startswith("crash: a tool outside the fence")


def test_blindcheck_verdict():
    from missions import blindcheck
    tools = [f"mcp__homebase__t{i}" for i in range(9)]
    init = {"tools": tools, "mcp_servers": [{"name": "homebase", "status": "connected"}]}
    t = worker.Turn(text="\n".join(tools) + "\n\n**3.** No. I see no CLAUDE.md.")
    assert all(blindcheck.verdict(init, t).values())
    init["tools"] = tools + ["Bash"]
    assert not all(blindcheck.verdict(init, t).values())

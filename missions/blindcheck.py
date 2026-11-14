"""python -m missions.blindcheck: one real haiku turn proving what a worker sees. Needs the Homebase chart service."""
import asyncio
import json
import os
import re
import socket
import sys
import tempfile
from pathlib import Path

from missions import config, worker

PROMPT = ("List the exact names of every tool you have. Then try to read the file /etc/hosts and say what happened. "
          "Then say whether you see any CLAUDE.md, memory or RECENT instructions: yes or no.")
MID = 987654


def verdict(init, t) -> dict:
    names = set(re.findall(r"mcp__homebase__\w+", t.text))
    srv = init.get("mcp_servers") or []
    last = t.text.strip().split("\n\n")[-1].lower()
    # init.tools lists the MCP tools too: the fence holds when it names nothing else (no built-in tool).
    return {
        "init.tools has only mcp__homebase__ tools (no built-ins)": bool(init.get("tools")) and all(x.startswith("mcp__homebase__") for x in init["tools"]),
        "only homebase, connected": [x.get("name") for x in srv] == ["homebase"] and srv[0].get("status") == "connected",
        "9 mcp__homebase__ tools listed": len(names) == 9,
        "no tool use outside mcp__homebase__": all(c["name"].startswith("mcp__homebase__") for c in t.tool_calls),
        "reply says no CLAUDE.md/memory/RECENT": bool(re.search(r"\bno\b", last)) and "yes" not in last,
    }


def main() -> int:
    with socket.socket() as s:
        s.settimeout(2)
        if s.connect_ex(("127.0.0.1", config.chart_port())) != 0:
            print(f"The Homebase chart service is not up on port {config.chart_port()}.")
            return 3
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HOMEBASE_MISSIONS"] = tmp
        os.environ.setdefault("MISSIONS_HOME", str(Path(tmp) / "home"))
        d = Path(tmp) / str(MID)
        d.mkdir()
        (d / "brief.json").write_text(json.dumps({"approved": True, "owner_said": "blind check", "test_months": "ask",
                                                  "goal": {"kind": "points", "target": 1.0}}))
        init = {}
        t = asyncio.run(worker.run_turn(MID, "blindcheck", PROMPT, model="haiku", effort="low", max_tool_calls=3,
                                        timeout_s=300, init_out=init))
    print("init.tools:", init.get("tools"))
    print("init.mcp_servers:", init.get("mcp_servers"))
    print("tool calls:", [c["name"] for c in t.tool_calls])
    print("why:", t.why, "ok:", t.ok)
    print("reply:\n" + t.text)
    checks = verdict(init, t)
    for k, v in checks.items():
        print("PASS" if v else "FAIL", k)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

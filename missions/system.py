"""Limits, the Claude plan reserve, keep-awake, alerts, and the hunt pause. No worker text is built here."""
import json
import logging
import os
import re
import subprocess
import time
import urllib.request

from . import config, store

log = logging.getLogger(__name__)
RESERVE = 0.90
UNKNOWN_WAIT = 900
ALERTS = {"achieved": "goal reached", "limit": "a limit ran out", "out_of_reach": "out of reach",
          "waiting_plan": "waiting for the Claude plan to reset", "waiting_owner": "waiting for your yes to read the test months",
          "crashed": "stopped by an error", "tool": "a new tool waits for your yes"}
RUNNING = ("running", "waiting_homebase")  # Homebase being down is still mission time
STEERING = "30-Projects/Onyx-Trading/Hunt/hunt-steering.md"


def _path():
    return config.home() / "usage.json"


def _load():
    try:
        return json.loads(_path().read_text())
    except (OSError, ValueError):
        return {}


def note_rate(rate) -> None:
    """Keep the newest figure of each window the CLI reports (shortcut: needs the CLI's utilization field)."""
    if not isinstance(rate, dict) or rate.get("rateLimitType") not in ("five_hour", "seven_day"):
        return
    d = _load()
    u = rate.get("utilization")
    if rate.get("status") == "rejected":
        u = 1.0
    if not isinstance(u, (int, float)):
        return
    d[rate["rateLimitType"]] = {"used": u / 100 if u > 1 else u, "resets_at": rate.get("resetsAt")}
    d["at"] = time.time()
    config.home().mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(d))
    os.replace(tmp, _path())


def usage() -> dict:
    d = _load()
    return {"five_hour": d.get("five_hour"), "seven_day": d.get("seven_day"), "at": d.get("at")}


def may_start_turn(now=None):
    now = time.time() if now is None else now
    for w in (usage()["five_hour"], usage()["seven_day"]):
        if w and w["used"] >= RESERVE and not (w["resets_at"] and w["resets_at"] <= now):  # a passed reset is stale
            return False, w["resets_at"]
    return True, None


async def wait_for_plan(resets_at, *, sleep, now=None) -> None:
    now = time.time() if now is None else now
    await sleep(max(0, resets_at - now) + 60 if resets_at else UNKNOWN_WAIT)


def limit_hit(m, tries_mission):
    lim = m.get("limits") or {}
    if lim.get("until_goal"):
        return None
    if (t := lim.get("tries")) and tries_mission >= t["n"]:
        return "tries"
    if (h := lim.get("hours")) and m["run_seconds"] >= h["n"] * 3600:
        return "hours"
    w = usage()["seven_day"]
    if (u := lim.get("usage")) and w and m.get("usage_start") is not None \
            and w["used"] - m["usage_start"] >= u["pct"] / 100:
        return "usage"
    return None


def awake(on: bool) -> None:
    pidf = config.home() / "awake.pid"
    try:
        pid = int(pidf.read_text())
    except (OSError, ValueError):
        pid = None
    if on and pid is None:
        config.home().mkdir(parents=True, exist_ok=True)
        pidf.write_text(str(subprocess.Popen(["caffeinate", "-i", "-s"]).pid))
    elif not on and pid is not None:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        pidf.unlink(missing_ok=True)


def alert(mid, kind) -> None:
    if kind not in ALERTS:
        return
    text = f"Mission {mid}: {ALERTS[kind]}"
    try:
        subprocess.Popen(["osascript", "-e", f'display notification "{text}" with title "Missions"'])
        if isinstance(topic := config.settings().get("ntfy_topic"), str) and topic:
            urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{topic}", data=text.encode()), timeout=10)
    except Exception as e:
        log.warning("alert failed: %s", e)


def _steering():
    return config.vault() / STEERING


def hunt_paused():
    try:
        m = re.search(r"^PAUSE:\s*(yes|no)\s*$", _steering().read_text(), re.M | re.I)
    except OSError:
        return None
    return m and m.group(1).lower() == "yes"


def pause_hunt(on: bool) -> None:
    p = _steering()
    p.write_text(re.sub(r"^PAUSE:.*$", f"PAUSE: {'yes' if on else 'no'}", p.read_text(), count=1, flags=re.M))

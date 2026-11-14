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


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def note_rate(rate) -> None:
    """Keep the newest figure of each window. CLI shape: unifiedWindows{five_hour,seven_day}{utilization 0-1, resetsAt,
    status}; top-level fields count only for those two types; any rejected event blocks until its resetsAt."""
    if not isinstance(rate, dict):
        return
    d, now, changed = _load(), time.time(), False
    uw = rate.get("unifiedWindows") if isinstance(rate.get("unifiedWindows"), dict) else {}
    for key in ("five_hour", "seven_day"):
        w = uw.get(key) if isinstance(uw.get(key), dict) else None
        if w is None and rate.get("rateLimitType") == key:
            w = rate
        if w is None:
            continue
        u = 1.0 if w.get("status") == "rejected" else w.get("utilization")
        if _num(u):
            d[key] = {"used": u, "resets_at": w.get("resetsAt"), "at": now}
            changed = True
    if rate.get("status") == "rejected":
        d["rejected"] = {"resets_at": rate.get("resetsAt"), "at": now}
        changed = True
    if not changed:
        return
    d["at"] = now
    config.home().mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(d))
    os.replace(tmp, _path())


def usage() -> dict:
    d = _load()
    return {"five_hour": d.get("five_hour"), "seven_day": d.get("seven_day"), "at": d.get("at")}


def _live(w, now):
    """A figure still counts until its reset passes; with no reset known, for 15 minutes after it was seen."""
    r = w.get("resets_at")
    return r > now if r else now - w.get("at", 0) < UNKNOWN_WAIT


def may_start_turn(now=None):
    now = time.time() if now is None else now
    d = _load()
    for w in (d.get("rejected"), d.get("five_hour"), d.get("seven_day")):
        if w and (w.get("used", 1.0) >= RESERVE) and _live(w, now):
            return False, w.get("resets_at")
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


def _is_caffeinate(pid) -> bool:
    """Alive and really our caffeinate (a stale awake.pid may hold a reused pid)."""
    try:
        r = subprocess.run(["ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "caffeinate" in r.stdout


def awake(on: bool) -> None:
    pidf = config.home() / "awake.pid"
    try:
        pid = int(pidf.read_text())
    except (OSError, ValueError):
        pid = None
    if pid is not None and not _is_caffeinate(pid):
        pidf.unlink(missing_ok=True)
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
    try:
        txt = p.read_text()
    except OSError as e:
        log.warning("hunt steering note not readable: %s", e)
        return
    p.write_text(re.sub(r"^PAUSE:.*$", f"PAUSE: {'yes' if on else 'no'}", txt, count=1, flags=re.M))

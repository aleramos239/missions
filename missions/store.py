import fcntl
import json
import os
import shutil
from datetime import datetime, timezone

from . import config

ROLES = ("lead", "builder", "doubter", "defender")
STATUS = ("briefing", "ready", "queued", "running", "paused", "waiting_plan", "waiting_homebase", "waiting_owner",
          "achieved", "limit", "out_of_reach", "stopped", "crashed")
DONE = ("achieved", "limit", "out_of_reach", "stopped")
MODELS = ("fable", "opus", "sonnet", "haiku")
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ids(p):
    return [int(d.name) for d in p.glob("*") if d.name.isdigit()] if p.exists() else []


def mdir(mid):
    return config.home() / str(mid)


def events_path(mid):
    return mdir(mid) / "events.jsonl"


LIMITS = ("tries", "stages", "hours", "usage", "until_goal")


def check_limits(lim):
    """tries: {"n": int > 0} (per stage); stages: {"n": int > 0}; hours: {"n": number > 0}; usage: {"pct": number > 0}; until_goal: true or false. Anything else is a ValueError."""
    if not isinstance(lim, dict) or set(lim) - set(LIMITS):
        raise ValueError(f"limits is an object with only {list(LIMITS)}")
    for k, v in lim.items():
        if k == "until_goal":
            ok = isinstance(v, bool)
        else:
            f = "pct" if k == "usage" else "n"
            x = v.get(f) if isinstance(v, dict) and set(v) == {f} else None
            ok = isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0 and (k not in ("tries", "stages") or isinstance(x, int))
        if not ok:
            raise ValueError(f"bad limit {k}: {v!r}")


def check_team(team):
    """Exactly the four roles, each {model, effort} from MODELS and EFFORTS; else ValueError."""
    if not isinstance(team, dict) or set(team) != set(ROLES):
        raise ValueError(f"team needs exactly {list(ROLES)}")
    for r in ROLES:
        t = team[r]
        if not isinstance(t, dict) or t.get("model") not in MODELS or t.get("effort") not in EFFORTS:
            raise ValueError(f"bad team entry for {r}: {t}")


DEFAULT_TEAM = {"lead": {"model": "opus", "effort": "high"}, "builder": {"model": "sonnet", "effort": "high"},
                "doubter": {"model": "sonnet", "effort": "medium"}, "defender": {"model": "sonnet", "effort": "medium"}}


def team_defaults() -> dict:
    t = config.settings().get("team_defaults")
    try:
        check_team(t)
        return t
    except ValueError:
        return DEFAULT_TEAM


def _last_id():
    try:
        return int((config.home() / "last_id").read_text())
    except (OSError, ValueError):
        return 0


def delete(mid):
    shutil.rmtree(mdir(mid))
    shutil.rmtree(config.home() / "_work" / str(mid), ignore_errors=True)


def new_mission(sentence: str, team: dict, limits: dict, test_months: str) -> dict:
    check_limits(limits)
    if test_months not in ("team", "ask"):
        raise ValueError("bad team or test_months")
    check_team(team)
    config.home().mkdir(parents=True, exist_ok=True)
    # mkdir is the claim: two callers cannot take the same id (shortcut: skips ids on a race)
    while True:
        mid = 1 + max(_ids(config.home()) + _ids(config.hb_missions()) + [_last_id()], default=0)
        try:
            mdir(mid).mkdir()
            (config.home() / "last_id").write_text(str(mid))  # a deleted id is never handed out again
            break
        except FileExistsError:
            continue
    m = {"id": mid, "title": sentence[:40], "sentence": sentence, "created": _now(), "status": "briefing",
         "team": team, "limits": limits, "test_months": test_months, "brief": None, "round": 0, "step": None,
         "sessions": {}, "versions": [], "pending": {}, "empty_rounds": 0, "run_seconds": 0,
         "usage_start": None, "cost_usd": 0.0, "reads": 0, "result": None}
    save(m)
    return m


def load(mid) -> dict:
    return json.loads((mdir(mid) / "mission.json").read_text())


def save(m: dict) -> None:
    p = mdir(m["id"]) / "mission.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, indent=2))
    os.replace(tmp, p)


def missions() -> list[dict]:
    out = []
    for i in sorted(_ids(config.home()), reverse=True):
        try:
            out.append(load(i))
        except (OSError, ValueError):
            pass
    return out


def event(mid, type, who, text="", data=None, to=None, for_workers=True) -> dict:
    p = events_path(mid)
    with open(p, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        txt = f.read()
        n = max((r["n"] for r in _rows(txt)), default=0) + 1
        if txt and not txt.endswith("\n"):
            f.write("\n")  # close a torn line so the new row stands alone
        e = {"n": n, "at": _now(), "type": type, "who": who, "to": to, "text": text, "data": data,
             "for_workers": for_workers}
        f.write(json.dumps(e) + "\n")
        f.flush()
    return e


def _rows(txt):
    rows = []
    for line in txt.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass  # torn line
    return rows


def events(mid, after=0) -> list[dict]:
    try:
        rows = _rows(events_path(mid).read_text())
    except OSError:
        return []
    return [e for e in rows if e["n"] > after]

"""The brief: the Lead asks the owner up to QUESTIONS_MAX things, the engine validates what he writes, the owner says yes."""
import asyncio
import math
from datetime import date

from . import digest as _digest, roles, store

QUESTIONS_MAX = 6
KINDS = ("eval", "points", "net", "years")
RETRY = "Your last answer was refused: {why}. Fix it and answer again."
NOW = "You have asked enough: write the brief now (the {\"brief\": {...}} block), no more questions."
TARGETS_R = (0.5, 0.75, 1, 1.5, 2)
BUSY = ("running", "paused", "waiting_plan", "waiting_homebase", "waiting_owner")


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _strs(b, k):
    v = b.get(k)
    if not isinstance(v, list) or not all(isinstance(s, str) and s.strip() for s in v):
        return f"{k} must be a list of plain sentences"


def check(brief, accounts):
    """The reason a brief is refused, or None. The engine decides, never the Lead."""
    if not isinstance(brief, dict):
        return "the brief is not an object"
    if "drafts" in brief:
        return "drafts are off for missions"
    g = brief.get("goal")
    if not isinstance(g, dict):
        return "goal is missing"
    if g.get("kind") not in KINDS:
        return f"goal.kind must be one of {list(KINDS)}"
    if g["kind"] == "years":
        rc = g.get("recent")
        if not isinstance(rc, list) or not rc or any(type(y) is not int or not 2017 <= y <= 2030 for y in rc):
            return "goal.recent must be a list of years 2017-2030"
        if not _num(g.get("win_min")) or not 0 < g["win_min"] < 1:
            return "goal.win_min must be a share between 0 and 1 (0.40, not 40)"
        if g.get("rest") != "green":
            return 'goal.rest must be "green"'
        t = g["win_min"]
    else:
        t = g.get("target")
    if not _num(t) or t <= 0:
        return "goal.target must be a number above 0"
    if g["kind"] == "eval":
        if t > 1:
            return "an eval target is a share between 0 and 1 (0.5, not 50)"
        if not isinstance(g.get("rule"), str) or g["rule"] not in {a.get("id") for a in accounts}:
            return f"goal.rule must be one of the open accounts: {[a.get('id') for a in accounts]}"
        if "days" in g and (type(g["days"]) is not int or not 1 <= g["days"] <= 20):
            return "goal.days must be a whole number of weekdays from 1 to 20"
    elif "days" in g:
        return "goal.days is for eval goals only"
    if brief.get("exits", "hm40") not in ("hm40", "hm60"):
        return "exits must be hm40 or hm60"
    if "target_r" in brief and (not _num(brief["target_r"]) or brief["target_r"] not in TARGETS_R):
        return f"target_r must be one of {list(TARGETS_R)}"
    if "base" in brief:
        b = brief["base"]
        if not (isinstance(b, dict) and set(b) == {"mission", "version"} and type(b["mission"]) is int
                and isinstance(b["version"], str)):
            return 'base must be {"mission": <id>, "version": "vNN"}'
        try:
            ok = any(v["version"] == b["version"] for v in store.load(b["mission"])["versions"])
        except (OSError, ValueError, KeyError):
            ok = False
        if not ok:
            return f"base: mission {b['mission']} has no version {b['version']}"
    if not isinstance(brief.get("idea"), str) or not brief["idea"].strip():
        return "idea is missing"
    for k in ("fixed", "may_change"):
        if e := _strs(brief, k):
            return e
    f = brief.get("fewest_trades_week")
    if not _num(f) or f <= 0:
        return "fewest_trades_week must be a number above 0"
    if not isinstance(brief.get("notes"), str):
        return "notes must be text"


def _clean(b):
    g = b["goal"]
    goal = {"kind": g["kind"], "target": g["win_min"] if g["kind"] == "years" else g["target"]}
    if g["kind"] == "years":
        goal.update(recent=sorted(set(g["recent"])), win_min=g["win_min"], rest="green")
    if g["kind"] == "eval":
        goal["rule"] = g["rule"]
        if "days" in g:
            goal["days"] = g["days"]
    return {"goal": goal, "idea": b["idea"].strip(), "fixed": b["fixed"], "may_change": b["may_change"],
            "fewest_trades_week": b["fewest_trades_week"], "notes": b["notes"],
            **{k: b[k] for k in ("exits", "target_r", "base") if k in b}}


def _ask_ok(a):
    o = a.get("options") if isinstance(a, dict) else None
    if not (isinstance(a, dict) and isinstance(a.get("q"), str) and a["q"].strip() and isinstance(o, list)
            and 2 <= len(o) <= 4 and all(isinstance(s, str) and s.strip() for s in o)):
        return "ask needs a question and 2 to 4 reply buttons"


def _chat(mid):
    return "\n".join(f"{e['who']}: {e['text']}" for e in store.events(mid) if e["type"] == "chat" and e["text"])


_locks = {}


def _lock(mid):
    return _locks.setdefault((asyncio.get_running_loop(), mid), asyncio.Lock())


async def next_step(mid, answer=None, *, run_turn, hb):
    async with _lock(mid):
        return await _step(mid, answer, run_turn, hb)


async def _step(mid, answer, run_turn, hb):
    m = store.load(mid)
    if m["status"] != "briefing":
        return {"error": f"the mission is {m['status']}, not briefing"}
    m["brief"] = None  # a leftover brief is never approvable; saved now so an error leaves none
    store.save(m)
    p = m["pending"].setdefault("brief", {"asked": 0})
    if answer:
        store.event(mid, "chat", "owner", answer)
    accounts = await asyncio.to_thread(hb.accounts)
    ask = answer or None
    lead = m["team"]["lead"]
    for attempt in (0, 1):
        if p["asked"] >= QUESTIONS_MAX:
            ask = f"{ask}\n\n{NOW}" if ask else NOW
        pr = roles.prompt("lead", "brief", brief=m["sentence"], board=accounts, chat=_chat(mid), ask=ask,
                          digest=_digest.digest())
        t = await run_turn(mid, "lead", pr, model=lead["model"], effort=lead["effort"],
                           session_id=m["sessions"].get("lead"), tools=False)
        m["sessions"]["lead"] = t.session_id or m["sessions"].get("lead")
        if not t.ok:
            _save(mid, m)
            return {"error": t.why or "the Lead's turn failed"}
        r = roles.reply(t.text) or {}
        # brief first: a reply holding both is the Lead finishing, and an ask must not hide a finished brief
        if "brief" in r:
            why = check(r["brief"], accounts)
        elif "ask" in r and p["asked"] < QUESTIONS_MAX:
            why = _ask_ok(r["ask"])
        else:
            why = "answer with an ask, or the brief" if p["asked"] < QUESTIONS_MAX else "write the brief now"
        if not why:
            break
        if attempt == 0:
            ask = RETRY.format(why=why)
            continue
        _save(mid, m)
        store.event(mid, "chat", "engine", f"The Lead's brief was refused twice: {why}", for_workers=False)
        return {"error": why}
    if "brief" in r:
        m["brief"], out = _clean(r["brief"]), None
        store.event(mid, "chat", "lead", roles.say(t.text))
        out = {"brief": m["brief"]}
    else:
        p["asked"] += 1
        a = r["ask"]
        store.event(mid, "chat", "lead", roles.say(t.text) or a["q"], data={"ask": a})
        out = {"ask": {"q": a["q"], "options": a["options"]}}
    _save(mid, m)
    return out


def _save(mid, m):
    """Save only what this step owns onto a fresh copy, so an overlapping change (status) is never overwritten."""
    f = store.load(mid)
    f["brief"], f["sessions"], f["pending"] = m["brief"], m["sessions"], m["pending"]
    store.save(f)


async def approve(mid, said, *, hb):
    """Holds the mission's lock for its whole run; refused while the Lead's turn holds it. Only the hb calls leave the loop."""
    if not isinstance(said, str) or not said.strip():
        raise ValueError("the owner's words are needed")
    lock = _lock(mid)
    if lock.locked():
        raise ValueError("the Lead is still working")
    async with lock:  # no await between the check and this: nothing slips in
        m = store.load(mid)
        if m["status"] != "briefing":
            raise ValueError(f"the mission is {m['status']}: it can only be approved while briefing")
        b = m["brief"]
        if not b or check(b, await asyncio.to_thread(hb.accounts)):
            raise ValueError("there is no valid brief to approve")
        await asyncio.to_thread(hb.write_brief, mid, {
            "approved": True, "owner_said": f"{said.strip()} (mission {mid}, {date.today()}: {m['sentence']})",
            "test_months": m["test_months"], "goal": b["goal"], **{k: b[k] for k in ("exits", "target_r") if b.get(k)}})
        busy = any(o["id"] != mid and o["status"] in BUSY for o in store.missions())
        m["status"] = "queued" if busy else "ready"
        store.save(m)
        store.event(mid, "status", "engine", m["status"])
        return m


def page(brief, accounts):
    a = next((x for x in accounts if x.get("id") == brief["goal"].get("rule")), None)
    return {**brief, "account": a, "bans": (a or {}).get("bans", [])}

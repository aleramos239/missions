"""The brief: the Lead asks the owner up to QUESTIONS_MAX things, the engine validates what he writes, the owner says yes."""
from datetime import date

from . import digest as _digest, roles, store

QUESTIONS_MAX = 6
KINDS = ("eval", "points", "net")
RETRY = "Your last answer was refused: {why}. Fix it and answer again."
NOW = "You have asked enough. Write the brief now (the {\"brief\": {...}} block), no more questions."
BUSY = ("running", "paused", "waiting_plan", "waiting_owner")


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


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
    t = g.get("target")
    if not _num(t) or t <= 0:
        return "goal.target must be a number above 0"
    if g["kind"] == "eval":
        if t > 1:
            return "an eval target is a share between 0 and 1 (0.5, not 50)"
        if g.get("rule") not in {a.get("id") for a in accounts}:
            return f"goal.rule must be one of the open accounts: {[a.get('id') for a in accounts]}"
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
    goal = {"kind": g["kind"], "target": g["target"]}
    if g.get("rule"):
        goal["rule"] = g["rule"]
    return {"goal": goal, "idea": b["idea"].strip(), "fixed": b["fixed"], "may_change": b["may_change"],
            "fewest_trades_week": b["fewest_trades_week"], "notes": b["notes"]}


def _ask_ok(a):
    o = a.get("options") if isinstance(a, dict) else None
    if not (isinstance(a, dict) and isinstance(a.get("q"), str) and a["q"].strip() and isinstance(o, list)
            and 2 <= len(o) <= 4 and all(isinstance(s, str) and s.strip() for s in o)):
        return "ask needs a question and 2 to 4 reply buttons"


def _chat(mid):
    return "\n".join(f"{e['who']}: {e['text']}" for e in store.events(mid) if e["type"] == "chat" and e["text"])


async def next_step(mid, answer=None, *, run_turn, hb):
    m = store.load(mid)
    p = m["pending"].setdefault("brief", {"asked": 0})
    if answer:
        store.event(mid, "chat", "owner", answer)
    accounts = hb.accounts()
    ask = answer or None
    lead = m["team"]["lead"]
    for attempt in (0, 1):
        if p["asked"] >= QUESTIONS_MAX:
            ask = f"{ask}\n\n{NOW}" if ask else NOW
        pr = roles.prompt("lead", "brief", brief=m["sentence"], board=accounts, chat=_chat(mid), ask=ask,
                          digest=_digest.digest())
        t = await run_turn(mid, "lead", pr, model=lead["model"], effort=lead["effort"],
                           session_id=m["sessions"].get("lead"))
        m["sessions"]["lead"] = t.session_id or m["sessions"].get("lead")
        if not t.ok:
            store.save(m)
            return {"error": t.why or "the Lead's turn failed"}
        r = roles.reply(t.text) or {}
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
        store.save(m)
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
    store.save(m)
    return out


def approve(mid, said, *, hb):
    if not isinstance(said, str) or not said.strip():
        raise ValueError("the owner's words are needed")
    m = store.load(mid)
    b = m["brief"]
    if not b or check(b, hb.accounts()):
        raise ValueError("there is no valid brief to approve")
    hb.write_brief(mid, {"approved": True, "owner_said": f"{said.strip()} (mission {mid}, {date.today()}: {m['sentence']})",
                         "test_months": m["test_months"], "goal": b["goal"]})
    busy = any(o["id"] != mid and o["status"] in BUSY for o in store.missions())
    m["status"] = "queued" if busy else "ready"
    store.save(m)
    store.event(mid, "status", "engine", m["status"])
    return m


def page(brief, accounts):
    a = next((x for x in accounts if x.get("id") == brief["goal"].get("rule")), None)
    return {**brief, "account": a, "bans": (a or {}).get("bans", [])}

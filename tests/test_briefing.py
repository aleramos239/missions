import asyncio

import pytest

from missions import briefing, store, worker
from tests.fakes.hb import FakeHB

TEAM = {r: {"model": "haiku", "effort": "low"} for r in store.ROLES}
GOOD = {"goal": {"kind": "eval", "target": 0.5, "rule": "lucid-live-50k"}, "idea": "9:30 follow",
        "fixed": ["NQ"], "may_change": ["stop"], "fewest_trades_week": 2.0, "notes": ""}


def block(d):
    import json
    return "Here.\n```json\n" + json.dumps(d) + "\n```"


class Lead:
    def __init__(self, *texts):
        self.texts, self.prompts, self.sessions = list(texts), [], []

    async def __call__(self, mid, role, prompt, *, model, effort, session_id=None, **kw):
        self.prompts.append(prompt)
        self.sessions.append(session_id)
        return worker.Turn(text=self.texts.pop(0), session_id="s1", ok=True)


@pytest.fixture
def hb():
    f = FakeHB()
    f.accounts_ = [{"id": "lucid-live-50k", "name": "Lucid", "size": 50000, "drawdown": 2000, "risk": 500,
                    "bans": ["news"]}]
    return f


def mk(sentence="pass the 50k", test_months="team"):
    return store.new_mission(sentence, TEAM, {}, test_months)["id"]


def run(c):
    return asyncio.run(c)


def test_question_then_answer_same_session(hb):
    mid = mk()
    lead = Lead(block({"ask": {"q": "Which account?", "options": ["50k", "100k"]}}), block({"brief": GOOD}))
    r = run(briefing.next_step(mid, run_turn=lead, hb=hb))
    assert r == {"ask": {"q": "Which account?", "options": ["50k", "100k"]}}
    assert any(e["who"] == "lead" for e in store.events(mid))
    r = run(briefing.next_step(mid, "50k", run_turn=lead, hb=hb))
    assert r["brief"]["goal"]["target"] == 0.5
    assert lead.sessions == [None, "s1"]
    assert "50k" in lead.prompts[1] and any(e["who"] == "owner" for e in store.events(mid))


def test_after_max_questions_write_now(hb):
    mid = mk()
    q = block({"ask": {"q": "?", "options": ["a", "b"]}})
    lead = Lead(*[q] * 6, block({"brief": GOOD}))
    for _ in range(6):
        run(briefing.next_step(mid, "x", run_turn=lead, hb=hb))
    assert "write the brief now" not in lead.prompts[5]
    assert "write the brief now" in (run(briefing.next_step(mid, "y", run_turn=lead, hb=hb)) and lead.prompts[6])


@pytest.mark.parametrize("bad", [
    {"kind": "eval", "target": 0.5, "rule": "lucid-flex-50k"}, {"kind": "eval", "target": 50, "rule": "lucid-live-50k"},
    {"kind": "eval", "target": 0, "rule": "lucid-live-50k"}, {"kind": "luck", "target": 1}, {"kind": "net"},
    {"kind": "points", "target": True}])
def test_bad_goal_back_once_then_waits(hb, bad):
    mid = mk()
    lead = Lead(block({"brief": {**GOOD, "goal": bad}}), block({"brief": {**GOOD, "goal": bad}}))
    r = run(briefing.next_step(mid, run_turn=lead, hb=hb))
    assert "error" in r and len(lead.prompts) == 2 and "was refused" in lead.prompts[1]
    assert store.load(mid)["brief"] is None


def test_bad_then_fixed(hb):
    mid = mk()
    lead = Lead(block({"brief": {**GOOD, "goal": {"kind": "eval", "target": 50, "rule": "lucid-live-50k"}}}),
                block({"brief": GOOD}))
    assert run(briefing.next_step(mid, run_turn=lead, hb=hb))["brief"]["goal"]["target"] == 0.5


@pytest.mark.parametrize("key", ["idea", "fixed", "may_change", "fewest_trades_week", "notes", "goal"])
def test_missing_field(key):
    assert briefing.check({k: v for k, v in GOOD.items() if k != key}, [{"id": "lucid-live-50k"}])


def test_drafts_refused_and_never_written(hb):
    assert "drafts" in briefing.check({**GOOD, "drafts": True}, hb.accounts_)
    mid = mk()
    m = store.load(mid)
    m["brief"] = briefing._clean({**GOOD, "drafts": True})
    store.save(m)
    run(briefing.approve(mid, "Yes, start", hb=hb))
    assert "drafts" not in hb.briefs[mid]


def test_approve_writes_exact_keys(hb):
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    m = run(briefing.approve(mid, "Yes, start: go", hb=hb))
    b = hb.briefs[mid]
    assert set(b) == {"approved", "owner_said", "test_months", "goal"} and b["approved"] is True
    assert "Yes, start: go" in b["owner_said"] and "pass the 50k" in b["owner_said"]
    assert b["test_months"] == "team" and b["goal"] == GOOD["goal"]
    assert m["status"] == "ready"


def test_approve_needs_words(hb):
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    with pytest.raises(ValueError):
        run(briefing.approve(mid, "  ", hb=hb))
    assert mid not in hb.briefs


def test_second_mission_queued(hb):
    a = mk()
    m = store.load(a)
    m["status"] = "running"
    store.save(m)
    b = mk()
    run(briefing.next_step(b, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    assert run(briefing.approve(b, "Yes", hb=hb))["status"] == "queued"


def test_page_has_bans(hb):
    p = briefing.page(GOOD, hb.accounts_)
    assert p["bans"] == ["news"] and p["account"]["id"] == "lucid-live-50k"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("goal", [{"kind": "eval", "rule": "lucid-live-50k"}, {"kind": "points"}])
def test_non_finite_numbers(bad, goal):
    acc = [{"id": "lucid-live-50k"}]
    assert briefing.check({**GOOD, "goal": {**goal, "target": bad}}, acc)
    assert briefing.check({**GOOD, "goal": {**goal, "target": 0.5}, "fewest_trades_week": bad}, acc)


@pytest.mark.parametrize("rule", [["lucid-live-50k"], {"a": 1}, 5])
def test_rule_must_be_str_for_eval(hb, rule):
    assert briefing.check({**GOOD, "goal": {"kind": "eval", "target": 0.5, "rule": rule}}, hb.accounts_)
    mid = mk()
    bad = block({"brief": {**GOOD, "goal": {"kind": "eval", "target": 0.5, "rule": rule}}})
    assert "error" in run(briefing.next_step(mid, run_turn=Lead(bad, bad), hb=hb))


def test_rule_dropped_on_non_eval(hb):
    mid = mk()
    b = {**GOOD, "goal": {"kind": "points", "target": 100, "rule": ["x"]}}
    r = run(briefing.next_step(mid, run_turn=Lead(block({"brief": b})), hb=hb))
    assert r["brief"]["goal"] == {"kind": "points", "target": 100}


def approved(hb):
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    run(briefing.approve(mid, "Yes", hb=hb))
    return mid


def test_repeat_approve_refused(hb):
    mid = approved(hb)
    n = len(hb.calls)
    with pytest.raises(ValueError):
        run(briefing.approve(mid, "Yes again", hb=hb))
    assert not [c for c in hb.calls[n:] if c[0] == "write_brief"] and store.load(mid)["status"] == "ready"


@pytest.mark.parametrize("status", ["running", "achieved", "paused"])
def test_approve_only_while_briefing(hb, status):
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    m = store.load(mid)
    m["status"] = status
    store.save(m)
    with pytest.raises(ValueError):
        run(briefing.approve(mid, "Yes", hb=hb))
    assert mid not in hb.briefs and store.load(mid)["status"] == status


def test_ask_and_error_clear_the_brief(hb):
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    assert store.load(mid)["brief"]
    run(briefing.next_step(mid, "change", run_turn=Lead(block({"ask": {"q": "?", "options": ["a", "b"]}})), hb=hb))
    assert store.load(mid)["brief"] is None
    with pytest.raises(ValueError):
        run(briefing.approve(mid, "Yes", hb=hb))
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))

    async def fail(*a, **k):
        return worker.Turn(ok=False, why="plan")
    assert run(briefing.next_step(mid, "again", run_turn=fail, hb=hb)) == {"error": "plan"}
    assert store.load(mid)["brief"] is None


def test_overlapping_next_steps_are_serialised(hb):
    mid = mk()
    q = block({"ask": {"q": "?", "options": ["a", "b"]}})
    seen = []

    async def slow(*a, **k):
        seen.append(1)
        await asyncio.sleep(0.01)
        return worker.Turn(text=q, session_id="s", ok=True)

    async def go():
        return await asyncio.gather(*[briefing.next_step(mid, str(i), run_turn=slow, hb=hb) for i in range(8)])
    run(go())
    assert store.load(mid)["pending"]["brief"]["asked"] == 6  # 8 overlapping answers, never past 6


def test_approve_during_a_turn_is_refused_and_status_kept(hb):
    mid = mk()
    m = store.load(mid)
    m["brief"] = briefing._clean(GOOD)
    store.save(m)

    async def slow(*a, **k):
        with pytest.raises(ValueError):
            await briefing.approve(mid, "Yes", hb=hb)
        return worker.Turn(text=block({"ask": {"q": "?", "options": ["a", "b"]}}), ok=True)
    run(briefing.next_step(mid, run_turn=slow, hb=hb))
    assert store.load(mid)["status"] == "briefing" and mid not in hb.briefs


def test_second_mission_queued_while_the_first_waits_for_homebase(hb):
    a = mk()
    m = store.load(a)
    m["status"] = "waiting_homebase"
    store.save(m)
    b = mk()
    run(briefing.next_step(b, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    assert "waiting_homebase" in store.STATUS
    assert run(briefing.approve(b, "Yes", hb=hb))["status"] == "queued"


def test_next_step_during_a_slow_approve_waits_and_approve_wins(hb):
    import time
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    orig = hb.accounts

    def slow():
        time.sleep(0.2)
        return orig()
    hb.accounts = slow

    async def go():
        a = asyncio.ensure_future(briefing.approve(mid, "Yes", hb=hb))
        await asyncio.sleep(0.05)  # approve is inside its slow hb call, holding the lock
        n = await briefing.next_step(mid, "change it", run_turn=Lead(block({"brief": GOOD})), hb=hb)
        return await a, n
    m, n = run(go())
    assert "not briefing" in n["error"]
    got = store.load(mid)
    assert got["status"] == "ready" and got["brief"] and hb.briefs[mid]["approved"] is True

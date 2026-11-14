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
    briefing.approve(mid, "Yes, start", hb=hb)
    assert "drafts" not in hb.briefs[mid]


def test_approve_writes_exact_keys(hb):
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    m = briefing.approve(mid, "Yes, start: go", hb=hb)
    b = hb.briefs[mid]
    assert set(b) == {"approved", "owner_said", "test_months", "goal"} and b["approved"] is True
    assert "Yes, start: go" in b["owner_said"] and "pass the 50k" in b["owner_said"]
    assert b["test_months"] == "team" and b["goal"] == GOOD["goal"]
    assert m["status"] == "ready"


def test_approve_needs_words(hb):
    mid = mk()
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    with pytest.raises(ValueError):
        briefing.approve(mid, "  ", hb=hb)
    assert mid not in hb.briefs


def test_second_mission_queued(hb):
    a = mk()
    m = store.load(a)
    m["status"] = "running"
    store.save(m)
    b = mk()
    run(briefing.next_step(b, run_turn=Lead(block({"brief": GOOD})), hb=hb))
    assert briefing.approve(b, "Yes", hb=hb)["status"] == "queued"


def test_page_has_bans(hb):
    p = briefing.page(GOOD, hb.accounts_)
    assert p["bans"] == ["news"] and p["account"]["id"] == "lucid-live-50k"

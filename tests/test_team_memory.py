"""Team memory: the tried list, closed branches, the plan's "new" line, exact repeats, ending a stage early, the stall backstop."""
import re

import pytest

from missions import engine, store, system
from tests.test_engine import kit, round_then_stop, run  # noqa: F401
from tests.test_stages import REPORT, prompts, staged


@pytest.fixture(autouse=True)
def _usage(monkeypatch):
    monkeypatch.setattr(system, "usage", lambda: {"seven_day": None})


def lines(kit, who="engine"):
    return [e["text"] for e in store.events(kit.mid) if e["type"] == "chat" and e["who"] == who]


def with_versions(kit, *states):
    eng = kit.eng()
    eng.m["versions"] = [{"version": f"v{i:02d}", "name": f"m{kit.mid}_v{i:02d}", "state": s, "idea": f"idea {i}",
                          "family": "fvg", "why": "no box picked: under 2 trades a week" if s == "dropped" else None}
                         for i, s in enumerate(states, 1)]
    return eng


def test_a_closure_needs_two_dropped_versions(kit):
    eng = with_versions(kit, "dropped", "dropped", "scored")
    eng._closures({"close": [{"what": "first-candle check on top of v23", "reason": "too few trades", "versions": ["v01", "v03"]}]})
    assert eng.m.get("closed") == [] and any("is refused" in t for t in lines(kit))
    eng._closures({"close": [{"what": "first-candle check on top of v23", "reason": "too few trades",
                              "versions": ["v01", f"m{kit.mid}_v02", "v99"]}]})
    assert eng.m["closed"] == [{"what": "first-candle check on top of v23", "reason": "too few trades",
                                "versions": ["v01", "v02"], "stage": 1, "by": "lead"}]
    assert eng.board()["closed"] == eng.m["closed"]


def test_reopen_removes_a_closure(kit):
    eng = with_versions(kit, "dropped", "dropped")
    eng._closures({"close": [{"what": "VWAP filter on v23", "reason": "r", "versions": ["v01", "v02"]}]})
    eng._closures({"reopen": ["vwap filter on V23"]})
    assert eng.m["closed"] == [] and any("Reopened" in t for t in lines(kit))


def test_a_plan_item_without_new_is_refused(kit):
    bad = {"plan": [{"version": "v01", "idea": "x", "family": "fvg", "why": "w"}]}
    kit.turns.over[("lead", "ideas")] = [bad, bad]
    run(round_then_stop(kit).run())
    assert "Your plan was refused" in prompts(kit, "lead", "ideas")[1]
    assert not any("(m%d_v01): x " % kit.mid in b for b in prompts(kit, "builder", "build"))
    assert any('no "new" line' in t for t in lines(kit))


def test_an_exact_repeat_is_refused_and_a_new_one_builds(kit):
    m = store.load(kit.mid)
    m["unbuilt"] = [{"version": "v01", "name": f"m{kit.mid}_v01", "idea": "Fade the gap!", "family": "fvg",
                     "state": "unbuilt", "why": "boom", "stage": 1, "round": 0}]
    store.save(m)
    kit.turns.over[("lead", "ideas")] = [{"plan": [{"version": "v02", "idea": "fade the  gap", "family": "fvg", "why": "w", "new": "n"}]},
                                         {"plan": [{"version": "v02", "idea": "fade the gap at 10:00", "family": "fvg", "why": "w", "new": "later"}]}]
    run(round_then_stop(kit).run())
    assert "is the same as v01" in prompts(kit, "lead", "ideas")[1]
    assert len(store.load(kit.mid)["versions"]) == 1


def test_end_stage_goes_to_the_stage_review(kit):
    eng = staged(kit, [{"stage": {"next": "fresh", "why": "x", "report": REPORT}}], tries=5)
    kit.turns.over[("lead", "verdict")] = [{"to_owner": "a. b.", "next": "n", "end_stage": True}]
    run(eng.run())
    m = store.load(kit.mid)
    assert len(prompts(kit, "lead", "stage")) == 1 and "ended early by you" in prompts(kit, "lead", "stage")[0]
    assert [v["stage"] for v in m["versions"]][:2] == [1, 2] and m["stage_reports"][0]["ended"] == "lead"


def test_a_stall_warns_the_lead_then_the_engine_ends_the_stage(kit):
    def build(t):  # every version builds, and its job fails: nothing ever scores
        names = sorted(set(re.findall(rf"m{kit.mid}_v\d\d", t.log[-1][2].split("Already on the ledger")[0])))
        for nm in names:
            kit.fake.made_[(kit.mid, nm)] = {"wf": True, "job_id": "jx"}
        return {"built": [], "failed": []}
    kit.fake.jobs["jx"] = {"done": True, "ok": False, "said": "boom", "progress": None}
    kit.turns.over[("builder", "build")] = build
    eng = staged(kit, [{"stage": {"next": "fresh", "why": "x", "report": REPORT}}], tries=10)
    assert run(eng.run()) == "limit"
    v = prompts(kit, "lead", "verdict")
    assert "The stage is stalled" not in v[0] and "The stage is stalled: 2 rounds" in v[1]
    st = prompts(kit, "lead", "stage")
    assert len(st) == 1 and "ended by the engine" in st[0]
    m = store.load(kit.mid)
    assert m["stage_reports"][0]["ended"] == "stalled" and [x["stage"] for x in m["versions"]][:4] == [1, 1, 1, 2]
    assert "The stage is stalled: 2 rounds" in v[4] and "The stage is stalled" not in v[3]  # stage 2 counts from 0 again
    assert "The last stage ended early" in " ".join(lines(kit))
    # the tried list reaches the workers, across rounds, with the Judge's reason
    assert "v01 (stage 1) [fvg] plan idea" in prompts(kit, "builder", "ideas")[1] and "dropped: boom" in prompts(kit, "builder", "ideas")[1]  # (the Doubter writes only once something is scored)


def test_a_score_resets_the_stall(kit):
    m = store.load(kit.mid)
    m["pending"]["stall"] = 2
    store.save(m)
    run(round_then_stop(kit).run())
    assert store.load(kit.mid)["pending"]["stall"] == 0 and "The stage is stalled" not in prompts(kit, "lead", "verdict")[0]


def test_the_leads_orders_reach_the_workers(kit):
    eng = kit.eng()
    orig = eng._round_start

    def rs():
        if eng.m["round"] >= 2:
            engine.stop(kit.mid)
        return orig()
    eng._round_start = rs
    run(eng.run())
    p = prompts(kit, "builder", "ideas")  # (the Defender writes only once something is scored)
    assert "The Lead's orders for this round" not in p[0]
    assert "The Lead's orders for this round (they bind what you propose" in p[1] and "try a wider stop" in p[1]


def test_a_fresh_stage_frees_the_old_idea(kit):
    eng = staged(kit, [{"stage": {"next": "fresh", "why": "x", "report": REPORT}}])
    run(eng.run())
    p = prompts(kit, "builder", "ideas")
    assert '"may_change"' in p[0] and '"may_change"' not in p[1] and "free to try a new idea" in p[1]
    assert '"goal"' in p[1] and '"fewest_trades_week"' in p[1]


def test_a_version_that_was_never_built_is_remembered(kit):
    kit.turns.over[("builder", "build")] = [{"built": [], "failed": [{"version": "v01", "why": "no such block"}]}] * 2
    run(round_then_stop(kit).run())
    m = store.load(kit.mid)
    assert m["unbuilt"][0]["why"] == "no such block" and m["versions"] == []
    assert "build failed: no such block" in kit.eng().board()["tried"][0]

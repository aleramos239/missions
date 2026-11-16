"""Stages (tries per stage, the Lead's stage review), target_r, base, the code check step."""
import pytest

from missions import briefing, engine, roles, store, system
from missions import hb as hbmod
from tests.fakes.hb import FakeHB
from tests.test_briefing import GOOD, Lead, block as bblock, mk as bmk
from tests.test_engine import BRIEF, kit, kit3, round_then_stop, run, set_fake, steps  # noqa: F401


@pytest.fixture(autouse=True)
def _usage(monkeypatch):
    monkeypatch.setattr(system, "usage", lambda: {"seven_day": None})


def staged(kit, stage_reply, tries=1, stages=2):
    m = store.load(kit.mid)
    m["limits"] = {"tries": {"n": tries}, "stages": {"n": stages}}
    store.save(m)
    kit.turns.over[("lead", "stage")] = stage_reply
    eng = kit.eng()
    eng.system = system  # the real limit_hit
    return eng


def prompts(kit, role, step):
    return [t[2] for t in kit.turns.log if t[:2] == (role, step)]


def test_a_full_stage_goes_to_the_lead_then_the_next_stage_runs_fresh(kit):
    eng = staged(kit, [{"stage": {"next": "fresh", "why": "nothing worked"}}])
    assert run(eng.run()) == "limit"  # stage 2 used its try: the last stage ends the mission
    m = store.load(kit.mid)
    assert m["stage"] == 2 and len(prompts(kit, "lead", "stage")) == 1
    assert [v["stage"] for v in m["versions"]] == [1, 2]
    p = prompts(kit, "builder", "ideas")
    assert "Start from new ideas" not in p[0] and "Start from new ideas" in p[1]
    assert '"of": 2' in p[1] and '"n": 2' in p[1]
    assert "stage" in steps(kit.mid)


def test_narrow_carries_the_base_idea_and_settings(kit):
    kit.fake.specs["m%d_v01" % kit.mid] = {"stop": 12}
    eng = staged(kit, [{"stage": {"next": "narrow", "base": "v01", "why": "it worked"}}])
    run(eng.run())
    p = prompts(kit, "doubter", "ideas")
    assert "Work only on this idea: variations of it. Base v01: plan idea" in p[1] and 'stop\\": 12' in p[1]
    assert "Work only on this idea" not in p[0]


def test_stop_ends_the_mission(kit):
    eng = staged(kit, [{"stage": {"next": "stop", "why": "enough"}}], stages=3)
    assert run(eng.run()) == "limit"
    assert store.load(kit.mid).get("stage", 1) == 1 and len(store.load(kit.mid)["versions"]) == 1


def test_a_bad_narrow_is_asked_again_then_crashes(kit):
    eng = staged(kit, [{"stage": {"next": "narrow", "base": "v99"}}, {"stage": {"next": "narrow"}}])
    assert run(eng.run()) == "crashed"
    assert "refused" in prompts(kit, "lead", "stage")[1]
    assert store.load(kit.mid)["step"] == "stage"  # a resume re-enters the review


def test_an_old_mission_without_stages_is_one_stage(kit):
    m = store.load(kit.mid)
    m["limits"] = {"tries": {"n": 1}}
    store.save(m)
    eng = kit.eng()
    eng.system = system
    assert run(eng.run()) == "limit" and not prompts(kit, "lead", "stage")
    assert eng.board()["stage"] == {"n": 1, "of": 1, "try": 1, "per": 1, "focus": None}


def test_a_dropped_for_no_trade_version_is_not_a_try(kit):
    eng = kit.eng()
    eng.m["versions"] = [{"version": "v01", "name": "a", "state": "dropped", "why": "no box picked: no box has a trade"},
                         {"version": "v02", "name": "b", "state": "dropped", "why": "the job failed"},
                         {"version": "v03", "name": "c", "state": "scored"}]
    assert eng._tries_used() == 2
    eng.m["stage"] = 2
    assert eng._tries_used() == 0


def test_hours_still_end_the_mission_when_tries_are_full(kit):
    m = store.load(kit.mid)
    m["limits"] = {"tries": {"n": 1}, "stages": {"n": 3}, "hours": {"n": 1}}
    m["run_seconds"] = 3600 * 2
    store.save(m)
    eng = kit.eng()
    eng.system = system
    assert run(eng.run()) == "limit" and not prompts(kit, "lead", "stage")


def test_a_new_mission_starts_narrowed_on_another_missions_version(kit3):
    old = store.load(1)
    old["versions"] = [{"version": "v23", "name": "m1_v23", "idea": "fade the gap at 9:35"}]
    store.save(old)
    kit3.fake.specs["m1_v23"] = {"target": 2}
    m = store.load(kit3.mid)
    m["brief"] = {**BRIEF, "base": {"mission": 1, "version": "v23"}}
    m["limits"] = {"tries": {"n": 1}}
    store.save(m)
    eng = kit3.eng()
    kit3.turns.over[("lead", "ideas")] = None
    eng.system = system
    run(eng.run())
    p = prompts(kit3, "builder", "ideas")[0]
    assert "Base v23: fade the gap at 9:35" in p and 'target\\": 2' in p


def test_the_builder_checks_the_code_after_the_table(kit):
    run(round_then_stop(kit).run())
    assert [t[:2] for t in kit.turns.log if t[1] in ("build", "check", "argue")][:3] == \
        [("builder", "build"), ("builder", "check"), ("doubter", "argue")]
    assert "m%d_v01" % kit.mid in prompts(kit, "builder", "check")[0]
    assert "blueprint_code_check" in roles._read("builder") and "Do NOT call `blueprint_code_check`" in roles._read("builder")


def test_no_check_turn_when_no_table_is_done(kit):
    kit.fake.jobs["j1"] = {"done": True, "ok": False, "said": "boom", "progress": None}
    eng = kit.eng()
    eng.system = system
    m = store.load(kit.mid)
    m["limits"] = {"tries": {"n": 1}}
    store.save(m)
    run(eng.run())
    assert not prompts(kit, "builder", "check")


def test_contracts():
    assert '"next": "narrow" | "fresh" | "stop"' in roles._C[("lead", "stage")]
    assert "target_r" in roles._C[("lead", "brief")] and "base" in roles._C[("lead", "brief")]
    assert '"checked"' in roles._C[("builder", "check")]
    with pytest.raises(ValueError):
        roles.prompt("doubter", "stage", brief=None, board=None, chat="", ask=None)


def test_limits_accept_stages():
    store.check_limits({"tries": {"n": 20}, "stages": {"n": 3}})
    for bad in ({"stages": {"n": 0}}, {"stages": {"n": 1.5}}, {"stages": 3}):
        with pytest.raises(ValueError):
            store.check_limits(bad)


def test_brief_target_r_and_base(monkeypatch, tmp_path):
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "v"))
    acc = [{"id": "lucid-live-50k"}]
    assert briefing.check({**GOOD, "target_r": 2}, acc) is None
    assert briefing.check({**GOOD, "target_r": 3}, acc)
    assert briefing.check({**GOOD, "target_r": True}, acc)
    mid = bmk()
    m = store.load(mid)
    m["versions"] = [{"version": "v23"}]
    store.save(m)
    ok = {**GOOD, "target_r": 2, "base": {"mission": mid, "version": "v23"}}
    assert briefing.check(ok, acc) is None
    assert briefing.check({**GOOD, "base": {"mission": mid, "version": "v99"}}, acc)
    assert briefing.check({**GOOD, "base": {"mission": 99, "version": "v23"}}, acc)
    assert briefing.check({**GOOD, "base": "v23"}, acc)
    assert briefing._clean(ok)["base"] == ok["base"] and briefing._clean(ok)["target_r"] == 2


def test_approve_carries_target_r_but_not_base(monkeypatch, tmp_path):
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "v"))
    f = FakeHB()
    f.accounts_ = [{"id": "lucid-live-50k", "bans": []}]
    mid = bmk()
    run(briefing.next_step(mid, run_turn=Lead(bblock({"brief": {**GOOD, "target_r": 2}})), hb=f))
    run(briefing.approve(mid, "Yes", hb=f))
    assert f.briefs[mid]["target_r"] == 2 and "base" not in f.briefs[mid]
    assert "target_r" in hbmod.BRIEF_KEYS

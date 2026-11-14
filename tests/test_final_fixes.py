"""The final-review fixes: start from ready, off-loop hb calls, worker-proof stops, sliced waits, limits, pids."""
import asyncio
import os
import threading

import pytest

from missions import briefing, engine, hb, store, worker
from tests.test_engine import BRIEF, TEAM, kit, run, stopper  # noqa: F401
from tests.test_briefing import GOOD, Lead, block
from tests.fakes.hb import FakeHB


def test_approved_mission_starts_via_the_runner():
    f = FakeHB()
    f.accounts_ = [{"id": "lucid-live-50k", "name": "L", "size": 50000, "drawdown": 2000, "risk": 500, "bans": []}]
    mid = store.new_mission("pass the 50k", TEAM, {}, "team")["id"]
    run(briefing.next_step(mid, run_turn=Lead(block({"brief": GOOD})), hb=f))
    assert run(briefing.approve(mid, "Yes", hb=f))["status"] == "ready"
    seen = []

    class Eng(engine.Engine):
        async def run(self):
            seen.append(store.load(self.mid)["status"])
            engine._set_status(self.mid, "stopped")
    orig, engine.Engine = engine.Engine, Eng
    try:
        run(engine.runner(until_idle=True))
    finally:
        engine.Engine = orig
    assert seen == ["running"]


def test_hb_calls_run_off_the_event_loop(kit):
    main = threading.get_ident()
    seen = []
    real = kit.fake.family_of
    kit.fake.family_of = lambda n: seen.append(threading.get_ident()) or real(n)
    run(stopper(kit.eng(), kit).run())
    assert seen and all(t != main for t in seen)


def test_an_empty_lead_plan_is_a_failed_round_not_an_empty_one(kit):
    kit.turns.over[("lead", "ideas")] = [{"plan": []}, {"plan": []}, {"plan": [{"junk": 1}]}]
    assert run(stopper(kit.eng(), kit).run()) == "stopped"
    m = store.load(kit.mid)
    assert m["empty_rounds"] == 0 and m["status"] == "stopped"


def test_six_failed_rounds_crash_with_an_alert(kit):
    kit.turns.over[("lead", "ideas")] = [{"plan": []}] * 40
    alerts = []

    class Sys(engine._NoSystem):
        def alert(self, mid, kind):
            alerts.append(kind)
    m = store.load(kit.mid)
    m["limits"] = {"until_goal": True}
    store.save(m)
    assert run(kit.eng(system=Sys()).run()) == "crashed"
    assert store.load(kit.mid)["status"] == "crashed" and alerts == ["crashed"]
    assert any("6 rounds in a row" in e["text"] for e in store.events(kit.mid))


def test_pause_during_a_table_wait_is_honoured(kit):
    kit.fake.jobs["j1"] = {"done": False, "ok": False, "said": "", "progress": None}
    orig = kit.clock.sleep

    async def sleep(s):
        engine.pause(kit.mid)
        await orig(s)
    eng = kit.eng()
    eng.sleep = sleep
    assert run(eng.run()) == "paused"
    assert store.load(kit.mid)["step"] == "wait"


def test_stop_during_a_plan_reserve_wait_is_honoured(kit):
    class Sys(engine._NoSystem):
        async def wait_for_plan(self, resets_at, *, sleep):
            await sleep(5 * 3600)
    kit.turns.over[("builder", "ideas")] = [worker.Turn(why="plan", resets_at=555)]
    orig = kit.clock.sleep

    async def sleep(s):
        engine.stop(kit.mid)
        await orig(s)
    eng = kit.eng(system=Sys())
    eng.sleep = sleep
    assert run(eng.run()) == "stopped"
    assert sum(kit.clock.slept) < 100


def test_a_wf_row_without_a_job_row_is_waited_for_then_adopted(kit):
    orig = kit.fake.made
    n = {"i": 0}

    def made(mid, name):
        r = orig(mid, name)
        n["i"] += 1
        return r if n["i"] < 4 else {**r, "job_id": "j1"}
    kit.fake.made = made
    kit.turns.over[("builder", "build")] = lambda t: (kit.fake.made_.update({(kit.mid, f"m{kit.mid}_v01"):
                                                       {"wf": True, "job_id": None}}) or {"built": []})
    run(stopper(kit.eng(), kit).run())
    v = store.load(kit.mid)["versions"][0]
    assert v["job_id"] == "j1" and n["i"] >= 4


def test_approve_read_queues_when_another_mission_runs(kit):
    other = store.new_mission("other", TEAM, {}, "team")
    other["status"] = "running"
    store.save(other)
    m = store.load(kit.mid)
    m.update(status="waiting_owner", pending={"read_for": "x"})
    store.save(m)
    engine.approve_read(kit.mid, "yes")
    assert store.load(kit.mid)["status"] == "queued"


@pytest.mark.parametrize("lim,ok", [({}, True), ({"tries": {"n": 5}, "usage": {"pct": 12.5}, "until_goal": False}, True),
                                    ({"tries": {"n": 0}}, False), ({"tries": 5}, False), ({"hours": {"pct": 1}}, False),
                                    ({"usage": {"n": 3}}, False), ({"tries": {"n": True}}, False),
                                    ({"until_goal": "yes"}, False), ({"bogus": 1}, False), ([], False)])
def test_limits_validation(lim, ok):
    if ok:
        store.new_mission("g", TEAM, lim, "team")
    else:
        with pytest.raises(ValueError):
            store.new_mission("g", TEAM, lim, "team")


def test_api_rejects_bad_limits_and_hunt_without_pause():
    from tests.test_api import call
    body = {"sentence": "go", "team": TEAM, "limits": {"tries": {"n": -1}}, "test_months": "team"}
    assert call("POST", "/api/missions", json=body).status_code == 400
    mid = store.new_mission("go", TEAM, {}, "team")["id"]
    assert call("PATCH", f"/api/missions/{mid}", json={"limits": {"hours": {"n": "x"}}}).status_code == 400
    assert call("POST", "/api/hunt", json={}).status_code == 400


def test_stale_read_pid_from_another_start_is_stopped():
    store.new_mission("s", TEAM, {}, "team")
    (store.mdir(1) / "read_m1_v01.pid").write_text(f"{os.getpid()} Thu Jan  1 00:00:00 1970")
    assert hb.read_result(1, "m1_v01") == {"refused": hb.STOPPED}
    (store.mdir(1) / "read_m1_v01.pid").write_text(f"{os.getpid()} {hb._lstart(os.getpid())}")
    assert hb.read_result(1, "m1_v01") is None  # same process: still running


def test_kill_all_kills_running_turn_groups(monkeypatch):
    killed = []
    monkeypatch.setattr(worker.os, "killpg", lambda pid, sig: killed.append(pid))
    worker._live.update({11, 12})
    worker.kill_all()
    assert sorted(killed) == [11, 12] and not worker._live

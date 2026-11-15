import asyncio
import json
import re

import pytest

from missions import engine, store, worker
from tests.fakes.hb import FakeHB

TEAM = {r: {"model": "haiku", "effort": "low"} for r in store.ROLES}
BRIEF = {"goal": {"kind": "points", "target": 3.0}, "idea": "9:30 follow", "fixed": ["NQ"], "may_change": ["stop"],
         "fewest_trades_week": 2.0, "notes": ""}
LINES = [{"line": n, "ok": True, "said": "ok"} for n in ("boxes", "trades", "luck", "years", "worse fills")]
CH = [{"charge": c, "held": True, "why": "fine"} for c in ("One year carries it", "Worse fills kill it", "It looks ahead",
                                                          "One side carries it", "It is a dead family again")]


def block(d):
    return "Words.\n```json\n" + json.dumps(d) + "\n```"


def run(c):
    return asyncio.run(c)


class Clock:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def __call__(self):
        return self.t

    async def sleep(self, s):
        self.slept.append(s)
        self.t += s


class Kill(BaseException):
    """The app dies here: not an Exception, so run() does not turn it into a crash."""


class Turns:
    """A scripted run_turn: answers by (role, step); self.log holds (role, step, prompt) of every turn."""

    def __init__(self, fake, mid):
        self.fake, self.mid, self.log, self.over = fake, mid, [], {}
        self.n = 0

    @staticmethod
    def step_of(prompt):
        for k in ("owner wrote", "Step: ideas", "Step: build", "Step: argue", "Step: verdict", "Step: read"):
            if k in prompt:
                return {"owner wrote": "owner"}.get(k, k[6:])

    def default(self, role, step, prompt):
        n = self.n
        if step == "ideas" and role == "lead":
            return {"plan": [{"version": "v01", "idea": "plan idea", "family": "fvg", "why": "w"}]}
        if step == "ideas":
            return {"ideas": [{"idea": f"idea of {role} {n}", "family": "fvg", "why": "w"}]}
        if step == "build":
            names = sorted(set(re.findall(rf"m{self.mid}_v\d\d", prompt.split("Already on the ledger")[0])))
            for nm in names:
                self.fake.made_[(self.mid, nm)] = {"wf": True, "job_id": "j1"}
                if (nm, "12") not in self.fake.gates:
                    set_fake(self.fake, self.mid, n=nm)
            return {"built": [{"version": nm[-3:], "name": nm, "job_id": "j1"} for nm in names], "failed": []}
        if step == "argue" and role == "doubter":
            return {"claims": [{"version": "v01", "charge": "One year carries it", "say": "2023 carries it"}]}
        if step == "argue":
            return {"answers": [], "fixes": [{"idea": "fix", "family": "fvg", "why": "w"}]}
        if step == "verdict":
            return {"to_owner": "Two plain sentences.", "next": "try a wider stop"}
        if step == "read":
            return {"next": "go_on", "why": "keep going"}
        if step == "owner":
            return {"reply": "hello", "plan_change": "use 15m"}

    async def __call__(self, mid, role, prompt, *, model, effort, session_id=None, **kw):
        step = self.step_of(prompt)
        self.n += 1
        self.log.append((role, step, prompt))
        h = self.over.get((role, step))
        if isinstance(h, list):
            h = h.pop(0) if h else None
        if callable(h):
            h = h(self)
        if isinstance(h, worker.Turn):
            return h
        out = h if h is not None else self.default(role, step, prompt)
        return worker.Turn(text=block(out) if isinstance(out, dict) else out, session_id=f"s{self.n}", ok=True)


def set_fake(fake, mid, *, clear=True, value=4.0, n=None):
    n = n or f"m{mid}_v01"
    fake.reach["fvg"] = {"family": "fvg", "reachable": True}
    fake.jobs["j1"] = {"done": True, "ok": True, "said": "", "progress": None}
    fake.tables[n] = {"pick": "12", "rows": [{"box": "12", "value": 20, "cell": 14}]}
    fake.gates[(n, "12")] = {"name": n, "box": "12", "clear": clear, "lines": LINES, "charges": CH,
                             "goal": {"kind": "points", "target": 3.0, "value": value, "met": clear}, "tries": 1}
    fake.reads[n] = {"held": False, "line": "worse fills", "close": "far"}


def make_kit(monkeypatch, tmp_path, pre=0):
    """A mission with a brief, running; `pre` earlier missions make its id higher than 1."""
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "vault"))
    engine._active.clear()
    for _ in range(pre):
        store.new_mission("earlier", TEAM, {}, "team")
    m = store.new_mission("reach 3 points", TEAM, {}, "team")
    m["brief"], m["status"] = BRIEF, "running"
    store.save(m)
    fake, clock = FakeHB(), Clock()
    set_fake(fake, m["id"])
    turns = Turns(fake, m["id"])

    def mk(mid=None, **kw):
        kw.setdefault("backoff", (1, 4))
        return engine.Engine(mid or m["id"], hb=fake, run_turn=turns, clock=clock, sleep=clock.sleep, **kw)
    return type("Kit", (), {"mid": m["id"], "fake": fake, "turns": turns, "clock": clock, "eng": mk, "mk": mk})


@pytest.fixture
def kit(monkeypatch, tmp_path):
    return make_kit(monkeypatch, tmp_path)


@pytest.fixture
def kit3(monkeypatch, tmp_path):
    return make_kit(monkeypatch, tmp_path, pre=2)  # mission id 3


def steps(mid):
    return [e["text"] for e in store.events(mid) if e["type"] == "step"]


def round_then_stop(kit, **kw):
    """One whole round, then stop at the next round start."""
    eng = kit.eng()
    orig = eng._round_start

    def rs():
        if eng.m["round"] >= 1:
            engine.stop(kit.mid)
        orig()
    eng._round_start = rs
    return eng


def test_a_round_runs_the_steps_in_order_and_no_step_is_skipped(kit):
    assert run(round_then_stop(kit).run()) == "stopped"
    assert steps(kit.mid) == list(engine.STEPS)[:3] + ["argue", "verdict", "read"]
    assert [t[:2] for t in kit.turns.log if t[1] == "argue"] == [("doubter", "argue"), ("defender", "argue"),
                                                                 ("doubter", "argue")]


def test_ideas_are_written_alone(kit):
    run(round_then_stop(kit).run())
    ideas = [t for t in kit.turns.log if t[1] == "ideas" and t[0] != "lead"]
    assert len(ideas) == 3
    for role, _, p in ideas:
        for other in {"builder", "doubter", "defender"} - {role}:
            assert f"idea of {other}" not in p
    lead = next(t for t in kit.turns.log if t[:2] == ("lead", "ideas"))
    assert all(f"idea of {r}" in lead[2] for r in ("builder", "doubter", "defender"))


def test_an_unreachable_family_is_dropped_before_it_is_built(kit):
    kit.fake.reach["fvg"] = {"family": "fvg", "reachable": False}
    kit.turns.over[("lead", "ideas")] = lambda t: {"plan": [{"version": "v01", "idea": "i", "family": "fvg", "why": "w"}]}
    run(round_then_stop(kit).run())
    assert not any(t[1] == "build" for t in kit.turns.log)
    assert any(e["who"] == "judge" and "luck bar needed is above anything fvg has shown" in e["text"]
               for e in store.events(kit.mid))


def test_two_empty_rounds_stop_as_out_of_reach_even_with_run_until_goal(kit):
    m = store.load(kit.mid)
    m["limits"] = {"until_goal": True}
    store.save(m)
    kit.fake.reach["fvg"] = {"family": "fvg", "reachable": False}
    assert run(kit.eng().run()) == "out_of_reach"
    assert store.load(kit.mid)["round"] == 2 and store.load(kit.mid)["status"] == "out_of_reach"


def test_a_version_the_ledger_does_not_hold_is_not_built(kit):
    kit.turns.over[("builder", "build")] = lambda t: {"built": [{"version": "v01", "name": f"m{kit.mid}_v01", "job_id": "j9"}]}
    run(round_then_stop(kit).run())
    builds = [t for t in kit.turns.log if t[1] == "build"]
    assert len(builds) == 2 and "These are not on the ledger: m1_v01" in builds[1][2]
    assert store.load(kit.mid)["versions"] == []
    assert not any(t[1] == "argue" and t[0] == "doubter" for t in kit.turns.log)


def test_no_worker_runs_while_jobs_run(kit):
    kit.fake.jobs["j1"] = {"done": False, "ok": False, "said": "", "progress": [1, 4]}
    states = iter([{"done": False, "ok": False, "said": "", "progress": [2, 4]},
                   {"done": True, "ok": True, "said": "", "progress": None}])
    orig = kit.fake.job

    def job(j):
        r = orig(j)
        if not r["done"]:
            kit.fake.jobs["j1"] = next(states)
        return r
    kit.fake.job = job
    run(round_then_stop(kit).run())
    log = [t[:2] for t in kit.turns.log]
    i = max(k for k, t in enumerate(log) if t[1] == "build")
    assert log[i + 1][1] == "argue"
    assert len([c for c in kit.fake.calls if c[0] == "job"]) >= 3
    assert any(e["type"] == "progress" for e in store.events(kit.mid))


def test_a_job_that_fails_drops_the_version(kit):
    kit.fake.jobs["j1"] = {"done": True, "ok": False, "said": "boom", "progress": None}
    run(round_then_stop(kit).run())
    v = store.load(kit.mid)["versions"][0]
    assert v["state"] == "dropped" and "boom" in v["why"]


def test_a_claim_outside_the_five_charges_is_dropped(kit):
    kit.turns.over[("doubter", "argue")] = {"claims": [{"version": "v01", "charge": "It smells", "say": "x"},
                                                       {"version": "v09", "charge": "It looks ahead", "say": "y"}]}
    run(round_then_stop(kit).run())
    ev = store.events(kit.mid)
    assert sum(e["who"] == "lead" and "not on the list" in e["text"] for e in ev) >= 2
    assert not any(e["who"] == "doubter" and e["for_workers"] for e in ev)


def test_a_claim_never_changes_the_gate(kit):
    before = repr(kit.fake.gates)
    run(round_then_stop(kit).run())
    v = store.load(kit.mid)["versions"][0]
    assert v["gate"]["clear"] is True and v["state"] in ("cleared", "frozen")
    assert any(e["who"] == "doubter" and "2023 carries it" in e["text"] for e in store.events(kit.mid))
    assert repr(kit.fake.gates) == before
    assert store.load(kit.mid)["pending"]["fixes"]


def test_only_a_cleared_version_is_read_and_the_best_goes_first(kit):
    m = store.load(kit.mid)
    for i, (clear, val) in enumerate([(True, 2.0), (True, 5.0), (False, 9.0)], 1):
        g = {"clear": clear, "goal": {"value": val}, "lines": [], "charges": []}
        m["versions"].append({"name": f"m{kit.mid}_x{i}", "version": f"v1{i}", "round": 0, "family": "fvg",
                              "job_id": None, "state": "cleared" if clear else "scored", "box": str(i), "gate": g})
    m["step"] = "read"
    store.save(m)
    for i in (1, 2, 3):
        kit.fake.reads[f"m{kit.mid}_x{i}"] = {"held": False, "line": "years", "close": "close"}
    run(round_then_stop(kit).run())
    assert kit.fake.started[0][1] == f"m{kit.mid}_x2"  # one read a round, the best first
    assert all(s[1] != f"m{kit.mid}_x3" for s in kit.fake.started)


def test_held_ends_the_mission_as_achieved(kit):
    kit.fake.reads[f"m{kit.mid}_v01"] = {"held": True, "line": "", "close": "close"}
    assert run(kit.eng().run()) == "achieved"
    m = store.load(kit.mid)
    assert m["status"] == "achieved" and m["result"]["version"] == "v01" and m["reads"] == 1


def test_a_broke_read_freezes_the_version_and_the_next_round_starts(kit):
    assert run(round_then_stop(kit).run()) == "stopped"
    m = store.load(kit.mid)
    assert m["versions"][0]["state"] == "frozen" and m["reads"] == 1
    assert m["versions"][0]["heard"] == {"held": False, "line": "worse fills", "close": "far"}
    assert any(e["who"] == "judge" and "worse fills" in e["text"] for e in store.events(kit.mid))


def test_a_refused_read_spends_the_version(kit):
    kit.fake.reads[f"m{kit.mid}_v01"] = {"refused": "that box was read"}
    run(round_then_stop(kit).run())
    assert store.load(kit.mid)["versions"][0]["state"] == "spent"
    assert store.load(kit.mid)["reads"] == 0


def test_ask_me_first_waits_and_reads_only_after_his_words(kit):
    m = store.load(kit.mid)
    m["test_months"] = "ask"
    store.save(m)
    assert run(kit.eng().run()) == "waiting_owner"
    assert kit.fake.started == []
    engine.approve_read(kit.mid, "yes, read it")
    assert store.load(kit.mid)["status"] == "running"
    run(round_then_stop(kit).run())
    assert kit.fake.started == [(kit.mid, f"m{kit.mid}_v01", "12", "yes, read it")]


def test_plan_used_up_waits_and_reruns_the_same_turn(kit):
    class Sys(engine._NoSystem):
        waited = []

        async def wait_for_plan(self, resets_at, *, sleep):
            self.waited.append(resets_at)
    kit.turns.over[("builder", "ideas")] = [worker.Turn(why="plan", resets_at=555)]
    eng = kit.eng(system=Sys())
    orig = eng._round_start

    def rs():
        if eng.m["round"] >= 1:
            engine.stop(kit.mid)
        orig()
    eng._round_start = rs
    run(eng.run())
    assert Sys.waited == [555]
    assert len([t for t in kit.turns.log if t[:2] == ("builder", "ideas")]) == 2
    assert any(e["text"] == "waiting_plan" for e in store.events(kit.mid) if e["type"] == "status")


def test_a_reply_with_no_json_gets_one_retry_then_the_step_goes_on(kit):
    kit.turns.over[("doubter", "ideas")] = ["no block here", "still none"]
    run(round_then_stop(kit).run())
    d = [t for t in kit.turns.log if t[:2] == ("doubter", "ideas")]
    assert len(d) == 2 and "end your message with the json block" in d[1][2].lower()
    assert any("The doubter did not answer" in e["text"] for e in store.events(kit.mid))
    assert any(t[1] == "build" for t in kit.turns.log)


def test_a_crashed_turn_is_retried_in_a_fresh_session(kit):
    kit.turns.over[("builder", "ideas")] = [worker.Turn(why="timeout")]
    run(round_then_stop(kit).run())
    assert len([t for t in kit.turns.log if t[:2] == ("builder", "ideas")]) == 2


def test_stop_wins_over_everything_at_the_next_step(kit):
    def h(t):
        engine.stop(kit.mid)
    kit.turns.over[("lead", "ideas")] = lambda t: (engine.stop(kit.mid), None)[1]
    assert run(kit.eng().run()) == "stopped"
    assert not any(t[1] == "build" for t in kit.turns.log)
    assert store.load(kit.mid)["status"] == "stopped"


def test_pause_is_seen_at_round_start_and_resume_goes_on(kit):
    engine.pause(kit.mid)
    assert run(kit.eng().run()) == "paused" and store.load(kit.mid)["round"] == 0
    engine.resume(kit.mid)
    assert store.load(kit.mid)["status"] == "running"


def test_a_text_to_the_lead_during_a_wait_gets_an_answer_at_once(kit):
    kit.fake.jobs["j1"] = {"done": False, "ok": False, "said": "", "progress": None}
    orig = kit.clock.sleep
    n = {"i": 0}

    async def sleep(s):
        n["i"] += 1
        if n["i"] == 1:
            engine.owner_says(kit.mid, "lead", "think about 15m")
        if n["i"] == 2:
            kit.fake.jobs["j1"] = {"done": True, "ok": True, "said": "", "progress": None}
        await orig(s)
    eng = kit.mk()
    eng.sleep = sleep
    orig_rs = eng._round_start

    def rs():
        if eng.m["round"] >= 1:
            engine.stop(kit.mid)
        orig_rs()
    eng._round_start = rs
    run(eng.run())
    own = [t for t in kit.turns.log if t[1] == "owner"]
    assert len(own) == 1 and own[0][0] == "lead" and own[0][2].count("think about 15m") == 1
    assert any(e["who"] == "lead" and e["text"] == "hello" for e in store.events(kit.mid))
    assert store.load(kit.mid)["pending"].get("plan_change") in ("use 15m", None)


def test_workers_see_new_chat_lines_since_their_last_turn(kit):
    run(round_then_stop(kit).run())
    d = [t for t in kit.turns.log if t[:2] == ("doubter", "argue")]
    assert "judge:" in d[0][2] and "m1_v01" in d[0][2]
    assert "defender:" not in d[0][2] and "doubter: v01" in d[1][2] or "doubter:" not in d[1][2]


def test_the_board_holds_goal_versions_and_best(kit):
    run(round_then_stop(kit).run())
    b = kit.eng().board()
    assert b["goal"]["kind"] == "points" and b["round"] == 1 and b["best"] == "v01"
    v = b["versions"][0]
    assert v["box"] == "20 · #14" and v["goal_value"] == 4.0 and v["lines_failed"] == []


def test_one_mission_runs_at_a_time(kit):
    m2 = store.new_mission("second", TEAM, {}, "team")
    m2["brief"], m2["status"] = BRIEF, "queued"
    store.save(m2)
    set_fake(kit.fake, m2["id"])
    kit.fake.reads[f"m{kit.mid}_v01"] = {"held": True, "line": "", "close": "close"}
    kit.fake.reads[f"m{m2['id']}_v01"] = {"held": True, "line": "", "close": "close"}
    kit.turns.mid = None
    seen = []
    orig = kit.turns.__call__

    async def t(mid, role, prompt, **kw):
        seen.append((mid, store.load(m2["id"])["status"]))
        for x in (kit.mid, m2["id"]):
            kit.fake.made_[(x, f"m{x}_v01")] = {"wf": True, "job_id": "j1"}
        return await orig(mid, role, prompt, **kw)
    run(engine.runner(until_idle=True, hb=kit.fake, run_turn=t, clock=kit.clock, sleep=kit.clock.sleep))
    assert store.load(kit.mid)["status"] == "achieved" and store.load(m2["id"])["status"] == "achieved"
    assert all(s == "queued" for mid, s in seen if mid == kit.mid)


# ---- fix round 1

def stopper(eng, kit, n=1):
    orig = eng._round_start

    def rs():
        if eng.m["round"] >= n:
            engine.stop(kit.mid)
        orig()
    eng._round_start = rs
    return eng


class LimitSys(engine._NoSystem):
    def limit_hit(self, m, tries_mission):
        return "tries"


def test_a_lead_reply_with_stop_does_not_end_the_mission(kit):
    kit.turns.over[("lead", "read")] = {"why": "stop now", "next": "stop"}
    eng = kit.eng(system=LimitSys())
    calls = {"n": 0}
    ok = engine._NoSystem.limit_hit

    def limit(m, t):  # round 1 runs whole, then a limit ends it: the Lead's "stop" did not
        calls["n"] += 1
        return "tries" if calls["n"] > 1 else None
    eng.system.limit_hit = limit
    assert run(eng.run()) == "limit"
    m = store.load(kit.mid)
    assert m["round"] == 1 and m["reads"] == 1 and m["pending"]["next"] == "stop now"


def test_until_goal_skips_the_limits_in_the_engine(kit):
    m = store.load(kit.mid)
    m["limits"] = {"until_goal": True}
    store.save(m)
    kit.fake.reach["fvg"] = {"family": "fvg", "reachable": False}
    assert run(kit.eng(system=LimitSys()).run()) == "out_of_reach"


def test_two_failed_lead_turns_are_not_empty_rounds(kit):
    bad = worker.Turn(why="timeout")
    kit.turns.over[("lead", "ideas")] = [bad] * 6  # three rounds of a failed turn and its retry
    eng = stopper(kit.eng(), kit)
    assert run(eng.run()) == "stopped"
    m = store.load(kit.mid)
    assert m["empty_rounds"] == 0 and m["round"] == 1 and len(m["versions"]) == 1
    assert any("could not be made or checked" in e["text"] for e in store.events(kit.mid))


def test_a_refused_reach_retries_the_round_without_an_empty_round(kit):
    kit.fake.reach["fvg"] = kit.fake.Refused("no such family 7")
    n = {"i": 0}

    def lead(t):
        n["i"] += 1
        if n["i"] == 2:
            kit.fake.reach["fvg"] = {"family": "fvg", "reachable": True}
    kit.turns.over[("lead", "ideas")] = lead
    assert run(stopper(kit.eng(), kit).run()) == "stopped"
    m = store.load(kit.mid)
    assert m["empty_rounds"] == 0 and len(m["versions"]) == 1 and n["i"] == 2


def down_for(fake, name, n):
    orig, left = getattr(fake, name), {"n": n}

    def f(*a, **k):
        if left["n"] > 0:
            left["n"] -= 1
            raise fake.Down("no door")
        return orig(*a, **k)
    setattr(fake, name, f)
    return left


@pytest.mark.parametrize("name", ["reach", "made", "job", "table", "gate", "read_result", "start_read", "tries"])
def test_a_homebase_outage_waits_and_the_same_step_goes_on(kit, name):
    if name == "tries":
        kit.fake.tries_["fvg"] = {"mission": 1, "family_on_file": 0, "total": 1, "needed_t": 2.0}
    left = down_for(kit.fake, name, 3)
    assert run(stopper(kit.eng(), kit).run()) == "stopped"
    assert left["n"] == 0
    m = store.load(kit.mid)
    assert m["versions"][0]["state"] == "frozen" and m["reads"] == 1
    st = [e["text"] for e in store.events(kit.mid) if e["type"] == "status"]
    assert "waiting_homebase" in st and st.index("waiting_homebase") < len(st) - 1
    assert kit.clock.slept.count(1) + kit.clock.slept.count(2) + kit.clock.slept.count(4) >= 3  # capped backoff 1, 2, 4


def test_the_outage_backoff_is_capped(kit):
    down_for(kit.fake, "reach", 6)
    run(stopper(kit.eng(), kit).run())
    waits = [s for s in kit.clock.slept if s in (1, 2, 4)][:6]
    assert waits == [1, 2, 4, 4, 4, 4]


def test_pause_and_stop_are_honoured_while_homebase_is_down(kit):
    down_for(kit.fake, "reach", 100)
    orig = kit.clock.sleep

    async def sleep(s):
        engine.pause(kit.mid)
        await orig(s)
    eng = kit.eng()
    eng.sleep = sleep
    assert run(eng.run()) == "paused"
    assert store.load(kit.mid)["step"] == "ideas"
    engine.resume(kit.mid)
    engine._active.clear()
    left = {"n": 0}
    kit.fake.reach = lambda mid, fam: (_ for _ in ()).throw(kit.fake.Down("x"))
    eng2 = kit.eng()

    async def sleep2(s):
        engine.stop(kit.mid)
        await orig(s)
    eng2.sleep = sleep2
    assert run(eng2.run()) == "stopped"


def test_a_text_a_normal_turn_already_showed_gets_no_second_answer(kit):
    engine.owner_says(kit.mid, "lead", "think about 15m")
    run(stopper(kit.eng(), kit).run())
    assert not [t for t in kit.turns.log if t[1] == "owner"]
    lead = next(t for t in kit.turns.log if t[:2] == ("lead", "ideas"))
    assert "think about 15m" in lead[2]


def test_one_answer_task_a_mission_and_extra_calls_are_dropped(kit, monkeypatch):
    m = store.load(kit.mid)
    m["status"] = "paused"
    store.save(m)
    calls = []

    async def fake_answer(self):
        calls.append(self.mid)
        await asyncio.sleep(0.01)
    monkeypatch.setattr(engine.Engine, "answer", fake_answer)

    async def main():
        engine.owner_says(kit.mid, "lead", "one")
        engine.owner_says(kit.mid, "lead", "two")
        task = engine._answers[kit.mid]
        await task
        engine.owner_says(kit.mid, "lead", "three")  # the first is done: a new one may start
        await engine._answers[kit.mid]
    run(main())
    assert calls == [kit.mid, kit.mid]


def test_an_answer_turns_plan_wait_leaves_a_paused_mission_paused(kit):
    m = store.load(kit.mid)
    m["status"] = "paused"
    store.save(m)
    engine.owner_says(kit.mid, "lead", "hi")
    kit.turns.over[("lead", "owner")] = [worker.Turn(why="plan", resets_at=5)]
    run(kit.eng().answer())
    assert store.load(kit.mid)["status"] == "paused"
    assert any(t[:2] == ("lead", "owner") for t in kit.turns.log) and len([t for t in kit.turns.log if t[1] == "owner"]) == 2


def test_an_approval_during_an_answer_turn_survives(kit):
    m = store.load(kit.mid)
    m["status"], m["pending"]["read_for"] = "waiting_owner", "v01"
    store.save(m)
    engine.owner_says(kit.mid, "lead", "think about 15m")

    def approve(_):
        engine.approve_read(kit.mid, "yes, read it")
        return None  # the default owner reply
    kit.turns.over[("lead", "owner")] = approve
    run(kit.mk().answer())
    m = store.load(kit.mid)
    assert m["status"] == "running" and m["pending"]["read_ok"] == "yes, read it"
    assert m["pending"]["answered"] and m["pending"]["plan_change"] == "use 15m"


def test_a_failed_round_keeps_the_fixes_for_the_retry(kit):
    m = store.load(kit.mid)
    m["pending"]["fixes"] = [{"idea": "fix", "family": "fvg", "why": "w"}]
    m["pending"]["plan_change"] = "use 15m"
    store.save(m)
    kit.turns.over[("lead", "ideas")] = [worker.Turn(why="crash"), worker.Turn(why="crash")]
    eng = kit.mk()
    run(eng._ideas())
    p = store.load(kit.mid)["pending"]
    assert p["failed_rounds"] == 1 and p["fixes"] and p["plan_change"] == "use 15m"


def test_usage_start_set_during_an_answer_turn_survives(kit):
    class Sys(engine._NoSystem):
        def usage(self):
            return {"seven_day": {"used": 0.33, "resets_at": 1}}
    m = store.load(kit.mid)
    m["status"], m["pending"]["read_for"] = "waiting_owner", "v01"
    store.save(m)
    engine.owner_says(kit.mid, "lead", "hello")
    kit.turns.over[("lead", "owner")] = lambda _: engine.approve_read(kit.mid, "yes") or None
    run(kit.mk(system=Sys()).answer())
    m = store.load(kit.mid)
    assert m["usage_start"] == 0.33 and m["status"] == "running" and m["pending"]["read_ok"] == "yes"


def test_the_owners_patch_survives_an_engine_save():
    m = store.new_mission("s", TEAM, {"tries": {"n": 5}}, "team")
    eng = engine.Engine(m["id"], hb=FakeHB())
    d = store.load(m["id"])
    d["limits"], d["test_months"], d["team"] = {"hours": {"n": 2}}, "ask", {**TEAM, "lead": {"model": "opus", "effort": "high"}}
    store.save(d)
    eng.m["round"] = 3
    eng._save()
    got = store.load(m["id"])
    assert (got["limits"], got["test_months"], got["team"]["lead"]["model"], got["round"]) == \
        ({"hours": {"n": 2}}, "ask", "opus", 3)
    eng._save()  # a second save keeps it too
    assert store.load(m["id"])["limits"] == {"hours": {"n": 2}}


def test_an_ending_writes_the_wrapup_once(kit):
    from missions import config
    kit.fake.reads[f"m{kit.mid}_v01"] = {"held": True, "line": "", "close": "close"}
    assert run(kit.eng().run()) == "achieved"
    assert (config.vault() / "RECENT.md").read_text().count(f"Mission {kit.mid} ") == 1


def test_a_team_patch_during_a_run_reaches_the_next_turns_command_and_a_new_model_starts_fresh(kit):
    from missions import worker
    seen = []
    orig = kit.turns

    async def spy(mid, role, prompt, *, model, effort, session_id=None, **kw):
        seen.append((role, worker.command(mid, role, model, effort, session_id), session_id))
        if len(seen) == 2:  # the owner PATCHes (a disk write) while the engine holds its own copy
            m = store.load(mid)
            m["team"]["lead"] = {"model": "opus", "effort": "max"}
            store.save(m)
        return await orig(mid, role, prompt, model=model, effort=effort, session_id=session_id, **kw)

    eng = kit.eng()
    eng.run_turn = spy
    for _ in range(3):
        asyncio.run(eng._turn("lead", "ideas"))
    cmds = [c for r, c, _ in seen if r == "lead"]
    arg = lambda c, f: c[c.index(f) + 1]
    assert arg(cmds[1], "--model") == "haiku" and "--resume" in cmds[1]  # turn 2 was already on its way
    assert arg(cmds[2], "--model") == "opus" and arg(cmds[2], "--effort") == "max"
    assert "--resume" not in cmds[2] and store.load(kit.mid)["team"]["lead"]["model"] == "opus"

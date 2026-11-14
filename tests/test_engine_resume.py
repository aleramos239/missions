"""Resume: the app dies in build, wait or read; a new Engine from disk goes on without a second version or read."""
from missions import engine, store
from tests.test_engine import Kill, kit, run, steps  # noqa: F401
from tests.test_engine_blind import stop_at


def idempotent_start(kit):
    """The real hb.start_read starts nothing for a name already claimed; FakeHB logs every call, so make it the same."""
    orig = kit.fake.start_read

    def start(mid, name, box, said=None):
        if not any(s[1] == name for s in kit.fake.started):
            return orig(mid, name, box, said)
        kit.fake.calls.append(("start_read", mid, name, box, said))
        return 4242
    kit.fake.start_read = start


def die_then_resume(kit):
    eng = kit.eng()
    try:
        run(eng.run())
    except Kill:
        pass
    engine._active.clear()
    eng2 = kit.eng()
    stop_at(eng2, kit, 1)
    return run(eng2.run())


def test_a_death_in_build_resumes_without_making_a_version_twice(kit):
    n = f"m{kit.mid}_v01"

    def die(t):
        kit.fake.made_[(kit.mid, n)] = {"wf": True, "job_id": "j1"}  # the Builder got v01 on the ledger, then the app died
        raise Kill()
    kit.turns.over[("builder", "build")] = [die]
    assert die_then_resume(kit) == "stopped"
    builds = [t for t in kit.turns.log if t[1] == "build"]
    assert len(builds) == 1  # the resumed engine finds v01 on the ledger and asks for nothing
    m = store.load(kit.mid)
    assert [v["name"] for v in m["versions"]] == [n] and m["reads"] == 1


def test_the_build_prompt_after_a_death_lists_the_names_already_on_the_ledger(kit):
    n = f"m{kit.mid}_v01"
    kit.turns.over[("lead", "ideas")] = {"plan": [
        {"version": "v01", "idea": "a", "family": "fvg", "why": "w"}, {"version": "v02", "idea": "b", "family": "fvg", "why": "w"}]}

    def die(t):
        kit.fake.made_[(kit.mid, n)] = {"wf": True, "job_id": "j1"}
        raise Kill()
    kit.turns.over[("builder", "build")] = [die]
    die_then_resume(kit)
    builds = [t for t in kit.turns.log if t[1] == "build"]
    assert len(builds) == 2 and f"do not make them again: {n}" in builds[1][2]
    assert [v["name"] for v in store.load(kit.mid)["versions"]].count(n) == 1


def test_a_death_in_wait_goes_on_with_the_saved_job_ids(kit):
    calls = {"n": 0}
    orig = kit.fake.job

    def job(j):
        calls["n"] += 1
        if calls["n"] == 1:
            raise Kill()
        return orig(j)
    kit.fake.job = job
    assert die_then_resume(kit) == "stopped"
    assert store.load(kit.mid)["step"] is None and store.load(kit.mid)["versions"][0]["job_id"] == "j1"
    assert [t[1] for t in kit.turns.log].count("build") == 1
    assert [c for c in kit.fake.calls if c == ("job", "j1")]


def test_a_death_in_read_starts_one_read_and_uses_a_result_that_appeared_meanwhile(kit):
    n = f"m{kit.mid}_v01"
    idempotent_start(kit)
    answers = iter([Kill])
    orig = kit.fake.read_result

    def rr(mid, name):
        if next(answers, None) is Kill:
            raise Kill()
        return orig(mid, name)
    kit.fake.read_result = rr
    assert die_then_resume(kit) == "stopped"
    assert len(kit.fake.started) == 1 and kit.fake.started[0][1] == n
    v = store.load(kit.mid)["versions"][0]
    assert v["state"] == "frozen" and store.load(kit.mid)["reads"] == 1


def test_a_death_while_waiting_for_his_yes_keeps_the_wait(kit):
    m = store.load(kit.mid)
    m["test_months"] = "ask"
    store.save(m)
    assert run(kit.eng().run()) == "waiting_owner"
    assert run(kit.mk().run()) == "waiting_owner" and kit.fake.started == []


# ---- fix round 1

def test_a_death_between_the_reading_save_and_start_read_starts_the_read_after_resume(kit):
    idempotent_start(kit)
    orig = kit.fake.start_read
    n = {"i": 0}

    def start(mid, name, box, said=None):
        n["i"] += 1
        if n["i"] == 1:
            raise Kill()
        return orig(mid, name, box, said)
    kit.fake.start_read = start
    assert die_then_resume(kit) == "stopped"
    assert n["i"] == 2 and len(kit.fake.started) == 1
    assert store.load(kit.mid)["versions"][0]["state"] == "frozen"


def test_start_read_raising_down_waits_and_then_starts_once(kit):
    idempotent_start(kit)
    orig = kit.fake.start_read
    left = {"n": 2}

    def start(mid, name, box, said=None):
        if left["n"]:
            left["n"] -= 1
            raise kit.fake.Down("door gone")
        return orig(mid, name, box, said)
    kit.fake.start_read = start
    eng = kit.eng()
    stop_at(eng, kit, 1)
    assert run(eng.run()) == "stopped"
    assert len(kit.fake.started) == 1 and store.load(kit.mid)["reads"] == 1


def test_a_slow_read_posts_one_line_and_polls_slowly(kit, monkeypatch):
    monkeypatch.setattr(engine, "READ_LIMIT", 100)
    n = kit.mid
    left = {"n": 12}
    orig = kit.fake.read_result

    def rr(mid, name):
        if left["n"]:
            left["n"] -= 1
            return None
        return orig(mid, name)
    kit.fake.read_result = rr
    eng = kit.eng()
    stop_at(eng, kit, 1)
    assert run(eng.run()) == "stopped"
    slow = [e for e in store.events(kit.mid) if "taking very long" in e["text"]]
    assert len(slow) == 1
    assert kit.clock.slept.count(30) >= 10 and kit.clock.slept.count(engine.READ_POLL) >= 5
    assert store.load(kit.mid)["reads"] == 1


def test_a_round_with_a_read_never_picks_a_second_version_after_a_resume(kit):
    m = store.load(kit.mid)
    for i in (1, 2):
        g = {"clear": True, "goal": {"value": 5.0 - i}, "lines": [], "charges": []}
        m["versions"].append({"name": f"m{kit.mid}_x{i}", "version": f"v0{i}", "round": 0, "family": "fvg",
                              "job_id": None, "state": "cleared", "box": str(i), "gate": g})
    m["step"], m["round"] = "read", 1
    m["pending"]["read_round"] = 1  # a version of this round was already read before the death
    store.save(m)
    eng = kit.eng()
    stop_at(eng, kit, 1)
    run(eng.run())
    assert kit.fake.started == []


def test_a_death_in_the_lead_read_turn_leaves_the_round_closed(kit):
    idempotent_start(kit)
    kit.turns.over[("lead", "read")] = [lambda t: (_ for _ in ()).throw(Kill())]
    assert die_then_resume(kit) == "stopped"
    m = store.load(kit.mid)
    assert len(kit.fake.started) == 1 and m["reads"] == 1 and m["versions"][0]["state"] == "frozen"

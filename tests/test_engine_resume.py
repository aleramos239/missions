"""Resume: the app dies in build, wait or read; a new Engine from disk goes on without a second version or read."""
from missions import engine, store
from tests.test_engine import Kill, kit, run, steps  # noqa: F401
from tests.test_engine_blind import stop_at


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

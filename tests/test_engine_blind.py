"""Blind for real: the owner's files hold a sentinel; no worker text may carry it."""
import inspect
import json

from missions import config, engine, store
from tests.test_engine import Kill, kit, run  # noqa: F401

S = "SENTINEL-48213"
N = 48213.77


def plant(kit):
    owner = {"held": False, "line": S, "close": S, "net": N, "months": [S, N]}
    for n in ("m1_v01", "m1_v02", "m1_v03"):
        kit.fake.owner_files[("read", kit.mid, n)] = owner
    kit.fake.owner_files[("refused", kit.mid)] = [{"why": S, "n": N}]
    d = config.hb_missions() / str(kit.mid)
    for rel in ("reads/m1_v01.json", "refused.jsonl", "read.log", "runs_wf/m1_v01/oos/x.json"):
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(json.dumps(owner))
    v = config.vault()
    (v).mkdir(parents=True, exist_ok=True)
    (v / "RECENT.md").write_text(f"- {S} {N}\n")
    (v / "MEMORY.md").write_text(f"- {S} {N}\n")


def stop_at(eng, kit, n):
    orig = eng._round_start

    def rs():
        if eng.m["round"] >= n:
            engine.stop(kit.mid)
        orig()
    eng._round_start = rs


def test_no_test_month_number_reaches_a_worker_across_three_rounds_a_read_and_a_resume(kit):
    plant(kit)
    kit.fake.reads["m1_v01"] = {"held": False, "line": "worse fills", "close": "far", "net": 1.0, "extra": "x"}
    # the app dies in round 2's Lead ideas turn; a fresh Engine from disk goes on
    kit.turns.over[("lead", "ideas")] = [None, lambda t: (_ for _ in ()).throw(Kill())]
    eng = kit.eng()
    stop_at(eng, kit, 3)
    try:
        run(eng.run())
    except Kill:
        pass
    engine._active.clear()
    eng2 = kit.eng()
    stop_at(eng2, kit, 3)
    assert run(eng2.run()) == "stopped"
    assert store.load(kit.mid)["round"] == 3 and store.load(kit.mid)["reads"] >= 1
    assert [t for t in kit.turns.log if t[1] == "read"]
    for role, step, prompt in kit.turns.log:
        assert S not in prompt and "48213" not in prompt, (role, step)
    for e in store.events(kit.mid):
        if e["for_workers"]:
            assert S not in json.dumps(e) and "48213" not in json.dumps(e)
    assert "48213" not in json.dumps(kit.eng().board())
    # only the one-line answer's three keys came through
    assert not any('"extra"' in p or "extra" in p for _, _, p in kit.turns.log)
    assert not [c for c in kit.fake.calls if c[0] in ("owner_read", "owner_refused")]
    src = inspect.getsource(engine)
    assert "owner_read" not in src and "owner_refused" not in src

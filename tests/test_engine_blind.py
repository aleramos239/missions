"""Blind for real: the owner's files hold a sentinel; no worker text may carry it."""
import inspect
import json

from missions import config, engine, roles, store
from tests.test_engine import Kill, kit3, make_kit, run  # noqa: F401

S = "SENTINEL-48213"
N = 48213.77
FULL = {"held": False, "line": S, "close": S, "net": N, "months": [S, N], "report": S}  # the owner's full payload


def names(mid):
    return [roles.version_name(mid, i) for i in (1, 2, 3)]


def plant(kit):
    for n in names(kit.mid):
        kit.fake.owner_files[("read", kit.mid, n)] = FULL
    kit.fake.owner_files[("refused", kit.mid)] = [{"why": S, "n": N}]
    d = config.hb_missions() / str(kit.mid)
    for rel in (f"reads/{names(kit.mid)[0]}.json", "refused.jsonl", "read.log",
                f"runs_wf/{names(kit.mid)[0]}/oos/x.json"):
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(json.dumps(FULL))
    # regression guard only: the engine never reads the vault's feed or a memory index, so these can never reach it
    v = config.vault()
    v.mkdir(parents=True, exist_ok=True)
    (v / "RECENT.md").write_text(f"- {S} {N}\n")
    (v / "MEMORY.md").write_text(f"- {S} {N}\n")


def stop_at(eng, kit, n):
    orig = eng._round_start

    def rs():
        if eng.m["round"] >= n:
            engine.stop(kit.mid)
        return orig()
    eng._round_start = rs


def leaks(kit):
    """Every place a worker could have met the sentinel."""
    out = []
    for role, step, prompt in kit.turns.log:
        if S in prompt or "48213" in prompt:
            out.append(("prompt", role, step))
    for e in store.events(kit.mid):
        if e["for_workers"] and ("48213" in json.dumps(e)):
            out.append(("event", e["n"]))
    if "48213" in json.dumps(kit.eng().board()):
        out.append(("board",))
    return out


def test_no_test_month_number_reaches_a_worker_across_three_rounds_a_read_an_answer_and_a_resume(kit3):
    kit = kit3
    plant(kit)
    # the door's one-line answer carries extra keys holding the sentinel: only held / line / close may pass
    kit.fake.reads[names(kit.mid)[0]] = {"held": False, "line": "worse fills", "close": "far", "net": N,
                                         "months": [S], "report": S}
    kit.turns.over[("lead", "ideas")] = [None, lambda t: (_ for _ in ()).throw(Kill())]
    engine.owner_says(kit.mid, "lead", "keep to 5m bars")  # an owner text answered during a wait
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
    m = store.load(kit.mid)
    assert kit.mid != 1 and m["round"] == 3 and m["reads"] >= 1
    assert [t for t in kit.turns.log if t[1] == "read"]
    assert any("worse fills" in p for _, s, p in kit.turns.log if s == "read")  # the one line does arrive
    assert leaks(kit) == []
    assert not [c for c in kit.fake.calls if c[0] in ("owner_read", "owner_refused")]
    src = inspect.getsource(engine)
    assert "owner_read" not in src and "owner_refused" not in src


def test_the_owner_answer_path_is_blind_too(kit3):
    kit = kit3
    plant(kit)
    kit.fake.jobs["j1"] = {"done": False, "ok": False, "said": "", "progress": None}
    n = {"i": 0}
    orig = kit.clock.sleep

    async def sleep(s):
        n["i"] += 1
        if n["i"] == 1:
            engine.owner_says(kit.mid, "doubter", "what about 2023?")
        if n["i"] == 2:
            kit.fake.jobs["j1"] = {"done": True, "ok": True, "said": "", "progress": None}
        await orig(s)
    eng = kit.eng()
    eng.sleep = sleep
    stop_at(eng, kit, 1)
    run(eng.run())
    assert [t for t in kit.turns.log if t[1] == "owner"]
    assert leaks(kit) == []


def test_a_door_refusal_reaches_workers_without_a_number(kit3):
    kit = kit3
    plant(kit)
    kit.fake.reads[names(kit.mid)[0]] = {"refused": f"that box was already read {S} net {N} over 12 months"}
    eng = kit.eng()
    stop_at(eng, kit, 1)
    run(eng.run())
    lines = [e["text"] for e in store.events(kit.mid) if e["who"] == "judge" and "already read" in e["text"]]
    assert lines == ["that box was already read net over months"]
    assert leaks(kit) == []


def test_the_leak_check_catches_a_deliberately_leaking_board(kit3, monkeypatch):
    kit = kit3
    plant(kit)

    def leaking(self):  # a board that reads reads/*.json: the forbidden thing
        d = config.hb_missions() / str(self.mid) / "reads"
        return {"oops": [p.read_text() for p in d.glob("*.json")]}
    monkeypatch.setattr(engine.Engine, "board", leaking)
    eng = kit3.eng()
    stop_at(eng, kit, 1)
    run(eng.run())
    assert leaks(kit)

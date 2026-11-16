"""The speed work (2026-11-16): the Builder writes cards only, the Judge starts every table at once and runs the code check, the build
ask shows a card the tool accepted before, and no reach check before a build."""
import json

from missions import hb, roles, store
from tests.test_engine import kit, round_then_stop, run, set_fake, steps  # noqa: F401


def three(kit):
    kit.turns.over[("lead", "ideas")] = lambda t: {"plan": [{"version": f"v0{i}", "idea": f"i{i}", "family": "fvg", "why": "w", "new": "n"}
                                                            for i in (1, 2, 3)]}
    for i in (1, 2, 3):
        set_fake(kit.fake, kit.mid, n=f"m{kit.mid}_v0{i}")


def judge_says(kit):
    return [e["text"] for e in store.events(kit.mid) if e["who"] == "judge"]


def test_the_builder_writes_cards_and_the_judge_starts_every_table_at_once(kit):
    three(kit)
    run(round_then_stop(kit).run())
    names = [f"m{kit.mid}_v0{i}" for i in (1, 2, 3)]
    starts = [i for i, c in enumerate(kit.fake.calls) if c[0] == "start"]
    assert sorted(kit.fake.calls[i][2] for i in starts) == names
    assert starts == list(range(starts[0], starts[0] + 3))           # one gather: no other call between the three starts
    vs = store.load(kit.mid)["versions"]
    assert [v["name"] for v in vs] == names and {v["job_id"] for v in vs} == {"j1"}
    builds = [t for t in kit.turns.log if t[1] == "build"]
    assert len(builds) == 1 and "Write the cards" in builds[0][2]


def test_no_reach_call_before_a_build(kit):
    run(round_then_stop(kit).run())
    assert not [c for c in kit.fake.calls if c[0] == "reach"] and store.load(kit.mid)["versions"]


def test_a_refused_start_is_posted_and_is_not_a_try(kit):
    three(kit)
    kit.fake.refuse_start = {f"m{kit.mid}_v02": "m%d_v02: no box can reach 2 trades a week: the most is 1.2" % kit.mid}
    run(round_then_stop(kit).run())
    assert [v["version"] for v in store.load(kit.mid)["versions"]] == ["v01", "v03"]
    assert any(t.startswith("v02 not started: ") and "no box can reach" in t for t in judge_says(kit))
    assert not any("v02 is not on the ledger" in t for t in judge_says(kit))
    assert len([t for t in kit.turns.log if t[1] == "build"]) == 1  # a refusal is not a missing card: no second Builder turn


def test_a_missing_card_gets_the_one_retry_turn_then_is_dropped(kit):
    kit.turns.over[("builder", "build")] = lambda t: {"built": [], "failed": [{"version": "v01", "why": "no block"}]}
    run(round_then_stop(kit).run())
    builds = [t for t in kit.turns.log if t[1] == "build"]
    assert len(builds) == 2 and f"These are not on the ledger: m{kit.mid}_v01. Make them now." in builds[1][2]
    assert store.load(kit.mid)["versions"] == [] and not [c for c in kit.fake.calls if c[0] == "start"]
    assert any("v01 is not on the ledger and is dropped" in t for t in judge_says(kit))


def test_the_build_ask_shows_a_card_the_tool_accepted_before(kit):
    kit.fake.card_example_ = '{"name": "m1_v00", "card": {"why": "x"}, "settings": {"exits": "hm40"}}'
    run(round_then_stop(kit).run())
    ask = next(t[2] for t in kit.turns.log if t[1] == "build")
    assert "A card this tool accepted before, copy its shape:\n" + kit.fake.card_example_ in ask
    assert ("card_example", kit.mid, None) in kit.fake.calls


def test_no_example_when_none_is_on_file(kit):
    run(round_then_stop(kit).run())
    assert "copy its shape:\n" not in next(t[2] for t in kit.turns.log if t[1] == "build")


def test_a_narrow_stage_asks_for_the_base_versions_card(kit):
    eng = kit.eng()
    eng.m["versions"].append({"name": f"m{kit.mid}_v07", "version": "v07", "round": 0, "state": "gated"})
    eng.m["pending"]["focus"] = {"stage": 1, "mode": "narrow", "base": "v07", "text": "t"}
    assert eng._example_base() == f"m{kit.mid}_v07"
    eng.m["pending"]["focus"] = {"stage": 1, "mode": "narrow", "base": "v23", "text": "t"}
    eng.m["brief"] = {**eng.m["brief"], "base": {"mission": 3, "version": "v23"}}
    assert eng._example_base() == "m3_v23"
    eng.m["pending"]["focus"] = {"stage": 1, "mode": "fresh", "base": None, "text": "t"}
    assert eng._example_base() is None


def test_the_judge_runs_the_code_check_with_no_builder_turn(kit):
    kit.fake.checks = {f"m{kit.mid}_v01": {"name": f"m{kit.mid}_v01", "passed": False, "failed": ["1.4"]}}
    run(round_then_stop(kit).run())
    assert ("check", kit.mid, f"m{kit.mid}_v01") in kit.fake.calls and "check" in steps(kit.mid)
    assert not [t for t in kit.turns.log if t[1] == "check"]
    assert any("v01: the code check failed on line 1.4" in t for t in judge_says(kit))


def test_the_contract_and_the_builder_prompt():
    assert "job_id" not in roles._C[("builder", "build")] and '"failed"' in roles._C[("builder", "build")]
    text = roles._read("builder")
    assert "hm40 unless the brief says hm60" in text and "Do NOT call `blueprint_wf` or `blueprint_code_check`" in text


# ---- the adapter

def test_start_probe_check_go_through_the_door(monkeypatch):
    seen = []
    monkeypatch.setattr(hb, "door", lambda *a, timeout=600: seen.append((a, timeout)) or {"ok": 1})
    hb.start(7, "m7_v01"), hb.probe(7, "m7_v01"), hb.check(7, "m7_v01")
    assert [s[0] for s in seen] == [("start", 7, "m7_v01"), ("probe", 7, "m7_v01"), ("check", 7, "m7_v01")]
    assert all(s[1] >= 900 for s in seen)


def test_card_example_reads_the_newest_card_or_the_base(monkeypatch):
    specs = {"m7_v02": {"name": "m7_v02", "version": 2, "card": {"why": "w"}, "run": {"exits": "hm60", "family": "fvg"}},
             "m3_v23": {"name": "m3_v23", "card": {"why": "b"}, "run": {"family": "orb"}}}
    monkeypatch.setattr(hb, "idea_spec", lambda n: specs.get(n))
    monkeypatch.setattr(hb, "ledger", lambda mid: [{"kind": "card", "ref": "m7_v01"}, {"kind": "card", "ref": "m7_v02"},
                                                   {"kind": "wf", "ref": "m7_v01"}])
    assert json.loads(hb.card_example(7)) == {"name": "m7_v02", "card": {"why": "w"}, "settings": {"exits": "hm60", "family": "fvg"}}
    assert json.loads(hb.card_example(7, "m3_v23"))["settings"] == {"family": "orb"}
    monkeypatch.setattr(hb, "ledger", lambda mid: [])
    assert hb.card_example(7) is None
    specs["m7_v02"]["card"] = {"why": "x" * 3000}
    assert hb.card_example(7, "m7_v02") is None  # over the cap: left out, never cut

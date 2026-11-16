"""The whole app on fakes: the real engine, FakeHB, a scripted run_turn. No process, no claude, no Homebase, no test month."""
from missions import engine, store, system
from tests.test_engine import LINES, CH, kit, run  # noqa: F401  (kit is the fixture)


def fill(kit, nums, *, clear, held=None, line="worse fills", close="far"):
    """Gate, table and read for versions m<id>_vNN. clear=False: every table fails the gate."""
    for n in nums:
        nm = f"m{kit.mid}_v{n:02d}"
        kit.fake.tables[nm] = {"pick": "12", "rows": [{"box": "12", "value": 20, "cell": 14}]}
        kit.fake.gates[(nm, "12")] = {"name": nm, "box": "12", "clear": clear, "lines": LINES, "charges": CH,
                                      "goal": {"kind": "points", "target": 3.0, "value": 4.0 if clear else 1.0,
                                               "met": clear}, "tries": n}
        kit.fake.reads[nm] = {"held": held, "line": line, "close": close} if clear else {"held": False, "line": "boxes",
                                                                                          "close": "far"}


def test_a_goal_that_cannot_be_reached_ends_out_of_reach_with_no_read(kit):
    fill(kit, range(1, 20), clear=False)
    orig = kit.turns.default

    def default(role, step, prompt):  # reach turns false after 6 tries
        if len(store.load(kit.mid)["versions"]) >= 6:
            kit.fake.reach.d["fvg"] = {"family": "fvg", "reachable": False}
        return orig(role, step, prompt)
    kit.turns.default = default
    assert run(kit.eng().run()) == "out_of_reach"
    m = store.load(kit.mid)
    assert m["status"] == "out_of_reach" and m["reads"] == 0 and len(m["versions"]) >= 6
    assert kit.fake.started == [] and not any(c[0] == "start_read" for c in kit.fake.calls)


def test_a_tries_limit_of_four_ends_as_limit_never_achieved(kit, monkeypatch):
    fill(kit, range(1, 20), clear=False)
    monkeypatch.setattr(system, "usage", lambda: {"seven_day": None})
    m = store.load(kit.mid)
    m["limits"] = {"tries": {"n": 4}}
    store.save(m)
    assert run(kit.eng(system=_Real()).run()) == "limit"
    m = store.load(kit.mid)
    assert m["status"] == "limit" and m["reads"] == 0 and len(m["versions"]) >= 4 and kit.fake.started == []


class _Real(engine._NoSystem):
    def limit_hit(self, m, tries_mission):
        return system.limit_hit(m, tries_mission)


def test_a_planted_edge_clears_in_round_three_and_one_read_holds(kit):
    fill(kit, (1, 2), clear=False)
    fill(kit, (3,), clear=True, held=True, line="", close="close")
    assert run(kit.eng().run()) == "achieved"
    m = store.load(kit.mid)
    assert m["status"] == "achieved" and m["round"] == 3 and m["reads"] == 1
    assert [s[1] for s in kit.fake.started] == [f"m{kit.mid}_v03"] and m["result"]["version"] == "v03"
    from missions import config
    assert any((config.vault() / "30-Projects/Onyx-Trading/Missions").glob("*.md"))
    assert (config.vault() / "RECENT.md").read_text().count(f"Mission {kit.mid} ") == 1


def test_a_near_copy_both_versions_freeze_and_the_mission_goes_on(kit):
    fill(kit, (1,), clear=True, held=False, line="worse fills", close="far")
    fill(kit, (2,), clear=True, held=False, line="under the bar", close="close")
    eng = kit.eng()
    orig = eng._round_start

    def rs():  # stop after two reads: the mission was still going on
        if eng.m["round"] >= 2:
            engine.stop(kit.mid)
        return orig()
    eng._round_start = rs
    assert run(eng.run()) == "stopped"
    m = store.load(kit.mid)
    assert [v["state"] for v in m["versions"][:2]] == ["frozen", "frozen"] and m["reads"] == 2
    assert [x[1] for x in kit.fake.started] == [f"m{kit.mid}_v01", f"m{kit.mid}_v02"]
    assert m["versions"][1]["heard"]["line"] == "under the bar" and m["status"] != "achieved"

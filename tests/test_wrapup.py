import json

import pytest

from missions import config, engine, store, wrapup
from tests.test_api import TEAM, call, mk

PLANTED = "7777.77"
KEY = "[[1-reach-3-points]]"


def ended(status="out_of_reach"):
    m = store.new_mission("reach 3 points", TEAM, {}, "team")
    m.update(status=status, brief={"goal": {"kind": "points", "target": 3.0}}, round=2, reads=1, cost_usd=1.5,
             versions=[{"version": "v01", "name": "m1_v01", "family": "fvg", "state": "dropped", "round": 1,
                        "why": "too few trades", "box_label": "12", "gate": {}},
                       {"version": "v02", "name": "m1_v02", "family": "fvg", "state": "frozen", "round": 2,
                        "box_label": "7", "gate": {"goal": {"value": 4.0}, "lines": [{"line": "luck", "ok": False}]},
                        "heard": {"held": False, "line": "worse fills", "close": "far"}}])
    store.save(m)
    (config.hb_missions() / str(m["id"]) / "reads").mkdir(parents=True)
    (config.hb_missions() / str(m["id"]) / "reads" / "m1_v02.json").write_text(json.dumps({"net": PLANTED}))
    return m["id"]


def vault_setup():
    v = config.vault()
    (v / "30-Projects/Onyx-Trading").mkdir(parents=True)
    (v / "RECENT.md").write_text("---\nname: RECENT\n---\n\n# RECENT\n\nintro line\n\n- 2026-11-14 · code · old · [[a]]\n- older\n")
    return v


def run_end(mid):
    eng = engine.Engine(mid)
    wrapup.write(eng.m, eng.board())
    return eng


def test_note_recent_and_map():
    v = vault_setup()
    old = (v / "RECENT.md").read_text()
    eng = run_end(ended())
    txt = next((v / "30-Projects/Onyx-Trading/Missions").glob("*.md")).read_text()
    assert txt.startswith("---\n") and PLANTED not in txt and "[[" in txt
    assert "worse fills" in txt and "too few trades" in txt
    new = (v / "RECENT.md").read_text()
    assert new.count(KEY) == 1 and new.replace(wrapup.recent_line(eng.m) + "\n", "") == old
    assert new.index(KEY) < new.index("[[a]]")
    mp = (v / "30-Projects/Onyx-Trading" / wrapup.MAP_FILE).read_text()
    assert mp.split("## Missions")[1].strip().endswith("· fvg · out of reach · " + KEY)


def test_twice_makes_one_note_one_line():
    v = vault_setup()
    mid = ended()
    run_end(mid)
    run_end(mid)
    assert (v / "RECENT.md").read_text().count(KEY) == 1
    assert (v / "30-Projects/Onyx-Trading" / wrapup.MAP_FILE).read_text().count(KEY) == 1
    assert len(list((v / "30-Projects/Onyx-Trading/Missions").glob("*.md"))) == 1


def test_stop_runs_it_once():
    vault_setup()
    mid = mk(status="running")
    engine.stop(mid)
    assert (config.vault() / "RECENT.md").read_text().count(f"Mission {mid} ") == 1


def test_mark_dead_needs_his_words_and_adds_a_row():
    d = vault_setup() / "30-Projects/Onyx-Trading/dead-families.md"
    d.write_text("# x\n\n| family | verdict | date | why |\n|---|---|---|---|\n\nRelated: [[x]]\n")
    with pytest.raises(ValueError):
        wrapup.mark_dead("fvg", "no", "  ")
    assert "fvg" not in d.read_text()
    wrapup.mark_dead("fvg", "no edge", "kill it")
    t = d.read_text()
    assert t.index("| fvg | dead") < t.index("Related") and t.count("| fvg") == 1


def test_dead_route():
    vault_setup()
    d = config.vault() / "30-Projects/Onyx-Trading/dead-families.md"
    d.write_text("| family | verdict | date | why |\n|---|---|---|---|\n")
    mid = ended()
    assert call("POST", f"/api/missions/{mid}/dead", json={"family": "fvg"}).status_code == 400
    assert call("POST", f"/api/missions/{mid}/dead", json={"family": "zzz", "said": "yes"}).status_code == 400
    assert call("POST", f"/api/missions/{mid}/dead", json={"family": "fvg", "said": "yes mark it"}).status_code == 200
    assert "| fvg | dead" in d.read_text()


def test_a_failed_write_leaves_the_file_whole(monkeypatch):
    v = vault_setup()
    old = (v / "RECENT.md").read_text()
    monkeypatch.setattr(wrapup.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        run_end(ended())
    assert (v / "RECENT.md").read_text() == old


def test_map_line_lands_at_the_end_of_its_section_with_a_newline():
    v = vault_setup()
    mp = v / "30-Projects/Onyx-Trading" / wrapup.MAP_FILE
    mp.write_text("# x\n\n## Missions\n\n- 2026-01-01 · a · reached · [[z]]\n\n## Later\n\ntail")
    run_end(ended())
    t = mp.read_text()
    assert t.index(KEY) < t.index("## Later") and t.index("[[z]]") < t.index(KEY) and t.endswith("tail")
    mp.write_text("# x\n\n## Missions\n\n- 2026-01-01 · a · reached · [[z]]")  # no final newline
    wrapup._edit(mp, lambda t: wrapup._map_add(t, "- new [[n]]", "n"))
    assert mp.read_text().endswith("[[z]]\n- new [[n]]\n")


def test_title_with_colon_and_newline_and_recent_after_frontmatter():
    v = vault_setup()
    mid = ended()
    m = store.load(mid)
    m["title"] = "a: b\nc"
    store.save(m)
    (v / "RECENT.md").write_text("---\nname: R\ntags:\n- x\n---\n\n- old\n")
    run_end(mid)
    r = (v / "RECENT.md").read_text()
    assert r.index("Mission 1") > r.index("\n---\n") and "\n" not in wrapup.recent_line(store.load(mid))
    assert 'description: "' in next((v / "30-Projects/Onyx-Trading/Missions").glob("*.md")).read_text()


def test_dead_missing_file_bad_types_and_duplicates():
    v = vault_setup()
    mid = ended()
    post = lambda b: call("POST", f"/api/missions/{mid}/dead", json=b).status_code
    assert post({"family": "fvg", "said": "yes"}) == 400  # no dead-families.md
    d = v / "30-Projects/Onyx-Trading/dead-families.md"
    d.write_text("| family | verdict | date | why |\n|---|---|---|---|\n")
    assert post({"family": 5, "said": "yes"}) == 400 and post({"family": "fvg", "said": ["x"]}) == 400
    assert post({"family": "fvg", "said": "yes"}) == 200 and post({"family": "fvg", "said": "yes"}) == 200
    assert d.read_text().count("| fvg |") == 1

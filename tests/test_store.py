import threading

import pytest

from missions import config, store

TEAM = {r: {"model": "opus", "effort": "high"} for r in store.ROLES}
LIMITS = {"until_goal": False, "tries": {"on": True, "n": 40}, "hours": {"on": True, "n": 8},
          "usage": {"on": True, "pct": 40}}


def mk(s="a goal", team=TEAM):
    return store.new_mission(s, team, LIMITS, "team")


def test_id_skips_both_sides():
    (config.hb_missions() / "5").mkdir(parents=True)
    assert mk()["id"] == 6
    (config.home() / "9").mkdir(parents=True)
    assert mk()["id"] == 10


def test_new_mission_shape():
    m = mk("x" * 50)
    assert m["title"] == "x" * 40 and m["status"] == "briefing" and m["cost_usd"] == 0.0
    assert m["test_months"] == "team" and m["sessions"] == {} and m["result"] is None


def test_roundtrip_and_list_newest_first():
    a, b = mk("a"), mk("b")
    b["round"] = 3
    store.save(b)
    assert store.load(b["id"])["round"] == 3
    assert [m["id"] for m in store.missions()] == [b["id"], a["id"]]


def test_torn_line_and_after():
    m = mk()
    i = m["id"]
    for k in range(3):
        store.event(i, "note", "lead", f"t{k}")
    with open(store.events_path(i), "a") as f:
        f.write('{"n": 4, "ty')
    assert [e["n"] for e in store.events(i)] == [1, 2, 3]
    assert [e["n"] for e in store.events(i, after=2)] == [3]
    e = store.event(i, "note", "lead", to="builder", for_workers=False)
    assert e["to"] == "builder" and e["for_workers"] is False and e["n"] == 4
    assert [x["n"] for x in store.events(i)] == [1, 2, 3, 4]


def test_event_numbers_from_threads():
    i = mk()["id"]
    ts = [threading.Thread(target=lambda: [store.event(i, "n", "w") for _ in range(25)]) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert [e["n"] for e in store.events(i)] == list(range(1, 101))


@pytest.mark.parametrize("model,effort", [("gpt", "high"), ("opus", "ultra")])
def test_bad_team_refused(model, effort):
    with pytest.raises(ValueError):
        mk(team={**TEAM, "lead": {"model": model, "effort": effort}})


def test_claude_bin(tmp_path, monkeypatch):
    root = tmp_path / "cc"
    for v in ("2.1.285", "2.1.321"):
        p = root / v / "abc" / "claude.app/Contents/MacOS/claude"
        p.parent.mkdir(parents=True)
        p.touch()
    monkeypatch.setenv("MISSIONS_CLAUDE_ROOT", str(root))
    assert "2.1.321" in str(config.claude_bin())
    config.save_settings({"claude": "/x/claude"})
    assert str(config.claude_bin()) == "/x/claude"


def test_claude_bin_missing(monkeypatch):
    monkeypatch.setenv("PATH", "")
    with pytest.raises(config.ConfigError):
        config.claude_bin()


def test_work_dir_empty():
    d = config.work_dir(3, "lead")
    (d / "f").write_text("x")
    assert list(config.work_dir(3, "lead").iterdir()) == []

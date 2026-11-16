"""Items 22 and 23: one saved "turn" row per worker turn, and the workers' talk saved for the owner only."""
from missions import engine, store, worker
from tests.test_engine import block, kit, round_then_stop, run  # noqa: F401  (kit is a fixture)


def rows(mid, type):
    return [e for e in store.events(mid) if e["type"] == type]


def test_a_round_writes_one_turn_row_per_worker_turn(kit):
    run(round_then_stop(kit).run())
    turns = rows(kit.mid, "turn")
    assert [(e["who"], e["text"]) for e in turns] == [(r, s) for r, s, _ in kit.turns.log]
    for e in turns:
        assert e["for_workers"] is False
        assert set(e["data"]) == {"secs", "cost", "tools", "ok", "why", "model", "effort"}
        assert e["data"]["ok"] is True and e["data"]["model"] == "haiku" and e["data"]["effort"] == "low"


def test_a_failed_turn_records_ok_false_its_why_cost_and_tool_names(kit):
    bad = worker.Turn(ok=False, why="timeout", cost_usd=0.25,
                      tool_calls=[{"name": "mcp__homebase__m1_trades", "input": {}}, {"name": "x", "input": None}])
    kit.turns.over[("lead", "verdict")] = [bad]
    run(round_then_stop(kit).run())
    v = [e for e in rows(kit.mid, "turn") if e["who"] == "lead" and e["text"] == "verdict"]
    assert v[0]["data"] == {"secs": 0.0, "cost": 0.25, "tools": ["m1_trades", "x"], "ok": False, "why": "timeout",
                            "model": "haiku", "effort": "low"}
    assert v[1]["data"]["ok"] is True  # the retry has its own row


def test_a_turn_on_the_plan_limit_gets_a_row_too(kit):
    kit.turns.over[("lead", "verdict")] = [worker.Turn(ok=False, why="plan", resets_at=None)]
    run(round_then_stop(kit).run())
    assert [e["data"]["why"] for e in rows(kit.mid, "turn") if e["text"] == "verdict"] == ["plan", None]


def test_talk_is_saved_once_for_the_owner_and_never_reaches_a_worker(kit):
    kit.turns.over[("lead", "verdict")] = ["I think it holds.", "I think it holds.\n" + block(
        {"to_owner": "Two plain sentences.", "next": "n"})[len("Words.\n"):]]  # no json first: the retry repeats the talk
    eng = round_then_stop(kit)
    run(eng.run())
    talk = rows(kit.mid, "talk")
    v = [e for e in talk if e["who"] == "lead" and e["data"] == {"step": "verdict"}]
    assert [e["text"] for e in v] == ["I think it holds."] and v[0]["for_workers"] is False
    assert {e["text"] for e in talk} >= {"Words."}  # every default reply talks
    eng.m["pending"]["seen"] = {}
    hidden = [f"{e['who']}: {e['text']}" for e in talk + rows(kit.mid, "turn")]
    for r in store.ROLES:
        out = eng._chat_for(r)
        assert out and not any(h in out for h in hidden)
    assert not any("Words." in p or "I think it holds." in p for _, _, p in kit.turns.log)


def test_no_talk_row_for_an_empty_talk_and_it_is_capped(kit):
    kit.turns.over[("lead", "verdict")] = [block({"to_owner": "x", "next": "n"})[len("Words.\n"):]]
    kit.turns.over[("lead", "read")] = ["y" * 7000 + "\n" + block({"next": "go_on", "why": "w"})[len("Words.\n"):]]
    run(round_then_stop(kit).run())
    by = {e["data"]["step"]: e["text"] for e in rows(kit.mid, "talk") if e["who"] == "lead"}
    assert "verdict" not in by and len(by["read"]) == 6000

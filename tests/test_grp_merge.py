"""Where the 2026-11-16 groups meet: a refused start keeps the Judge's numbers and lands on the board with its reason."""
from missions import engine, store
from tests.test_engine import kit, round_then_stop, run  # noqa: F401
from tests.test_grp_speed import judge_says, three


def test_a_refused_start_keeps_its_numbers_and_is_on_the_board_with_its_reason(kit):  # noqa: F811
    three(kit)
    why = f"m{kit.mid}_v02: no box can reach 2 trades a week: the most is 1.2"
    kit.fake.refuse_start = {f"m{kit.mid}_v02": why}
    run(round_then_stop(kit).run())
    assert f"v02 not started: {why}." in judge_says(kit)
    eng = kit.eng()
    assert [(u["idea"], u["why"]) for u in eng.m["unbuilt"]] == [("i2", f"not started: {why}")]
    assert any(t.startswith("v02 ") and t.endswith(f"-> not started: {why}") for t in eng.board()["tried"])


def test_a_start_refusal_of_several_lines_loses_its_numbers():
    assert engine._said("one line, the most is 1.2") == "one line, the most is 1.2"
    assert "1.2" not in engine._said("Traceback\n  net 1.2 on line 40")
    assert "7" not in engine._said("x7 " * 200)

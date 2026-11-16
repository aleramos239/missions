import pytest

from missions import engine, roles, store
from tests.test_engine import kit, make_kit, run  # noqa: F401  (kit is a fixture)

WRITERS = ("builder", "doubter", "defender")


def _writers(kit):
    run(kit.mk()._ideas())
    return [t[0] for t in kit.turns.log if t[1] == "ideas"]


def _seed(kit, **pending):
    m = store.load(kit.mid)
    m["pending"].update(pending)
    store.save(m)
    return m


def test_no_score_only_the_builder_writes_ideas(kit):
    assert sorted(_writers(kit)) == ["builder", "lead"]
    lead = next(t[2] for t in kit.turns.log if t[:2] == ("lead", "ideas"))
    assert "idea of builder" in lead and "The three ideas" not in lead


def test_a_scored_version_brings_all_three_writers(kit):
    m = store.load(kit.mid)
    m["versions"].append({"name": f"m{kit.mid}_v01", "version": "v01", "round": 0, "family": "fvg", "job_id": None,
                          "state": "scored", "box": "12", "gate": {"clear": False, "lines": [], "charges": []}})
    store.save(m)
    assert sorted(_writers(kit)) == ["builder", "defender", "doubter", "lead"]


def test_a_narrow_focus_brings_all_three_writers_before_any_gate(kit):
    _seed(kit, focus={"stage": 1, "mode": "narrow", "base": "v01", "text": "t"})
    assert sorted(_writers(kit)) == ["builder", "defender", "doubter", "lead"]


def test_a_fresh_focus_keeps_only_the_builder(kit):
    _seed(kit, focus={"stage": 1, "mode": "fresh", "base": None, "text": "t"})
    assert sorted(_writers(kit)) == ["builder", "lead"]


def test_doubter_cut_to_one_defender_to_two_builder_three(kit):
    _seed(kit, focus={"stage": 1, "mode": "narrow", "base": "v01", "text": "t"})
    for r in WRITERS:
        kit.turns.over[(r, "ideas")] = (lambda r: lambda t: {"ideas": [{"idea": f"{r} #{i}", "family": "fvg", "why": "w"}
                                                                       for i in range(5)]})(r)
    run(kit.mk()._ideas())
    lead = next(t[2] for t in kit.turns.log if t[:2] == ("lead", "ideas"))
    for r, n in (("builder", 3), ("doubter", 1), ("defender", 2)):
        assert sum(f"{r} #{i}" in lead for i in range(5)) == n


def test_each_role_ideas_prompt_holds_only_its_own_job():
    for r in WRITERS:
        p = roles.prompt(r, "ideas", brief={}, board="", chat="", ask="")
        assert roles._IDEA_JOB[r] in p
        assert all(roles._IDEA_JOB[o] not in p for o in WRITERS if o != r)
    assert all(j not in roles.prompt("lead", "ideas", brief={}, board="", chat="", ask="")
               for j in roles._IDEA_JOB.values())

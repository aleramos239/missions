import json
import os
import sys
import time
from pathlib import Path

import pytest

from missions import config, hb, store
from tests.fakes.hb import FakeHB

FAKE = Path(__file__).parent / "fakes" / "judge"


@pytest.fixture
def judge(tmp_path, monkeypatch):
    f = tmp_path / "answers.json"
    monkeypatch.setenv("MISSIONS_JUDGE", str(FAKE))
    monkeypatch.setenv("FAKE_JUDGE", str(f))

    def put(d):
        f.write_text(json.dumps(d))
    return put


def test_door_returns_the_json(judge):
    judge({"accounts": [{"id": "a"}], "tries 7 orb": {"total": 3}})
    assert hb.accounts() == [{"id": "a"}]
    assert hb.tries(7, "orb") == {"total": 3}


def test_exit_1_is_refused_with_the_doors_words(judge):
    judge({"gate 7 m7_v01 12": {"refused": "frozen"}})
    with pytest.raises(hb.Refused, match="frozen"):
        hb.gate(7, "m7_v01", 12)
    with pytest.raises(hb.Refused, match="no such fake"):
        hb.door("nope")


def test_missing_door_is_down(monkeypatch, tmp_path):
    monkeypatch.setenv("MISSIONS_JUDGE", str(tmp_path / "none"))
    with pytest.raises(hb.Down):
        hb.accounts()


def test_write_brief_keys_and_no_drafts():
    b = {"approved": True, "owner_said": "go", "test_months": "ask",
         "goal": {"kind": "eval", "target": 0.5, "rule": "x"}}
    hb.write_brief(7, b)
    assert json.loads((config.hb_missions() / "7" / "brief.json").read_text()) == b
    with pytest.raises(hb.Refused):
        hb.write_brief(7, {**b, "drafts": True})
    with pytest.raises(hb.Refused):
        hb.write_brief(7, {**b, "extra": 1})
    hb.unapprove(7)
    assert json.loads((config.hb_missions() / "7" / "brief.json").read_text())["approved"] is False
    hb.unapprove(99)  # no brief: no error


def test_made_finds_wf_and_its_job():
    d = config.hb_missions() / "7"
    d.mkdir(parents=True)
    rows = [{"kind": "card", "ref": "m7_v01"}, {"kind": "job", "ref": "20261114T000000-abcdef"},
            {"kind": "wf", "ref": "m7_v01"}, "torn{"]
    (d / "ledger.jsonl").write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows))
    assert hb.made(7, "m7_v01") == {"wf": True, "job_id": "20261114T000000-abcdef"}
    assert hb.made(7, "m7_v02") is None


def test_family_of_and_job(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMEBASE_IDEAS_ROOT", str(tmp_path / "ideas"))
    i = tmp_path / "ideas" / "m7_v01"
    i.mkdir(parents=True)
    (i / "spec.json").write_text(json.dumps({"name": "m7_v01", "run": {"family": "orb"}}))
    assert hb.family_of("m7_v01") == "orb" and hb.family_of("m7_zz") is None
    j = tmp_path / "ideas" / "_jobs" / "20261114T000000-abcdef"
    j.mkdir(parents=True)
    (j / "job.json").write_text(json.dumps({"state": "running", "progress": "box 12/120"}))
    assert hb.job("20261114T000000-abcdef") == {"done": False, "ok": False, "said": "box 12/120", "progress": [12, 120]}
    (j / "job.json").write_text(json.dumps({"state": "done", "progress": ""}))
    (j / "result.json").write_text(json.dumps({"ok": True, "text": "table ready"}))
    assert hb.job("20261114T000000-abcdef") == {"done": True, "ok": True, "said": "table ready", "progress": None}


def _wait(p, n=50):
    for _ in range(n):
        if p.exists():
            return
        time.sleep(0.1)


def test_start_read_then_result(judge):
    store.new_mission("s", {r: {"model": "opus", "effort": "low"} for r in store.ROLES}, {}, "team")
    judge({"read 1 m1_v01 12": {"held": True, "line": "ok", "close": False}})
    assert hb.read_result(1, "m1_v01") is None  # never started
    hb.start_read(1, "m1_v01", "12")
    _wait(store.mdir(1) / "read_m1_v01.json")
    assert hb.read_result(1, "m1_v01") == {"held": True, "line": "ok", "close": False}


def test_dead_pid_and_no_file_is_stopped():
    store.new_mission("s", {r: {"model": "opus", "effort": "low"} for r in store.ROLES}, {}, "team")
    (store.mdir(1) / "read_m1_v01.pid").write_text("999999")
    assert hb.read_result(1, "m1_v01") == {"refused": hb.STOPPED}


def test_second_start_while_running_starts_nothing(judge, monkeypatch):
    store.new_mission("s", {r: {"model": "opus", "effort": "low"} for r in store.ROLES}, {}, "team")
    judge({"read 1 m1_v01 12": {"held": True, "line": "ok", "close": False}})
    monkeypatch.setenv("FAKE_JUDGE_SLEEP", "1.5")
    p1 = hb.start_read(1, "m1_v01", "12")
    assert hb.start_read(1, "m1_v01", "12") == p1
    assert hb.read_result(1, "m1_v01") is None
    _wait(store.mdir(1) / "read_m1_v01.json", 40)


def test_fakehb_has_every_hb_function():
    pub = {n for n in dir(hb) if not n.startswith("_") and callable(getattr(hb, n))
           and getattr(getattr(hb, n), "__module__", "") == "missions.hb" and n not in ("Refused", "Down")}
    assert pub <= {n for n in dir(FakeHB) if not n.startswith("_")} | {"door", "reach"}

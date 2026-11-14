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


def _jobs(tmp_path, monkeypatch, **jobs):
    monkeypatch.setenv("HOMEBASE_IDEAS_ROOT", str(tmp_path / "ideas"))
    for jid, (cmd, name) in jobs.items():
        d = tmp_path / "ideas" / "_jobs" / jid
        d.mkdir(parents=True)
        (d / "job.json").write_text(json.dumps({"command": cmd, "name": name, "state": "done"}))


def _ledger(rows):
    d = config.hb_missions() / "7"
    d.mkdir(parents=True)
    (d / "ledger.jsonl").write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows))


def test_made_pairs_a_version_with_its_own_job(tmp_path, monkeypatch):
    _jobs(tmp_path, monkeypatch, ja=("wf run", "m7_a"), jb=("wf run", "m7_b"), jc=("build", "m7_a"))
    _ledger([{"kind": "job", "ref": "ja"}, {"kind": "job", "ref": "jb"}, {"kind": "job", "ref": "jc"},
             {"kind": "wf", "ref": "m7_a"}, "torn{"])
    assert hb.made(7, "m7_a") == {"wf": True, "job_id": "ja"}
    assert hb.made(7, "m7_zz") is None


def test_made_without_a_matching_job(tmp_path, monkeypatch):
    _jobs(tmp_path, monkeypatch, jc=("build", "m7_a"))
    _ledger([{"kind": "job", "ref": "jc"}, {"kind": "job", "ref": "gone"}, {"kind": "wf", "ref": "m7_a"}])
    assert hb.made(7, "m7_a") == {"wf": True, "job_id": None}


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


def _mission():
    store.new_mission("s", {r: {"model": "opus", "effort": "low"} for r in store.ROLES}, {}, "team")


def test_dead_pid_and_no_file_is_stopped():
    _mission()
    (store.mdir(1) / "read_m1_v01.pid").write_text("999999")
    assert hb.read_result(1, "m1_v01") == {"refused": hb.STOPPED}


def test_start_after_a_finished_read_starts_nothing(judge):
    _mission()
    judge({"read 1 m1_v01 12": {"held": True, "line": "first", "close": False}})
    pid = hb.start_read(1, "m1_v01", "12")
    _wait(store.mdir(1) / "read_m1_v01.json")
    judge({"read 1 m1_v01 12": {"held": False, "line": "second", "close": False}})
    assert hb.start_read(1, "m1_v01", "12") == pid
    time.sleep(0.3)
    assert hb.read_result(1, "m1_v01")["line"] == "first"


def test_two_starts_race_one_process(judge, monkeypatch):
    _mission()
    judge({"read 1 m1_v01 12": {"held": True, "line": "ok", "close": False}})
    monkeypatch.setenv("FAKE_JUDGE_SLEEP", "1")
    spawned = []
    real = hb.subprocess.Popen
    monkeypatch.setattr(hb.subprocess, "Popen", lambda *a, **k: spawned.append(1) or real(*a, **k))
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda _: hb.start_read(1, "m1_v01", "12"), range(2)))
    assert len(spawned) == 1
    _wait(store.mdir(1) / "read_m1_v01.json", 40)


def test_empty_claim_is_not_a_second_spawn(judge):
    _mission()
    (store.mdir(1) / "read_m1_v01.pid").write_text("")
    hb.start_read(1, "m1_v01", "12")
    assert not (store.mdir(1) / "read_m1_v01.json").exists()
    assert hb.read_result(1, "m1_v01") is None


def test_box_is_checked(judge):
    for bad in ("-x", "a b", "../x", ""):
        with pytest.raises(hb.Refused):
            hb.gate(7, "m7_v01", bad)
    _mission()
    with pytest.raises(hb.Refused):
        hb.start_read(1, "m1_v01", "-rf")


def test_door_timeout_is_slow(tmp_path, monkeypatch):
    s = tmp_path / "slow"
    s.write_text("#!/bin/sh\nsleep 5\n")
    s.chmod(0o755)
    monkeypatch.setenv("MISSIONS_JUDGE", str(s))
    with pytest.raises(hb.Slow, match="more than 0.2"):
        hb.door("x", timeout=0.2)
    assert issubclass(hb.Slow, hb.Down)


def test_job_whose_process_is_gone(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMEBASE_IDEAS_ROOT", str(tmp_path / "ideas"))
    j = tmp_path / "ideas" / "_jobs" / "j1"
    j.mkdir(parents=True)
    (j / "job.json").write_text(json.dumps({"state": "running", "pid": 999999, "progress": "1/2"}))
    assert hb.job("j1") == {"done": True, "ok": False, "said": "the job's process is gone", "progress": None}
    (j / "job.json").write_text(json.dumps({"state": "running", "progress": "1/2"}))  # no pid: as it says
    assert hb.job("j1")["done"] is False


def test_slots(monkeypatch):
    class R:
        stdout = 'noise\n{"off": false, "cap": 4, "running": 1, "quiet": false}\n'
    monkeypatch.setattr(hb.subprocess, "run", lambda *a, **k: R)
    assert hb.slots() == {"cap": 4, "running": 1}
    R.stdout = '{"off": true}'
    assert hb.slots() == {"off": True}
    R.stdout = "boom"
    with pytest.raises(hb.Down):
        hb.slots()


def test_health(tmp_path, monkeypatch):
    import socket
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    monkeypatch.setenv("MISSIONS_CHART_PORT", str(srv.getsockname()[1]))
    c = tmp_path / "claude"
    c.write_text("#!/bin/sh\necho '2.1.321 (Claude Code)'\n")
    c.chmod(0o755)
    config.save_settings({"claude": str(c)})
    monkeypatch.setenv("MISSIONS_JUDGE", str(FAKE))
    assert hb.health() == {"chart_service": True, "door": True, "claude": "2.1.321"}
    srv.close()
    monkeypatch.setenv("MISSIONS_JUDGE", str(tmp_path / "none"))
    config.save_settings({"claude": str(tmp_path / "none")})
    assert hb.health() == {"chart_service": False, "door": False, "claude": None}


def test_fakehb_has_every_hb_function():
    pub = {n for n in dir(hb) if not n.startswith("_") and callable(getattr(hb, n))
           and getattr(getattr(hb, n), "__module__", "") == "missions.hb" and n not in ("Refused", "Down", "Slow")}
    assert pub <= {n for n in dir(FakeHB) if not n.startswith("_")} | {"door", "reach"}

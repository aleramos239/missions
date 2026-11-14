import asyncio
from unittest import mock

import pytest

from missions import config, store, system


def rate(kind, u, resets=None, status="allowed"):
    return {"rateLimitType": kind, "utilization": u, "resetsAt": resets, "status": status}


def test_a_window_at_091_blocks_a_turn_and_gives_its_reset():
    system.note_rate(rate("five_hour", 0.91, 5000))
    assert system.may_start_turn(now=1000) == (False, 5000)
    assert system.may_start_turn(now=6000) == (True, None)  # the reset passed: the figure is stale


def test_a_rejected_window_blocks_and_a_low_one_does_not():
    assert system.may_start_turn() == (True, None)
    system.note_rate(rate("seven_day", 0.2, 9e9))
    assert system.may_start_turn()[0]
    system.note_rate(rate("seven_day", 0.2, 9e9, status="rejected"))
    assert system.may_start_turn(now=1) == (False, 9e9)
    system.note_rate(None)
    assert system.usage()["seven_day"]["used"] == 1.0


def test_wait_for_plan_sleeps_to_the_reset_plus_60_or_900():
    got = []

    async def sleep(s):
        got.append(s)
    asyncio.run(system.wait_for_plan(1500, sleep=sleep, now=1000))
    asyncio.run(system.wait_for_plan(None, sleep=sleep))
    assert got == [560, 900]


def mission(**limits):
    return {"limits": limits, "run_seconds": 0, "usage_start": 0.10}


def test_each_limit_trips_at_its_number_and_none_with_until_goal():
    assert system.limit_hit(mission(tries={"n": 5}), 4) is None
    assert system.limit_hit(mission(tries={"n": 5}), 5) == "tries"
    m = mission(hours={"n": 2})
    m["run_seconds"] = 7199
    assert system.limit_hit(m, 0) is None
    m["run_seconds"] = 7200
    assert system.limit_hit(m, 0) == "hours"
    for lim in (dict(tries={"n": 1}), dict(hours={"n": 0.0001})):
        m = mission(until_goal=True, **lim)
        m["run_seconds"] = 99999
        assert system.limit_hit(m, 99) is None


def test_the_usage_limit_uses_the_move_since_the_start_not_the_level():
    m = mission(usage={"pct": 10})
    assert system.limit_hit(m, 0) is None  # never seen
    system.note_rate(rate("seven_day", 0.19, 9e9))
    assert system.limit_hit(m, 0) is None  # level 19 %, move 9 %
    system.note_rate(rate("seven_day", 0.20, 9e9))
    assert system.limit_hit(m, 0) == "usage"


def test_run_seconds_does_not_grow_while_paused_or_waiting():
    from missions import engine
    m = store.new_mission("x", {r: {"model": "sonnet", "effort": "low"} for r in store.ROLES}, {}, "team")
    t = [0]
    eng = engine.Engine(m["id"], clock=lambda: t[0])
    for status, grows in (("running", True), ("waiting_homebase", True), ("paused", False),
                          ("waiting_plan", False), ("waiting_owner", False)):
        eng.m["status"], eng.m["run_seconds"] = status, 0
        eng._save()
        t[0] += 10
        eng._save()
        assert (eng.m["run_seconds"] == 10) is grows, status


def test_alert_text_is_the_id_and_a_fixed_phrase(monkeypatch):
    monkeypatch.setattr(config, "settings", lambda: {})
    brief = "SENTINELBRIEF 99.5 points fvg"
    with mock.patch("subprocess.Popen") as pop, mock.patch("urllib.request.urlopen") as url:
        for kind in system.ALERTS:
            system.alert(7, kind)
            text = f"Mission 7: {system.ALERTS[kind]}"
            assert text in pop.call_args[0][0][2]
            assert "".join(c for c in text if c.isdigit()) == "7" and "SENTINEL" not in text
        system.alert(7, "stopped")  # not an alert kind: nothing
        assert pop.call_count == len(system.ALERTS)
        url.assert_not_called()


def test_ntfy_posts_only_with_a_topic_and_never_raises(monkeypatch):
    monkeypatch.setattr(config, "settings", lambda: {"ntfy_topic": "tpc"})
    with mock.patch("subprocess.Popen"), mock.patch("urllib.request.urlopen", side_effect=OSError("down")) as url:
        system.alert(3, "crashed")
        req = url.call_args[0][0]
        assert req.full_url == "https://ntfy.sh/tpc" and req.data == b"Mission 3: stopped by an error"


def test_pause_hunt_rewrites_only_the_pause_line(tmp_path, monkeypatch):
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path))
    p = tmp_path / system.STEERING
    p.parent.mkdir(parents=True)
    body = "# steer\nPAUSE: no\nTEST MONTHS: off\nmy direction\n"
    p.write_text(body)
    assert system.hunt_paused() is False
    system.pause_hunt(True)
    assert p.read_text() == body.replace("PAUSE: no", "PAUSE: yes") and system.hunt_paused() is True
    p.unlink()
    assert system.hunt_paused() is None


def test_awake_starts_one_caffeinate_and_stops_it(monkeypatch):
    with mock.patch("subprocess.Popen") as pop, mock.patch("os.kill") as kill:
        pop.return_value.pid = 4242
        system.awake(True)
        system.awake(True)
        assert pop.call_count == 1 and pop.call_args[0][0] == ["caffeinate", "-i", "-s"]
        assert (config.home() / "awake.pid").read_text() == "4242"
        system.awake(False)
        system.awake(False)
        kill.assert_called_once_with(4242, 15)
        assert not (config.home() / "awake.pid").exists()

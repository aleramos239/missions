import re

import pytest

from missions import roles

BLIND = "You will never be shown a test-month number. Do not ask for one and do not guess one."
PAIRS = [(r, s) for r in ("lead", "builder", "doubter", "defender")
         for s in ("brief", "ideas", "build", "argue", "verdict", "owner")]


def test_reply_last_block():
    t = 'a\n```json\n{"a": 1}\n```\nb\n```json\n{"b": 2}\n```\n'
    assert roles.reply(t) == {"b": 2}
    assert roles.say(t) == 'a\n```json\n{"a": 1}\n```\nb'


def test_reply_none():
    assert roles.reply("no block") is None
    assert roles.reply("```json\n{broken\n```") is None


def test_reply_ignores_quoted_earlier_block():
    t = 'tool said:\n```json\n{"x": 1}\n```\nmy words'
    assert roles.reply(t) == {"x": 1}  # only a block is a reply; here the quote is the last one
    assert roles.reply('```json\n{"x": 1}\n```\nmy words\n```json\n{"ok": true}\n```') == {"ok": True}


def test_version_name():
    assert roles.version_name(7, 8) == "m7_v08"


@pytest.mark.parametrize("role,step", PAIRS)
def test_prompt(role, step):
    p = roles.prompt(role, step, brief="B", board="", chat="C", ask="A")
    assert BLIND in p and "Plain, short words" in p
    assert not re.findall(r"\{[A-Za-z_]+\}", p)
    if (role, step) == ("builder", "build"):
        assert '"built"' in p and "wait_s" in p
    if step == "owner":
        assert '"reply"' in p


def test_planted_number_stays_out(tmp_path, monkeypatch):
    from missions import config, digest
    v = tmp_path / "vault"
    d = v / "30-Projects/Onyx-Trading"
    d.mkdir(parents=True)
    (d / "what-lives-what-is-dead-2026-11-07.md").write_text("| x_strat | alive | ok |\n")
    for rel in ("reads/a.json", "refused.jsonl", "read.log", "runs_wf/1/oos"):
        f = config.hb_missions() / "7" / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("test months +9.87 pts 77777")
    (v / "RECENT.md").write_text("alive 77777")
    monkeypatch.setenv("MISSIONS_VAULT", str(v))
    p = roles.prompt("lead", "verdict", brief="b", board="x", chat="c", ask="", digest=digest.digest())
    assert "77777" not in p and "9.87" not in p and "x_strat" in p

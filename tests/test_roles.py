import re

import pytest

from missions import roles

BLIND = "You will never be shown a test-month number. Do not ask for one and do not guess one."
PAIRS = [(r, s) for r in ("lead", "builder", "doubter", "defender")
         for s in ("brief", "ideas", "build", "argue", "verdict", "owner")] + [("lead", "read")]


def test_reply_last_block():
    t = 'a\n```json\n{"a": 1}\n```\nb\n```json\n{"b": 2}\n```\n'
    assert roles.reply(t) == {"b": 2}
    assert roles.say(t) == 'a\n```json\n{"a": 1}\n```\nb'


def test_reply_none():
    assert roles.reply("no block") is None
    assert roles.reply("```json\n{broken\n```") is None


def test_last_block_wins_over_an_earlier_quote():
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


def test_reply_tag_variants():
    assert roles.reply('x\n```JSON\n{"a": 1}\n```') == {"a": 1}
    assert roles.reply('x\r\n```json\r\n{"a": 1}\r\n```\r\n') == {"a": 1}
    assert roles.reply('x\n```json   \n{"a": 1}\n```') == {"a": 1}


def test_read_and_wait():
    p = roles.prompt("lead", "read", brief="b", board="", chat="", ask="held")
    assert '"why"' in p and '"go_on"' not in p and '"stop"' not in p and BLIND in p
    for r in ("builder", "doubter", "defender"):
        with pytest.raises(ValueError):
            roles.prompt(r, "read", brief="", board="", chat="", ask="")
    for r in ("lead", "builder", "doubter", "defender"):
        with pytest.raises(ValueError):
            roles.prompt(r, "wait", brief="", board="", chat="", ask="")


def test_doubter_md_has_every_charge():
    from pathlib import Path
    t = (Path(roles.__file__).parent / "prompts/doubter.md").read_text()
    assert all(c in t for c in roles.CHARGES)


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
    for f in (d / "sibling-notes.md", d / "findings-hub.md", v / "RECENT.md", v / "MEMORY.md",
              d / "MEMORY.md"):
        f.write_text("| leak_strat | alive | 77777 |\n- leak2: dead 77777\n")
    monkeypatch.setenv("MISSIONS_VAULT", str(v))
    dg = digest.digest()
    p = roles.prompt("lead", "verdict", brief="b", board="x", chat="c", ask="", digest=dg)
    for t in (dg, p):
        assert "77777" not in t and "9.87" not in t and "leak" not in t
    assert "x_strat" in p


def test_lead_brief_contract_spells_every_brief_field():
    from missions import briefing
    p = roles.prompt("lead", "brief", brief="b", board="x", chat="", ask="")
    for k in ("goal", "kind", "target", "rule", "idea", "fixed", "may_change", "fewest_trades_week", "notes", "days", *briefing.KINDS):
        assert f'"{k}"' in p

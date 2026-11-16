"""Better results: the Judge's report card (board note, chat, verdict ask, base focus), each version's settings on the board,
the could-not-be-built list (board, wrap-up note), and the digest of the strategy map (names and why, no result numbers)."""
import re
from pathlib import Path

from missions import config, digest, hb as hbmod, store, wrapup
from tests.test_engine import kit, kit3, round_then_stop, run  # noqa: F401
from tests.test_stages import REPORT, prompts, staged
from tests.test_wrapup import ended, run_end, vault_setup

CARD = {"line": "m1_v01: pick 12, +4.2 pts, 2.5/wk, net $29,740; 63/120 boxes green",
        "text": "m1_v01 (NQ 15m), the Judge's read of the in-sample table ...\nThe score picks box 12.", "data": {}}
SPEC = {"run": {"family": "fvg", "exits": "hm40", "params": {"gap_min": [2, 3, 4]}, "fixed": {"side": "with"},
                "filters": [{"vwap": "with"}]}}


def card_for(kit, name=None, c=None):
    name = name or f"m{kit.mid}_v01"
    kit.fake.cards = {name: dict(c or CARD, line=CARD["line"].replace("m1_v01", name))}
    return name


# ---- item 6: the report card


def test_the_card_goes_on_the_board_in_the_chat_once_and_in_the_verdict_ask(kit):  # noqa: F811
    name = card_for(kit)
    run(round_then_stop(kit).run())
    v = store.load(kit.mid)["versions"][0]
    assert v["card_line"].startswith(f"{name}: pick 12")
    assert kit.eng().board()["versions"][0]["note"] == v["card_line"]
    said = [e["text"] for e in store.events(kit.mid) if e["type"] == "chat" and e["who"] == "judge"]
    assert sum(CARD["text"].split("\n")[1] in t for t in said) == 1
    assert f"Judge: {v['card_line']}" in prompts(kit, "lead", "verdict")[0]
    assert [c for c in kit.fake.calls if c[0] == "card"] == [("card", kit.mid, name)]


def test_a_refused_or_down_card_is_skipped_and_the_round_goes_on(kit):  # noqa: F811
    kit.fake.cards = {f"m{kit.mid}_v01": hbmod.Down("no door")}
    assert run(round_then_stop(kit).run()) == "stopped"
    v = store.load(kit.mid)["versions"][0]
    assert "card_line" not in v and v["state"] in ("scored", "cleared", "frozen", "spent")
    assert kit.eng().board()["versions"][0]["note"] is None
    assert ". Judge: " not in prompts(kit, "lead", "verdict")[0]
    run(round_then_stop(kit).run())                                   # no card on file: also skipped (the fake refuses)


def test_hb_card_runs_the_judges_card_command(monkeypatch):
    got = []
    monkeypatch.setattr(hbmod, "door", lambda *a, **k: got.append(a) or CARD)
    assert hbmod.card(3, "m3_v01") == CARD and got == [("card", 3, "m3_v01")]


# ---- item 8: the base report card


def test_the_narrow_focus_carries_the_bases_report_card(kit):  # noqa: F811
    kit.fake.specs[f"m{kit.mid}_v01"] = {"stop": 12}
    card_for(kit)
    run(staged(kit, [{"stage": {"next": "narrow", "base": "v01", "why": "it worked", "report": REPORT}}]).run())
    p = prompts(kit, "doubter", "ideas")[-1]  # the Doubter writes only once there is a score
    assert 'stop\\": 12' in p and "Base report card: " in p and "The score picks box 12." in p


def test_a_focus_on_another_missions_base_asks_that_missions_card(kit3):  # noqa: F811
    eng = kit3.eng()
    kit3.fake.cards = {"m1_v04": CARD}
    eng._base_focus("m1_v04", "v04", "night + morning agree", 1)
    assert ("card", 1, "m1_v04") in kit3.fake.calls
    assert "Base report card: " in eng.m["pending"]["focus"]["text"]
    kit3.fake.cards = {}
    eng._base_focus("m1_v04", "v04", "night + morning agree", 1)  # no card on file: quietly left out
    assert "Base report card" not in eng.m["pending"]["focus"]["text"]


# ---- items 9 and 10: settings and could-not-be-built on the board


def two_planned(kit):
    kit.turns.over[("lead", "ideas")] = lambda t: {"plan": [
        {"version": "v01", "idea": "plan idea", "family": "fvg", "why": "w", "new": "n"},
        {"version": "v02", "idea": "gap with a volume stop", "family": "fvg", "why": "w", "new": "n"},
        {"version": "v03", "idea": "news straddle", "family": "fvg", "why": "w", "new": "n"}]}
    n1 = f"m{kit.mid}_v01"
    kit.fake.specs[n1] = SPEC

    def build(t):
        kit.fake.made_[(kit.mid, n1)] = {"wf": True, "job_id": "j1"}
        return {"built": [{"version": "v01", "name": n1, "job_id": "j1"}],
                "failed": [{"version": "v02", "why": "no volume stop block"}, {"version": "v99", "why": "not planned"}]}
    kit.turns.over[("builder", "build")] = build


def test_settings_and_could_not_be_built_on_the_board(kit):  # noqa: F811
    two_planned(kit)
    run(round_then_stop(kit).run())
    b = kit.eng().board()
    s = b["versions"][0]["settings"]
    assert s == 'family=fvg side=with gap_min=2,3,4 filters=[{"vwap":"with"}]' and len(s) <= 160
    un = [(u["version"], u["idea"], u["why"], u["state"]) for u in kit.eng().m["unbuilt"]]  # one list: what got no table, and why
    assert un == [("v02", "gap with a volume stop", "no volume stop block", "unbuilt"), ("v03", "news straddle", "not on the ledger", "unbuilt")]
    tried = b["tried"]
    assert '{family=fvg side=with gap_min=2,3,4 filters=[{"vwap":"with"}]}' in tried[0]     # the tried line carries the settings
    assert tried[1].endswith("-> build failed: no volume stop block")
    assert [c for c in kit.fake.calls if c == ("idea_spec", f"m{kit.mid}_v01")] == [("idea_spec", f"m{kit.mid}_v01")]


def test_settings_are_cut_at_160_and_empty_without_a_spec(kit):  # noqa: F811
    from missions import engine
    assert engine._settings_text(None) == "" and engine._settings_text({"card": {}}) == ""
    assert len(engine._settings_text({"run": {"family": "x", "fixed": {f"k{i}": "v" * 20 for i in range(20)}}})) == 160


def test_the_tried_line_carries_the_judges_read(kit):  # noqa: F811
    eng = kit.eng()
    eng.m["versions"] = [{"version": "v01", "name": "m1_v01", "family": "f", "state": "dropped", "idea": "an idea", "why": "no box picked",
                          "card_line": "m1_v01: no pick (under 2 a week); best +6.0 pts, 1.2/wk; 16/24 boxes green"}]
    assert eng.board()["tried"] == ["v01 (stage 1) [f] an idea -> dropped: no pick (under 2 a week); best +6.0 pts, 1.2/wk; 16/24 boxes green"]


def test_the_prompts_tell_the_team_to_read_the_board_and_skip_what_cannot_be_built():
    t = (Path(__file__).parent.parent / "missions/prompts/common.md").read_text()
    assert "`tried`" in t and "settings in braces" in t and "`Judge:`" in t and "build failed or not started" in t


def test_the_wrapup_note_lists_missing_blocks():
    vault_setup()
    mid = ended()
    m = store.load(mid)
    m["unbuilt"] = [{"version": "v02", "name": "m1_v02", "idea": "gap with a volume stop", "family": "fvg", "state": "unbuilt",
                     "why": "no volume stop block", "round": 1, "stage": 1}]
    store.save(m)
    run_end(mid)
    note = next((config.vault() / "30-Projects/Onyx-Trading/Missions").glob("*.md")).read_text()
    assert "## Could not be built or started\n\n- gap with a volume stop (fvg): no volume stop block, round 1" in note
    assert note.index("## What was tried") < note.index("## Could not be built or started") < note.index("**Cost.**")


# ---- item 5: the digest

REAL = """## Still alive

### A. Test months unread: the next step waits on the owner's word

| Idea | Note | Trades/wk | Stop / target | In-sample | Next blueprint step |
|---|---|---|---|---|---|
| ATR open band, held to the close | [[2026-11-07-nq-atr-open-band-hold-to-close]] | 2.5 | out at the open level or 15:58 | 471 trades, Sharpe 2.71, 6 of 6 years | The owner's word |
| Midday trend pullback: 5m dip against EMA50, 11:00-13:30 | [[2026-11-05-nq-5m-wick-break]] | 6.4 | 2 ATR (~59 pts), 1:3 | +$226k, 5 of 6 years (2023 −$20.5k) | Idea card |

### C. Thin or doubtful (under 2 a week, or a cousin failed): watch, do not build on

- **Morning displacement against EMA100 (A/B/C): DEAD 2026-11-12.** In-sample +3.6 to +6.3 over break-even at 1:1.5. [[nq-disp]]
- **Others under 2 a week:**
  - FVG 15m oside: [[fvg-odir-owner-idea-2026-10-19]]

## Dead: do not retest

| Family | Why it failed | Link |
|---|---|---|
| 9:30 one-side stop / pick the side before 9:30 | The side is a coin flip; nothing before 9:30 picks it. The "with overnight" side does worse than random | [[2026-11-06-nq-930-one-side-stop]] |
| 9:30 straddle, tight or near stops (5-25 pts), vol-sized, busy-day filters | Tight brackets die of costs. On ticks, 2021-24 was a losing coin flip (24.7% win vs 25% need). Vol-sizing was no better than fixed points | [[2026-10-07-nq-930]] |
| VWAP band fades (3σ, 3.25σ ATR, touch) | Coin flip minus costs. +$62.9k in-sample became −$44.3k on the test read | [[2026-10-11-nq-vwap-fade]] |

## Patterns

- **Follows, not fades.** Every fade family died (VWAP band, fair price, sweeps, poke, absorption).
- **Evening, London and Asia are dead.** About 90 ideas and 6 markets.
"""


def digest_of(tmp_path, monkeypatch, text):
    d = tmp_path / "v/30-Projects/Onyx-Trading"
    d.mkdir(parents=True)
    (d / "what-lives-what-is-dead-2026-11-07.md").write_text(text)
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "v"))
    return digest.digest()


def test_the_digest_keeps_full_names_and_the_dead_rows_why(tmp_path, monkeypatch):
    t = digest_of(tmp_path, monkeypatch, REAL)
    body = t.split("The owner's standing rules")[0]
    assert ("- 9:30 one-side stop / pick the side before 9:30: dead. Why: The side is a coin flip; nothing before 9:30 picks it. "
            'The "with overnight" side does worse than random') in body
    assert "- 9:30 straddle, tight or near stops, vol-sized, busy-day filters: dead. Why: Tight brackets die of costs. " \
           "Vol-sizing was no better than fixed points" in body
    assert "- VWAP band fades: dead. Why: Coin flip minus costs." in body
    assert "- Morning displacement against EMA100 (A/B/C): dead" in body
    assert "- ATR open band, held to the close: alive" in body
    assert "- Midday trend pullback: 5m dip against EMA50, 11:00-13:30: alive" in body
    assert "- FVG 15m oside: thin" in body and "Others under" not in body
    assert "- Follows, not fades" in body and "- Evening, London and Asia are dead\n" in body
    assert body.index("Dead, do not retest:") < body.index("Alive or watched:") < body.index("Lessons:")
    assert t.endswith(digest.RULES)


def test_the_digest_has_no_result_number_and_no_header_entry(tmp_path, monkeypatch):
    body = digest_of(tmp_path, monkeypatch, REAL).split("The owner's standing rules")[0]
    assert "$" not in body and "%" not in body and "[[" not in body and "**" not in body
    left = re.sub(r"\b\d{1,2}:\d{2}\b|\b\d+[smh]\b|\bEMA\d+\b", "", body)
    assert not re.search(r"\d", left), left
    for head in ("- Idea", "- Family", "- Note", "Why it failed:"):
        assert head not in body


def test_the_digest_is_capped(tmp_path, monkeypatch):
    rows = "\n".join(f"| dead family number{'x' * (i % 7)} {chr(65 + i % 26)}{i // 26} | a reason that is long enough | [[l]] |" for i in range(400))
    t = digest_of(tmp_path, monkeypatch, "## Dead\n\n| Family | Why | Link |\n|---|---|---|\n" + rows + "\n")
    assert len(t.split("\n\nThe owner's")[0]) <= digest.CAP

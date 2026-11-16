import json
import re
from pathlib import Path

CHARGES = ("One year carries it", "Worse fills kill it", "It looks ahead", "One side carries it",
           "It is a dead family again")
_BLOCK = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n[ \t]*```", re.S | re.I)
_IDEAS = ('{"ideas": [{"idea": "...", "family": "<a family blueprint_blocks lists>", "why": "..."}]} '
          "(at most 3)")
_C = {
    ("lead", "brief"): ('{"ask": {"q": "...", "options": ["...", "..."]}} to ask the owner one thing, '
                        'or, when the brief is ready, exactly this shape: {"brief": {"goal": {"kind": "eval" | "points" | '
                        '"net" | "years", "target": 0.5, "rule": "<an account id from the board, eval only>", "days": 10}, "idea": "...", '
                        '"exits": "hm40", "target_r": 2, "base": {"mission": 3, "version": "v23"}, "fixed": ["..."], "may_change": ["..."], "fewest_trades_week": 2, "notes": "..."}} '
                        '(target_r: optional, the R target the goal is about, one of 0.5, 0.75, 1, 1.5, 2 (2 for a 1:2 goal); base: optional, only to start already narrowed on a version of an earlier mission, {"mission": <id>, "version": "vNN"}; exits: hm40 default; hm60 adds fixed-point stops 15/25/40/60 pts, only when the owner asks for fixed points; an eval target is a share 0-1; points and net targets are numbers above 0; days: eval only, the weekdays the eval must pass within (default 10); '
                        'years: {"kind": "years", "recent": [2025, 2026], "win_min": 0.40, "rest": "green"}: recent years\' full-target win rate at least win_min, every other year net above 0, no target)'),
    ("builder", "ideas"): _IDEAS, ("doubter", "ideas"): _IDEAS.replace("3", "1"),
    ("defender", "ideas"): _IDEAS.replace("3", "2"),
    ("lead", "ideas"): ('{"plan": [{"version": "v08", "idea": "...", "family": "...", "why": "...", '
                        '"new": "<one line: how it differs from everything in the tried list>"}]} '
                        "(at most 3 a round; new is required: an item without it, or the same idea and family as a "
                        "version already tried, is refused. Never plan a closed branch)"),
    ("builder", "build"): ('{"built": [{"version": "v08", "name": "m7_v08"}], '
                           '"failed": [{"version": "v09", "why": "..."}]}'),
    ("doubter", "argue"): '{"claims": [{"version": "v08", "charge": "<one of the five charges>", "say": "..."}]}',
    ("defender", "argue"): ('{"answers": [{"version": "v08", "charge": "...", "say": "..."}], '
                            '"fixes": [{"idea": "...", "family": "...", "why": "..."}]}'),
    ("lead", "verdict"): ('{"to_owner": "<two plain sentences: what happened and what you decided>", '
                          '"next": "<your orders for the next round: what the team tries>", '
                          '"close": [{"what": "<the exact combination, e.g. first-candle check on top of v23>", '
                          '"reason": "...", "versions": ["v07", "v08"]}], "reopen": ["<what>"], "end_stage": true} '
                          "(close, reopen and end_stage are optional. close: a branch of THIS mission that keeps failing; "
                          "it needs at least 2 versions of this mission that were dropped or failed, or it is refused. "
                          "reopen: a closed what that is worth trying again, e.g. the base idea changed. "
                          "end_stage: true ends this stage now, its unused tries are not kept; the stage review comes next. "
                          "No question to the owner: decide yourself)"),
}
_C[("lead", "stage")] = ('{"stage": {"next": "narrow" | "fresh" | "stop", "base": "v23", "why": "...", "report": "..."}} '
                         "(narrow: the next stage works only on variations of one scored version, base is required and must be one "
                         "of the scored versions; fresh: the next stage starts from new ideas, no base; stop: the mission ends; "
                         "why: two plain sentences for the owner; report: the full report of this stage, plain words, short sections: what was "
                         "tried (each version, one line), what worked and the numbers, what failed and why, what the next stage should "
                         "try and what to avoid; at least 200 characters. The whole team reads it at the start of the next stage)")
_C[("lead", "read")] = ('{"why": "..."} (plain words first, say what the Judge\'s one-line answer means '
                        "and what the next round tries: the team reads it as your orders. You cannot stop the mission. "
                        "No question to the owner: decide yourself)")
_OWNER = '{"reply": "..."}'
_STEPS = {"brief": "Write the brief with the owner.",
          "ideas": ("Step: ideas. Write your angles alone. Read the board's tried list first: never propose a version "
                    "already tried, nor anything on the closed list."),
          "build": "Step: build. Write the cards of the planned versions. The app starts their tables.",
          "stage": ("Step: stage review. This stage is over: its tries are used, or it was ended early. Stop, look at everything: what worked, what did not. "
                    "If nothing worked, the next stage restarts from zero with fresh ideas. If one idea worked, the next stage works "
                    "only on that idea. Or stop the mission. You also write the stage report: the whole team reads it at the start of the next stage and works off it."),
          "argue": "Step: argue.",
          "verdict": ("Step: verdict. Sum up the round. Read the tried list: if the team keeps rebuilding the same thing, "
                      "close that branch, give new orders, or end the stage."),
          "read": "Step: read. The Judge answered in one line (held, which line, or close). Say what comes next.",
          "owner": "The owner wrote to you. Answer him."}
_IDEA_JOB = {
    "builder": ("Your job: ideas the blocks can build that are not already on the board. For each, say the family and "
                "the settings that matter. At most 3."),
    "doubter": ("Your job: ONE idea only: the control or stripped-down test that would show whether the best result so "
                "far is real. Drop one rule, flip the side, take the side by a coin flip, or run the same rule with no filter."),
    "defender": ("Your job: say in one line why the best version's edge exists and who loses to it. Then at most TWO "
                 "variations that should do better if that reason is true."),
}


def _read(name):
    return (Path(__file__).parent / "prompts" / f"{name}.md").read_text().strip()


def prompt(role, step, *, brief, board, chat, ask, digest=None) -> str:
    if role not in ("lead", "builder", "doubter", "defender") or step not in _STEPS:
        raise ValueError(f"bad role or step: {role} {step}")
    if step in ("read", "stage") and role != "lead":
        raise ValueError(f"only the lead speaks at {step}: {role}")
    contract = _OWNER if step == "owner" else _C.get((role, step))
    if role == "lead" and step == "owner":
        contract += ' (the Lead may add "plan_change": "...")'
    contract = contract or "Nothing is asked of you at this step. Reply with plain words only."
    text = f"{_STEPS[step]} {_IDEA_JOB[role]}" if step == "ideas" and role in _IDEA_JOB else _STEPS[step]
    parts = [_read("common"), _read(role), f"# Step\n\n{text}\n\nEnd with this json block: {contract}"]
    if digest:
        parts.append(f"# What lives and what is dead\n\n{digest}")
    for title, body in (("The brief", brief), ("The board", board), ("The chat", chat), ("Asked of you", ask)):
        if body:
            parts.append(f"# {title}\n\n{body if isinstance(body, str) else json.dumps(body, indent=1)}")
    return "\n\n".join(parts)


def _last(text):
    return list(_BLOCK.finditer(text or ""))[-1:]


def reply(text):
    for m in _last(text):
        try:
            v = json.loads(m.group(1))
        except ValueError:
            return None
        return v if isinstance(v, dict) else None
    return None


def say(text):
    for m in _last(text):
        return (text[:m.start()] + text[m.end():]).strip()
    return (text or "").strip()


def version_name(mid, n) -> str:
    return f"m{mid}_v{int(n):02d}"

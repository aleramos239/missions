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
                        '"exits": "hm40", "fixed": ["..."], "may_change": ["..."], "fewest_trades_week": 2, "notes": "..."}} '
                        '(exits: hm40 default; hm60 adds fixed-point stops 15/25/40/60 pts, only when the owner asks for fixed points; an eval target is a share 0-1; points and net targets are numbers above 0; days: eval only, the weekdays the eval must pass within (default 10); '
                        'years: {"kind": "years", "recent": [2025, 2026], "win_min": 0.40, "rest": "green"}: recent years\' full-target win rate at least win_min, every other year net above 0, no target)'),
    ("builder", "ideas"): _IDEAS, ("doubter", "ideas"): _IDEAS, ("defender", "ideas"): _IDEAS,
    ("lead", "ideas"): ('{"plan": [{"version": "v08", "idea": "...", "family": "...", "why": "..."}]} '
                        "(at most 3 a round)"),
    ("builder", "build"): ('{"built": [{"version": "v08", "name": "m7_v08", "job_id": "..."}], '
                           '"failed": [{"version": "v09", "why": "..."}]}'),
    ("doubter", "argue"): '{"claims": [{"version": "v08", "charge": "<one of the five charges>", "say": "..."}]}',
    ("defender", "argue"): ('{"answers": [{"version": "v08", "charge": "...", "say": "..."}], '
                            '"fixes": [{"idea": "...", "family": "...", "why": "..."}]}'),
    ("lead", "verdict"): '{"to_owner": "<two plain sentences>", "next": "<what the next round tries>"}',
}
_C[("lead", "read")] = ('{"why": "..."} (advice only: plain words first, say what the Judge\'s one-line answer means '
                        "and what the next round could try. You cannot stop the mission)")
_OWNER = '{"reply": "..."}'
_STEPS = {"brief": "Write the brief with the owner.", "ideas": "Step: ideas. Write your angles alone.",
          "build": "Step: build. Make the planned versions and start their tables.",
          "argue": "Step: argue.", "verdict": "Step: verdict. Sum up the round.",
          "read": "Step: read. The Judge answered in one line (held, which line, or close). Say what comes next.",
          "owner": "The owner wrote to you. Answer him."}


def _read(name):
    return (Path(__file__).parent / "prompts" / f"{name}.md").read_text().strip()


def prompt(role, step, *, brief, board, chat, ask, digest=None) -> str:
    if role not in ("lead", "builder", "doubter", "defender") or step not in _STEPS:
        raise ValueError(f"bad role or step: {role} {step}")
    if step == "read" and role != "lead":
        raise ValueError(f"only the lead speaks at read: {role}")
    contract = _OWNER if step == "owner" else _C.get((role, step))
    if role == "lead" and step == "owner":
        contract += ' (the Lead may add "plan_change": "...")'
    contract = contract or "Nothing is asked of you at this step. Reply with plain words only."
    parts = [_read("common"), _read(role), f"# Step\n\n{_STEPS[step]}\n\nEnd with this json block: {contract}"]
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

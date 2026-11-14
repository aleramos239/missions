"""When a mission ends: the owner's vault note, the RECENT.md line, the strategy-map line. Owner-side only: nothing here
reads reads/*.json, refused.jsonl or read.log; the test-month line is the one the team heard (m["versions"][i]["heard"])."""
import re
from datetime import date
from pathlib import Path

from . import config

RESULT = {"achieved": "reached", "limit": "a limit ran out", "out_of_reach": "out of reach", "stopped": "stopped"}
MAP_WORD = {"achieved": "reached", "out_of_reach": "out of reach"}  # limit and stopped read "not reached"
MAP_FILE = "what-lives-what-is-dead-2026-11-07.md"


def _onyx():
    return config.vault() / "30-Projects/Onyx-Trading"


def _name(m):
    return f"{m['id']}-{re.sub(r'[^a-z0-9]+', '-', m['title'].lower()).strip('-') or 'mission'}"


def _best(m, board):
    return next((v for v in board["versions"] if v["version"] == board.get("best")), None)


def note(m, board) -> Path:
    p = _onyx() / "Missions" / f"{_name(m)}.md"
    g = board["goal"]
    best, tr = _best(m, board), board["tries"]
    word = RESULT.get(m["status"], m["status"])
    L = ["---", f"name: {_name(m)}", f"description: Mission {m['id']} ({m['title']}): {word}",
         "metadata:", "  type: mission", f"created: {date.today()}", "tags: [homebase, missions]", "---", "",
         f"# Mission {m['id']}: {m['title']}", "", f"**Goal.** {m['sentence']} ({g.get('kind')}, target {g.get('target')}"
         + (f", {g['rule']}" if g.get("rule") else "") + ")", "", f"**Result.** {word.capitalize()}.", ""]
    if best:
        L += [f"**Best version.** {best['name']} ({best['family']}), box {best['box']}, goal value {best['goal_value']}.", ""]
    L += [f"**Tries.** {tr.get('mission')} this mission, {tr.get('total')} in all. Rounds: {m['round']}. "
          f"Test-month reads: {m['reads']}.", "", "## What was tried", ""]
    for v, full in zip(board["versions"], m["versions"]):
        s = f"- {v['name']} ({v['family']}): {v['state']}"
        if full.get("why"):
            s += f", dropped because {full['why']}"
        if v["lines_failed"]:
            s += f"; lines failed: {', '.join(v['lines_failed'])}"
        h = v.get("heard")
        if h:
            s += f"; test months: {'held' if h.get('held') else 'broke'}, {h.get('line') or 'no line'}"
        L.append(s)
    L += ["", f"**Cost.** ${m.get('cost_usd', 0):.2f}, {int(m.get('run_seconds', 0)) // 60} minutes of work.", "",
          "Related: [[missions-app-owner-decisions-2026-11-14]], [[what-lives-what-is-dead-2026-11-07]]", ""]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L))
    return p


def recent_line(m) -> str:
    return (f"- {date.today()} · code · Mission {m['id']} ({m['title']}): {RESULT.get(m['status'], m['status'])}"
            f" · [[{_name(m)}]]")


def _insert_top(path, line, key):
    """Line at the top of RECENT's list (before its first '- ' line); the rest stays byte for byte."""
    txt = path.read_text() if path.exists() else ""
    if f"[[{key}]]" in txt:
        return
    mm = re.search(r"^- ", txt, re.M)
    i = mm.start() if mm else len(txt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt[:i] + line + "\n" + txt[i:])


def write(m, board) -> None:
    note(m, board)
    _insert_top(config.vault() / "RECENT.md", recent_line(m), _name(m))
    p = _onyx() / MAP_FILE
    txt = p.read_text() if p.exists() else ""
    if f"[[{_name(m)}]]" in txt:
        return
    fam = (_best(m, board) or {}).get("family") or "none"
    line = f"- {date.today()} · {fam} · {MAP_WORD.get(m['status'], 'not reached')} · [[{_name(m)}]]\n"
    if not re.search(r"^## Missions\s*$", txt, re.M):
        txt = txt.rstrip("\n") + "\n\n## Missions\n\n" if txt else "## Missions\n\n"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt + line)


def mark_dead(family, why, said) -> None:
    if not (said or "").strip() or not (family or "").strip():
        raise ValueError("family and his words are needed")
    clean = lambda s: " ".join(str(s).replace("|", "/").split())
    p = _onyx() / "dead-families.md"
    lines = p.read_text().split("\n")
    row = f"| {clean(family)} | dead | {date.today()} | {clean(why)} (owner: \"{clean(said)}\") |"
    last = max((i for i, l in enumerate(lines) if l.startswith("|")), default=None)
    if last is None:
        lines += ["", "| family | verdict | date | why |", "|---|---|---|---|", row]
    else:
        lines.insert(last + 1, row)
    p.write_text("\n".join(lines))

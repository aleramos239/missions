"""When a mission ends: the owner's vault note, the RECENT.md line, the strategy-map line. Owner-side only: nothing here
reads reads/*.json, refused.jsonl or read.log; the test-month line is the one the team heard (m["versions"][i]["heard"])."""
import os
import re
from datetime import date
from pathlib import Path

from . import config
import json

RESULT = {"achieved": "reached", "limit": "a limit ran out", "out_of_reach": "out of reach", "stopped": "stopped"}
MAP_WORD = {"achieved": "reached", "out_of_reach": "out of reach"}  # limit and stopped read "not reached"
MAP_FILE = "what-lives-what-is-dead-2026-11-07.md"


def _edit(path, fn):
    """Re-read the file now, apply fn(text) -> new text (None = no change), write a temp file beside it, then replace.
    Other chats and the desktop app write the same files; a failed write leaves the original whole."""
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = path.read_text() if path.exists() else ""
    new = fn(txt)
    if new is None or new == txt:
        return
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(new)
    os.replace(tmp, path)


def _title(m):
    return " ".join(m["title"].split())


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
    L = ["---", f"name: {_name(m)}", "description: " + json.dumps(f"Mission {m['id']} ({_title(m)}): {word}"),
         "metadata:", "  type: mission", f"created: {date.today()}", "tags: [homebase, missions]", "---", "",
         f"# Mission {m['id']}: {_title(m)}", "", f"**Goal.** {' '.join(m['sentence'].split())} ({g.get('kind')}, target {g.get('target')}"
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
    if cb := m.get("unbuilt"):
        L += ["", "## Could not be built or started", ""] + [f"- {c['idea']} ({c.get('family')}): {c.get('why')}, round {c.get('round')}" for c in cb]
    L += ["", f"**Cost.** ${m.get('cost_usd', 0):.2f}, {int(m.get('run_seconds', 0)) // 60} minutes of work.", "",
          "Related: [[missions-app-owner-decisions-2026-11-14]], [[what-lives-what-is-dead-2026-11-07]]", ""]
    _edit(p, lambda _: "\n".join(L))
    return p


def recent_line(m) -> str:
    return (f"- {date.today()} · code · Mission {m['id']} ({_title(m)}): {RESULT.get(m['status'], m['status'])}"
            f" · [[{_name(m)}]]")


def _insert_top(path, line, key):
    """Line at the top of RECENT's list: after the frontmatter, before the first '- ' line; the rest stays byte for byte."""
    def fn(txt):
        if f"[[{key}]]" in txt:
            return None
        start = 0
        if txt.startswith("---\n") and (e := txt.find("\n---\n", 3)) != -1:
            start = e + 5
        mm = re.compile(r"^- ", re.M).search(txt, start)
        i = mm.start() if mm else len(txt)
        pre = txt[:i] + ("\n" if txt[:i] and not txt[:i].endswith("\n") else "")
        return pre + line + "\n" + txt[i:]
    _edit(path, fn)


def _map_add(txt, line, key):
    if f"[[{key}]]" in txt:
        return None
    mm = re.search(r"^## Missions[ \t]*$", txt, re.M)
    if not mm:
        return txt.rstrip("\n") + ("\n\n" if txt else "") + "## Missions\n\n" + line + "\n"
    nxt = re.compile(r"^## ", re.M).search(txt, mm.end())
    i = nxt.start() if nxt else len(txt)
    head = txt[:i].rstrip("\n") + "\n" + line + "\n"
    return head + ("\n" + txt[i:] if nxt else "")


def write(m, board) -> None:
    note(m, board)
    _insert_top(config.vault() / "RECENT.md", recent_line(m), _name(m))
    fam = (_best(m, board) or {}).get("family") or "none"
    line = f"- {date.today()} · {fam} · {MAP_WORD.get(m['status'], 'not reached')} · [[{_name(m)}]]"
    _edit(_onyx() / MAP_FILE, lambda t: _map_add(t, line, _name(m)))


def mark_dead(family, why, said) -> None:
    if not all(isinstance(x, str) for x in (family, why, said)) or not said.strip() or not family.strip():
        raise ValueError("family and his words are needed")
    clean = lambda s: " ".join(str(s).replace("|", "/").split())
    p = _onyx() / "dead-families.md"
    if not p.exists():
        raise ValueError("dead-families.md is not in the vault")

    def fn(txt):
        lines = txt.split("\n")
        if any(l.startswith("|") and l.strip("| ").split("|")[0].strip() == clean(family) for l in lines):
            return None  # already a row
        row = f"| {clean(family)} | dead | {date.today()} | {clean(why)} (owner: \"{clean(said)}\") |"
        last = max((i for i, l in enumerate(lines) if l.startswith("|")), default=None)
        if last is None:
            lines.extend(["", "| family | verdict | date | why |", "|---|---|---|---|", row])
        else:
            lines.insert(last + 1, row)
        return "\n".join(lines)
    _edit(p, fn)

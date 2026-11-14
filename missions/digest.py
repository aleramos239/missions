import re
from pathlib import Path

from . import config

VERDICTS = ("dead", "alive", "held", "failed", "parked", "weak", "strong")
_FILES = ("what-lives-what-is-dead-2026-11-07.md", "dead-families.md")
_V = re.compile(r"\b(" + "|".join(VERDICTS) + r")\b", re.I)
RULES = """The owner's standing rules:
- NQ only. The heat map is hm40; judge the average box, never the best.
- Fewer rules beat more. An edge must make sense.
- 2 to 3 trades a week or more.
- Test months are the Judge's alone."""


def _name(line):
    s = line.strip()
    if s.startswith("|"):
        s = s.strip("|").split("|")[0]
    elif re.match(r"[-*] ", s):
        s = s[2:]
    else:
        return ""  # headings and prose never count
    s = re.sub(r"[\[\]`*]", "", s).strip()
    m = re.match(r"[A-Za-z][\w.\-]*", s)
    return m.group(0) if m else ""


def _safe(base, f):
    p = base / f
    if p.is_symlink():
        return None
    r = p.resolve()
    return r if r.parent == base.resolve() else None


def digest() -> str:
    out = []
    base = config.vault() / "30-Projects/Onyx-Trading"
    for f in _FILES:
        try:
            lines = (_safe(base, f) or Path("/nonexistent")).read_text().splitlines()
        except OSError:
            continue
        for ln in lines:
            m = _V.search(ln)
            if m and (n := _name(ln)) and not _V.fullmatch(n):
                out.append(f"- {n}: {m.group(1).lower()}")
    body = "\n".join(out) if out else "No notes found: the dead list and the strategy map could not be read."
    return f"{body}\n\n{RULES}"

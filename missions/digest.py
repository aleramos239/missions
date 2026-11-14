import re

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
    else:
        s = re.sub(r"^[-*\d.\s]+", "", s)
    s = re.sub(r"[\[\]`*]", "", s).strip()
    return re.split(r"[\s:|(]", s, 1)[0].strip("-—") if s else ""


def digest() -> str:
    out = []
    base = config.vault() / "30-Projects/Onyx-Trading"
    for f in _FILES:
        try:
            lines = (base / f).read_text().splitlines()
        except OSError:
            continue
        for ln in lines:
            m = _V.search(ln)
            if m and (n := _name(ln)) and not _V.fullmatch(n):
                out.append(f"- {n}: {m.group(1).lower()}")
    body = "\n".join(out) if out else "No notes found: the dead list and the strategy map could not be read."
    return f"{body}\n\n{RULES}"

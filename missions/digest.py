import re
from pathlib import Path

from . import config

VERDICTS = ("dead", "alive", "held", "failed", "parked", "weak", "strong", "thin")
_FILES = ("what-lives-what-is-dead-2026-11-07.md", "dead-families.md")
_V = re.compile(r"\b(" + "|".join(VERDICTS) + r")\b", re.I)
CAP = 6000
RULES = """The owner's standing rules:
- NQ only. The heat map is hm40; judge the average box, never the best.
- Fewer rules beat more. An edge must make sense.
- 2 to 3 trades a week or more.
- Test months are the Judge's alone."""

# Kept: clock times (9:30, 09:30-11:00), R:R (1:2, 1:0.75) and timeframes (15m, 30s, 1h). Every other number is a result and goes.
_KEEP = re.compile(r"(?<![\w.])(?:\d{1,2}:\d{1,2}(?:\.\d+)?|\d+[smh])(?![\w.])|\bLevel [23]\b")
_UNIT = r"(?:\s?(?:%|k\b|x\b|×|σ|pts?\b|points?\b|trades?\b|boxes\b|cells\b|years?\b|ideas\b|markets\b|accounts\b|picks\b|seeds?\b|min\b|s\b|seconds?\b|R\b))?"
_NUM = re.compile(r"[−+\-]?\$?(?<![\w.])\d[\d,.\-–/]*" + _UNIT)


def _clean(s):
    """Text with links, bold and code marks gone and every result number taken out."""
    s = re.sub(r"\[\[([^\]|]*)(?:\|[^\]]*)?\]\]", r"\1", s)
    s = re.sub(r"[`*]", "", s)
    kept = []
    s = _KEEP.sub(lambda m: kept.append(m.group(0)) or chr(0xE000 + len(kept) - 1), s)    # a mark the number pass cannot match
    s = re.sub(r"\([^()]*\d[^()]*\)", "", s)                     # a bracket holding a result number goes whole
    s = _NUM.sub("", s)
    s = re.sub("[\ue000-\uefff]", lambda m: kept[ord(m.group(0)) - 0xE000], s)
    for a, b in ((r"(?<!\S)#(?!\w)", ""), (r"\(\s*[,;]?\s*\)", ""), (r"\s+([,.;:)])", r"\1"), (r"\(\s+", "("), (r"([,;])(?:\s*[,;])+", r"\1"),
                 (r"\s{2,}", " "), (r"^[\s,.;:<>=~/-]+|[\s,;:<>=~/-]+$", "")):
        s = re.sub(a, b, s)
    return s.strip()


def _reason(cells):
    """The why of a dead row: its first cell after the name with words in it, sentences that held a number left out."""
    for c in cells[1:]:
        c = re.sub(r"\[\[[^\]]*\]\]", "", c).strip(" ·")
        if not c or _V.fullmatch(c.strip("* ")):
            continue
        parts = [p for p in re.split(r"(?<=[.;])\s+", c) if not _NUM.search(_KEEP.sub("", re.sub(r"\[\[[^\]]*\]\]", "", p)))]
        why = _clean(" ".join(parts)) if parts else ""
        if why:
            return why[:200]
    return ""


def _bullet_name(s):
    b = re.match(r"\*\*(.+?)\*\*", s)
    n = b.group(1) if b else re.split(r":\s|\s\[\[", s, maxsplit=1)[0]
    return None if n.rstrip().endswith(":") else n.rstrip(" .")


def _section(head, parent):
    h = head.lower()
    for k, v in (("dead", "dead"), ("thin", "thin"), ("doubtful", "thin"), ("held", "held"), ("alive", "alive")):
        if k in h:
            return v
    if "pattern" in h or "lesson" in h:
        return "lesson"
    return parent


def _entries(lines):
    """(verdict, name, why) of each table row and bullet that has a verdict word or sits under a verdict heading."""
    sec = sub = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("#"):
            lvl, head = len(s) - len(s.lstrip("#")), s.lstrip("#")
            if lvl <= 2:
                sec = sub = _section(head, None)
            else:
                sub = _section(head, sec)
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if re.fullmatch(r"[|\s:\-]+", s) or re.fullmatch(r"\|[\s:\-|]+\|?", nxt):
                continue                                          # a separator, or the header row above one
            raw = cells[0]
        elif re.match(r"[-*] ", s):
            raw, cells = _bullet_name(s[2:]), []
            if raw is None:
                continue
        else:
            continue                                              # headings and prose never count
        word = _V.search(re.sub(r"\[\[[^\]]*\]\]", "", s))
        dead = word and word.group(1).lower() == "dead" and sub != "lesson"
        verdict = "dead" if dead else sub or (word and word.group(1).lower())
        if not verdict:
            continue
        name = re.sub(r"\s*:\s*(?:" + "|".join(VERDICTS) + r")\b.*$", "", _clean(raw), flags=re.I) if sub != "lesson" else _clean(raw)
        if not name or _V.fullmatch(name):
            continue
        yield verdict, name[:160], (_reason(cells) if verdict == "dead" and cells else "")


def _safe(root, rel, f):
    p = root
    for part in (*Path(rel).parts, f):
        p = p / part
        if p.is_symlink():  # the vault root itself may be a link; nothing below it may
            return None
    r = p.resolve()
    return r if r.is_relative_to(root.resolve() / rel) else None


def digest() -> str:
    got = []
    root, rel = config.vault(), "30-Projects/Onyx-Trading"
    for f in _FILES:
        try:
            lines = (_safe(root, rel, f) or Path("/nonexistent")).read_text().splitlines()
        except OSError:
            continue
        got += [e for e in _entries(lines) if e not in got]
    dead = [f"- {n}: dead" + (f". Why: {w}" if w else "") for v, n, w in got if v == "dead"]
    live = [f"- {n}: {v}" for v, n, _ in got if v not in ("dead", "lesson")]
    lessons = [f"- {n}" for v, n, _ in got if v == "lesson"]
    out, size = [], 0
    for head, rows in (("Dead, do not retest:", dead), ("Alive or watched:", live), ("Lessons:", lessons)):
        for r in ([head] + rows) if rows else []:
            if size + len(r) + 1 > CAP:
                break
            out.append(r)
            size += len(r) + 1
    body = "\n".join(out) if out else "No notes found: the dead list and the strategy map could not be read."
    return f"{body}\n\n{RULES}"

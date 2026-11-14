# Plan 3: the shelf

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a mission's Builder (and any Claude chat) write a new toolkit piece, test it safely, and save it on a shelf
where every later mission and chat can build from it; the owner is told, and his yes commits it into Homebase.

**Architecture:** The shelf is a folder with its own git history, `~/.homebase/shelf/`, never inside the Homebase repo.
A piece is one folder: code, a card, its own test, the gate's result. Three fences keep a piece from reading what the
Judge hides or touching the repo: (1) a static check of what it imports, (2) a runtime audit hook that refuses any file,
network or process call made from piece code, and (3) an OS sandbox (`sandbox-exec`) around every toolkit run that loads
a piece. The toolkit loads listed pieces through one new module, `engine/families/zshelf.py`, and only inside the
sandbox; outside it the toolkit lists pieces from their cards without running their code. The gate is code
(`blueprint/shelfgate.py`): seven checks, pass or fail, never a profit or loss. The connector gets five tools. The
Missions app shows new pieces and takes his yes.

**Tech Stack:** Python (`.venv-research` for the toolkit and the gate, `.venv` for `homebase/`), macOS `sandbox-exec`,
pytest, git. In `~/missions`: the Plan 2 app.

**Spec:** `~/missions/docs/specs/2026-11-14-missions-design.md` (approved 2026-11-14), section 7, and sections 4, 5 (the
look-ahead charge), 9 ("Right after (the shelf)").

**How this plan is run (owner, 2026-11-14):** the planner (Fable 5.2) wrote this from a read of the real files; Opus 5.5
subagents build it task by task. Where the plan's code disagrees with the real code, **the real code wins**: fit the
plan's code to it, keep the behaviour the tests pin, and say what you changed. Never weaken a test to make it pass.

**Needs:** Plan 1 (Homebase main b39f9b6f) and Plan 2 (`feat/missions-door` merged; the app built) for Tasks 9 and 10.
Tasks 1-8 need only Plan 1.

## Facts this plan stands on (checked 2026-11-14, Homebase main)

- **The registry.** `engine/families/__init__.py` `load()` scans only its own folder with `pkgutil.iter_modules`, sorted
  by name, skipping names that start with `_`; it runs at import. A module must define `FAMILIES = {name: (Class, inputs,
  both_sides, notes[, LIB])}`; `load()` refuses a class whose `__module__` is not `families.<mod>`; an import error or a
  bad entry goes to `ERRORS`, and `run_menus.registry()` raises `RegistryBroken` for **everyone** while `ERRORS` is not
  empty. After the scan `load()` calls `_flex.apply()` and `_flat.apply()`, which patch every wrapped class.
  `ENGINE.md` forbids editing `l2sim.py`, `l2ref.py`, `score.py`, `library.py`, `run_menus.py`, `families/__init__.py`.
- **The contract.** `check_entry` (class subclasses `l2sim.Template`; `DEFAULTS`, `SCHEMA`, `SCREEN_TFS`, `FEATURES`;
  name lower-case; `inputs` with no `tf`, `sess` "all"; non-empty `notes`; the class constructs) and `check_library`
  (`rationale` 20+ chars, `complexity`, `roots`, `variants`, ...).
- **Joining the blocks.** Later families join the heat-map blocks themselves with `join_blocks()` (see
  `families/noise.py:119-133`): `blocks._wrap(name, cls)`, `blocks.BASES[name]`, `blocks.WRAPPED[name]`,
  `setattr(blocks, cls.__name__, cls)`. `blocks.py` is never edited: `runner.code()` hashes it, so an edit would mark
  every saved table stale.
- **Workers.** `l2sim.run_many` uses a spawn pool; a spec is pickled as `(cls, params)` and the worker re-imports the
  class by module and name (`l2sim._resolve`). A spawned worker gets the parent's `sys.path`.
- **The staleness hash.** `blueprint/runner.py` `code(family)` = sha256 over `l2sim.py`, `l2ref.py`,
  `families/blocks.py`, `families/<MODULE_OF[family]>.py`, `flowtab.py`, `bpfeat.py`, `levels.py`, `zones.py`,
  `indicators.py` (+ flex files).
- **Filters have no plug-in point.** `Blocks.allowed` is a hard-coded chain; `FILTERS`, `PLAIN`, `DEFAULTS` and `SCHEMA`
  are fixed tables in `blocks.py`. Indicators (`engine/indicators.py`) are plain functions with no registry, used only
  by hard-coded calls.
- **The toolkit runs with full rights.** `bp.py` and `.venv-research` are never sandboxed today. The draft sandbox
  (`homebase/backtest/draft.sb`, applied by `homebase/backtest/sandbox.py`) is for the tester's drafts only and denies
  `~/.homebase`.
- **Look-ahead tests today** are per family, by "garble after a cut": `engine/tests/test_blocks.py` has `minute_tape`,
  `garble(tape, cut_ns, seed)` and `play(cls, params, tape, daily, features)`; the check is that everything at or before
  the cut is the same with clean and garbled data, and that the garbage changed something after it. There is no test
  that runs over every family.
- **Charts.** The research engine's `plot` does nothing (`l2sim.py:1142`, "charts are not simulated").
- **The mini.** `bp_node` ships only the idea's folder; minisync ships only committed main. Nothing outside the repo
  reaches the mini.
- **The connector.** A tool is a spec (`_spec(name, description, props, required)`) plus a method `t_<name>`; `_bp(args)`
  runs `bp.py <args> --root=<ideas root> --json` with a 300 s timeout. Mission mode (`homebase/claude_mcp/mission.py`)
  has the allowlist `BASE` and the guards.

## Rulings made in this plan (the owner can overrule)

1. **What can go on the shelf in this build: entries (a family) and indicators (a module of plain functions a shelf
   entry may import). A "whole strategy" is an entry that carries its own filters as settings.** A **reusable filter**
   (one any family can switch on) is **not** built: it needs either an edit of `blocks.py`, which marks every saved
   table in the Lab stale, or a new layer that composes classes at run time. Cost: a filter idea is tested inside its
   own entry until that is decided. This is the owner's call to make before Plan 3 is built or after.
2. **Shelf runs stay on this Mac.** A run of an idea built on a shelf piece never goes to the mini (`--node=off` is
   forced). Cost: those tables use only this Mac's slots. The design's "runs carry their shelf pieces" is left out.
3. **Names.** A piece is `<name>_v<n>`; its family name in the toolkit is `s_<name>_v<n>` (so it can never collide with
   a repo family, and the `s_` prefix alone tells the toolkit to sandbox the run).
4. **Charts (gate check 6).** The research engine draws nothing, so the gate checks that the entry declares `DRAWS`
   (a non-empty tuple of names) and calls `self.plot(...)` for each name at least once in its smoke run. Showing it on
   the Lab chart comes when the piece is committed into the repo. Cost: a shelf idea has a table and no chart.
5. **Workers still get no file tool.** The Builder writes and reads pieces through connector tools (`shelf_write`,
   `shelf_read`), and reads toolkit source through `toolkit_code`, which serves a fixed list of code files. The design's
   "read the whole Homebase repo" is narrowed, because the repo holds test-month stores.
6. **His yes commits to Homebase main.** `shelf promote` is the one path, started only from the Missions app's "Commit
   into Homebase" button with his words. It ships to the trading server like any commit on main, when every account is
   flat.
7. **The look-ahead test on shifted data** (design line 372; parked as I6 in Plan 1) is built here and joins the Judge's
   "It looks ahead" charge for every family, shelf or repo.
8. **"Nothing built on a shelf piece goes on the Desk before it is committed"** is a written rule (CLAUDE.md, Task 10), not
   a code check: putting a strategy on the Desk is already the owner's own act. Cost: it rests on the rule being read.

## Global Constraints

- Homebase code: worktree `~/ramos-quant-homebase/.worktrees/shelf`, branch `feat/shelf`, off `main`. Never edit, commit
  or switch branch in the main checkout. Merged only on the owner's word. Never push.
- App code (Tasks 9, 10): `~/missions`, branch `feat/shelf-app`.
- Never edit `l2sim.py`, `l2ref.py`, `score.py`, `library.py`, `run_menus.py`, `families/__init__.py`,
  `families/blocks.py`. If a task seems to need one, STOP and report BLOCKED.
- Tests: research `~/ramos-quant-homebase/.venv-research/bin/python -m pytest <file> -W error` (cwd
  `<worktree>/research/edge-library`); app `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/<file>` (cwd the
  worktree root). Every shelf test sets `HOMEBASE_SHELF` to a temp folder: no test touches `~/.homebase/shelf`.
- While building, never run a real heat map, a real in-sample table or a test-month read. Engine tests use the synthetic
  tapes of `engine/tests` (`minute_tape`) and `tmp_path`. The gate's smoke run in tests uses the synthetic tape; its real
  "few in-sample months" mode is exercised once, by hand, on the owner's word, after the merge.
- The shell hook blocks recursive force-deletes: use `tmp_path`, `tempfile`, `shutil.move`.
- A broken shelf piece must never break the repo's own families: nothing in this plan may add to `families.ERRORS`.
- NQ only for missions. hm40 stays the exit grid: a piece cannot change it. The pipeline stays off.
- `shelf_check` answers pass or fail and what failed. It never returns a net, a win rate, a trade count or any number a
  worker could tune to.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, explicit paths only.

## Review Focus

1. A piece that opens a file (`open("/Users/.../runs_wf/x/oos/cells.npz")`, `numpy.load`, `pathlib.Path.read_bytes`), a
   socket, or a process, directly or through `getattr`/`__import__` tricks: refused at run time by the audit hook even
   when the static check missed it.
2. A piece whose file was edited after it was listed (its sha256 no longer matches the index): not loaded, shown with
   the reason, and every other piece and every repo family still loads.
3. A piece that imports cleanly but throws when built or run: lands in the shelf's own error list; `run_menus.registry()`
   does not raise; `bp.py blocks` still lists the repo's families.
4. A piece that passes with 1 worker and gives different trades with 8 (a module-level cache, a random seed): fails the
   gate.
5. `shelf promote` while Homebase main moved, or while the piece's name already exists in the repo: refused with the
   reason, nothing half-committed.

---

## The shelf's layout

```
~/.homebase/shelf/                       ($HOMEBASE_SHELF)   its own git repo (never pushed, never a remote)
  index.json                             {"pieces": {"<name>_v<n>": {"kind", "sha256", "listed_at", "built_by", "mission", "card": {...}}}}
  entry/<name>_v<n>/piece.py  card.json  test_piece.py  gate.json
  indicator/<name>_v<n>/piece.py  card.json  test_piece.py  gate.json
  _workbench/<kind>/<name>_v<n>/...      not listed; gate.json says what failed
  _mods/                                 one file per listed piece: s_<name>_v<n>.py (a copy of piece.py; on sys.path)
```

`card.json`: `{"name", "version", "kind": "entry"|"indicator", "does": "<one line>", "why": "<why it should work, 20+
chars>", "settings": {"<key>": {"values": [...], "default": ...}}, "built_by": "<role or chat>", "mission": <id or null>,
"date"}`. For an entry, `why` is written before any test (the gate refuses an entry with no `why`).

---

### Task 1: the look-ahead test on shifted data

**Files:** Create `research/edge-library/engine/lookahead.py`, `research/edge-library/engine/tests/test_lookahead.py`.
Modify `research/edge-library/blueprint/missionjudge.py` (the "It looks ahead" charge),
`research/edge-library/tests/test_mission_judge.py`.

**Interfaces — Produces:**

```python
# engine/lookahead.py
CUTS = (0.35, 0.6, 0.85)          # where the data is garbled, as a share of the tape
def check(cls, params: dict, *, tape=None, daily=None, features=None, cuts=CUTS, seed=7) -> dict
    # {"ok": bool, "why": str | None, "cuts": [{"cut_ns", "same_before": bool, "changed_after": bool}]}
def check_family(name: str, inputs: dict | None = None) -> dict       # the registered family, its unit inputs
```

`check` plays the class on a clean synthetic tape and, for each cut, on the same tape with everything after the cut
garbled; `ok` is true when every event at or before every cut is identical (entries, exits, the spy log) **and** the
garbage changed something after at least one cut. If the family never trades on the test tape the answer is `{"ok": False,
"why": "the test could not see this family trade on the test tape"}`: a family the test cannot exercise is not waved through.

- [ ] **Step 1: Read** `engine/tests/test_blocks.py` (`minute_tape` line ~75, `garble` ~128, `play` ~158, the look-ahead
  tests ~331, 392, 512, 658) and `engine/tests/test_fvg.py:221-265` (several cuts, "the garbage mattered").
- [ ] **Step 2: Move, do not copy:** `minute_tape`, `garble` and `play` go into `engine/lookahead.py`; `test_blocks.py`
  (and any other test file that defines its own copy) imports them from there. Run the files you touched: same results.
- [ ] **Step 3: Tests** (`test_lookahead.py`): an honest toy family (`Template` subclass that enters on a closed bar)
  → `ok` True; a cheating toy family (reads the next bar's close) → `ok` False with `why` naming the first cut; a family
  that never trades on the tape → `ok` False, "could not see this family trade"; `check_family("orb830")` (or another
  small registered family) → `ok` True.
- [ ] **Step 4: The charge.** In `missionjudge.charges`, the "It looks ahead" charge now also needs
  `lookahead.check_family(family, inputs)["ok"]`; its `why` carries the look-ahead test's `why`. Keep whatever the
  charge checked before (the code check). Tests in `test_mission_judge.py`: with a seam `MJ._lookahead` faked to fail,
  the charge does not hold and the gate is not clear; faked to pass, as before.
- [ ] **Step 5: Run** `engine/tests/test_lookahead.py engine/tests/test_blocks.py tests/test_mission_judge.py -W error`.
- [ ] **Step 6: Commit** `Look-ahead on shifted data: one test for any family; the Judge's charge uses it`.

- [ ] **Step 7 (report only, changes nothing):** run `check_family` over every registered family
  (`families.REGISTRY`) and put the table (family, ok, why) in your report. A repo family that fails is the owner's to
  hear about, not yours to fix.

---

### Task 2: the shelf store

**Files:** Create `homebase/shelf.py`, `tests/test_shelf_store.py`.

**Interfaces — Produces** (no piece code is ever imported or run here):

```python
KINDS = ("entry", "indicator")
NAME_RE = r"^[a-z][a-z0-9_]{1,30}$"
class ShelfError(ValueError): ...
def root() -> Path                                   # $HOMEBASE_SHELF or ~/.homebase/shelf; made, `git init` on first use
def piece_id(name, version) -> str                   # "<name>_v<n>"
def family_name(pid) -> str                          # "s_<name>_v<n>"
def next_version(kind, name) -> int                  # 1 + the highest version on the shelf OR the workbench
def write(kind, name, files: dict, card: dict, *, built_by, mission=None) -> str
    # a NEW version on the workbench: files = {"piece.py": str, "test_piece.py": str}; returns the piece id.
    # Refuses: a bad name; a name a repo family or module already has; a file other than those two; a file over 200,000 bytes;
    # code that does not compile; an entry card with no "why" of 20+ chars.
def read(pid) -> dict                                # {"kind", "where": "shelf"|"workbench", "card", "files": {...}, "gate": {...}|None}
def listing() -> dict                                # {"shelf": [...], "workbench": [...]}: id, kind, does, built_by, mission, gate ok / what failed
def index() -> dict
def sha(pid) -> str                                  # sha256 of piece.py
def list_piece(pid, gate: dict) -> None              # workbench -> shelf: move the folder, copy piece.py to _mods/s_<pid>.py,
                                                     # add to index.json (with the sha), `git add` + `git commit` in the shelf's repo
def unlist(pid, why: str) -> None                    # out of index.json and _mods (the folder stays), committed
def intact(pid) -> bool                              # the file's sha256 == the index's
```

A piece is **never edited in place**: `write` always makes a new version folder; there is no update function. The
shelf's git repo has no remote; `list_piece` and `unlist` are its only writers.

- [ ] **Step 1: Tests** (`HOMEBASE_SHELF` = `tmp_path`): `write` makes `_workbench/entry/foo_v1/` with the three files
  and returns `foo_v1`; a second `write` of `foo` gives `foo_v2`; a name of a repo family (take one from
  `research/edge-library/engine/families/`) is refused; a third file (`evil.sh`) is refused; code with a syntax error is
  refused; an entry with no `why` is refused; `list_piece` moves it, writes `_mods/s_foo_v1.py` with the same bytes,
  records the sha, and the shelf's `git log` has one new commit; `intact` turns false when the shelf file is changed by
  hand; `unlist` removes the `_mods` file and the index row; `read` of an unknown id raises `ShelfError`; `listing`
  shows a failed workbench piece with what failed.
- [ ] **Step 2-5: fail, implement, pass, commit** `The shelf store: pieces, versions, the index, its own git history`.

---

### Task 3: the guard (what piece code may import and do)

**Files:** Create `research/edge-library/engine/shelfguard.py`, `research/edge-library/engine/tests/test_shelfguard.py`.

**Interfaces — Produces:**

```python
ALLOWED_IMPORTS = {"math", "statistics", "bisect", "collections", "dataclasses", "enum", "functools", "itertools",
                   "typing", "numpy", "indicators", "levels", "zones", "ranges", "flexind"}
L2SIM_NAMES = {"Template"}                 # the only thing a piece may take from l2sim: `from l2sim import Template`
def static_check(source: str, *, mods: set[str] = frozenset()) -> list[str]     # [] = clean; else the reasons
def install(shelf_mods: Path) -> None      # sys.addaudithook(...) once per process; idempotent
class ShelfDenied(PermissionError): ...
```

- `static_check` (AST): every `import` / `from ... import` must name a module in `ALLOWED_IMPORTS`, or `l2sim` with only
  `Template`, or a listed shelf indicator module (`mods`, names `s_<pid>`). Refused by name anywhere in the code:
  `open`, `exec`, `eval`, `compile`, `__import__`, `globals`, `vars`, `input`, `breakpoint`; any attribute or name that
  starts and ends with two underscores other than `__init__`, `__name__` and `__doc__`; `getattr`/`setattr`/`delattr`
  whose attribute argument is not a string literal.
- `install` adds one audit hook. For the events `open`, `os.open`, `os.listdir`, `os.scandir`, `os.remove`, `os.rename`,
  `os.mkdir`, `os.system`, `os.exec`, `os.posix_spawn`, `os.fork`, `subprocess.Popen`, `socket.connect`, `socket.bind`,
  `socket.getaddrinfo`, `ctypes.dlopen`, `urllib.Request`, `shutil.copyfile`, `shutil.rmtree`, `pickle.find_class`
  (and `import` of a module outside the allow rules), it walks the stack from the innermost frame outward, skipping
  frames whose file is in the standard library or `site-packages`; if the first frame it reaches is a file under
  `shelf_mods`, it raises `ShelfDenied("a shelf piece may not <event>")`. A frame of the engine (`engine/*.py`) reached
  first means the engine itself is doing the work: allowed.

  ```python
  def _hook(event, args):
      if event not in WATCHED and event != "import": return
      f = sys._getframe(1)
      while f is not None:
          fn = f.f_code.co_filename
          if fn.startswith(_MODS): 
              if event == "import" and _import_ok(args[0]): return
              raise ShelfDenied(f"a shelf piece may not {event}")
          if not (fn.startswith(_STDLIB) or "site-packages" in fn or fn.startswith("<")): return
          f = f.f_back
  ```

- [ ] **Step 1: Tests.** `static_check`: clean code passes; `import os`, `from pathlib import Path`, `import barstore`,
  `import l2sim`, `from l2sim import run_many`, `open("x")`, `__import__("os")`, `x.__class__`, `getattr(m, name)` each
  give a reason naming the line; `from l2sim import Template`, `import numpy as np`, `from indicators import atr_series`
  pass. Audit hook (each in a **subprocess**, because a hook cannot be removed; write the piece to a temp `_mods`
  folder, `install`, import it, call it): a piece function that calls `open(__file__)` raises `ShelfDenied`; one that
  calls `numpy.load(path)` raises; one that reaches `open` through `[c for c in ().__class__.__base__.__subclasses__()]`
  style tricks still cannot open a file; `socket.create_connection` raises; `subprocess.run` raises; an engine helper
  (`indicators.atr_series`) called from the piece works; the same `open` from a test-file frame (not under `_mods`) is
  allowed.
- [ ] **Step 2-5: fail, implement, pass, commit** `Shelf guard: the import check and the runtime audit hook`.

---

### Task 4: the sandbox around toolkit runs that load a piece

**Files:** Create `research/edge-library/shelf.sb`, `research/edge-library/blueprint/shelfbox.py`,
`research/edge-library/tests/test_shelfbox.py`. Modify `research/edge-library/blueprint/cli.py` (the first lines of
`main`), `research/edge-library/blueprint/missiondoor.py` (the first lines of `main`).

**Interfaces — Produces:**

```python
ENV = "HOMEBASE_SHELF_SANDBOXED"
def uses_shelf(argv: list[str], ideas_root: Path) -> bool
    # True when the command names a shelf family: `"s_` family in a card/settings JSON in argv, or the idea named in argv
    # has a saved spec/card whose family starts with "s_", or the command is `shelf check`.
def available() -> bool                      # sandbox-exec is there and the profile denies what it must (probe; fail closed)
def command(argv: list[str], *, oos: bool = False) -> list[str]     # ["/usr/bin/sandbox-exec", "-f", shelf.sb, "-D", "REPO=...", ..., python, "bp.py", *argv]
def reexec_if_needed(argv, ideas_root, *, entry: str) -> None       # os.execve under the sandbox with ENV=1 and --node=off; returns if not needed
```

`cli.main` begins with `shelfbox.reexec_if_needed(argv, ideas_root, entry="bp.py")`; `missiondoor.main` does the same for
`gate`, `odds`, `mc`, `table`, `charges` and `read` (for `read`, `oos=True`). Inside the sandbox (`ENV == "1"`) it does
nothing. When a shelf run is asked for and `available()` is false, the command is refused: "the shelf's sandbox is not
available on this machine: a shelf piece cannot run". On the trading server nothing changes (it refuses backtests first).

**The profile** (`shelf.sb`, deny by default, parameters with `-D`):

```scheme
(version 1)
(deny default)
(allow process-fork)
(allow process-exec (literal (param "PYEXE")) (literal (param "PYREAL")))
(allow sysctl-read) (allow mach-lookup) (allow signal (target self))
(allow file-read*  (subpath "/usr") (subpath "/System") (subpath "/Library") (subpath "/private/var/db") (subpath "/dev")
                   (subpath (param "PYHOME")) (subpath (param "VENV")) (subpath (param "REPO"))
                   (subpath (param "SHELF")) (subpath (param "DATA")) (subpath (param "IDEAS")))
(deny  file-read*  (regex (string-append "^" (param "REPO") "/research/edge-library/runs_wf/[^/]+/oos(/|$)"))   ; lifted when OOS=1
                   (subpath (string-append (param "REPO") "/.git"))
                   (subpath (string-append (param "HOME") "/.homebase/missions"))
                   (subpath (string-append (param "HOME") "/.ssh")) (subpath (string-append (param "HOME") "/Library/Keychains")))
(allow file-write* (subpath (param "TMP")) (subpath (param "IDEAS"))
                   (subpath (string-append (param "REPO") "/research/edge-library/runs_wf"))
                   (literal (string-append (param "REPO") "/research/edge-library/ledger.csv")))
(deny  file-write* (subpath (string-append (param "REPO") "/.git")) (subpath (param "SHELF")))
; no (allow network*): every socket is refused, localhost too
```

`DATA` = `~/futures_derived`. With `oos=True` the `oos` deny line is left out and the same path is writable (the Judge's
read). The shelf itself is read-only inside the sandbox; `shelf check` writes its result to `TMP` and the caller (outside)
moves the piece.

- [ ] **Step 1: Find what a table run really reads and writes.** Run one **synthetic** engine run (the 1-vs-8-workers
  test of a small repo family, `engine/tests`) under `sandbox-exec -f shelf.sb` and widen the profile only for paths the
  engine itself needs (locks, caches, `engine/cache`, `/private/tmp`, the multiprocessing semaphores: `(allow ipc-posix-sem)`
  / `(allow ipc-posix-shm)` if the pool needs them). List every line you added and why in the report. Never add a
  network rule, never open `.git`, `oos` (without `OOS`), `~/.homebase/missions` or `~/.ssh`.
- [ ] **Step 2: Tests** (`test_shelfbox.py`; skip with a clear reason where `sandbox-exec` is missing):
  `uses_shelf(["card", '{"settings": {"family": "s_foo_v1"}}'])` is true, and false for `orb830`; an idea whose saved
  spec names `s_foo_v1` is true by name; `shelf check foo_v1` is true; `command()` has no network rule and names the
  profile; under the profile a child Python: cannot `open` a file under a fake `runs_wf/x/oos/`, can with `oos=True`;
  cannot write under `.git`; cannot connect to `127.0.0.1:8852`; can write under `TMP`; `reexec_if_needed` does nothing
  when `ENV` is `1`; adds `--node=off`; refuses when `available()` is false.
- [ ] **Step 3: Run; fail. Step 4: Implement and wire `cli.main` and `missiondoor.main`. Step 5: Run** these tests plus
  `tests/test_mission_door.py` and one existing `bp.py` CLI test file (to see that a non-shelf command is untouched).
- [ ] **Step 6: Commit** `Shelf sandbox: every toolkit run that loads a piece runs under sandbox-exec`.

---

### Task 5: the toolkit loads the shelf

**Files:** Create `research/edge-library/engine/families/zshelf.py`, `research/edge-library/engine/shelfload.py`,
`research/edge-library/engine/tests/test_shelfload.py`. Modify `research/edge-library/blueprint/runner.py` (`code`),
`research/edge-library/blueprint/blocklist.py`, `research/edge-library/blueprint/blockcode.py`,
`homebase/claude_mcp/blueprint_tools.py` (`toolkit_stamp`), `homebase/store/arsenal.py` (`research_stamp`).

**Interfaces — Produces:**

```python
# engine/shelfload.py
ERRORS: dict[str, str] = {}                 # piece id -> why it was not loaded  (never families.ERRORS)
LOADED: dict[str, str] = {}                 # family name -> piece id
def shelf_root() -> Path
def load(families_mod, blocks_mod) -> None  # see below
def is_shelf(family: str) -> bool           # family.startswith("s_")
def piece_file(family: str) -> Path         # the shelf's piece.py of that family (for the staleness hash)
def cards() -> list[dict]                   # every listed piece from index.json, WITHOUT importing any code

# engine/families/zshelf.py   (sorts after every other module; load() imports it last)
FAMILIES = {}                               # the registry's own contract: an empty dict is legal
import shelfload; shelfload.load(sys.modules["families"], ...)   # wrapped in try/except Exception: never raises
```

`shelfload.load`:
1. If `os.environ.get("HOMEBASE_SHELF_SANDBOXED") != "1"`: return (outside the sandbox no piece code is ever imported).
2. `shelfguard.install(shelf_root() / "_mods")`; put `_mods` on `sys.path`.
3. For each piece in `index.json`, in name order, inside its own `try`: `shelf.intact` (sha) else `ERRORS[pid] = "changed
   after it was listed"`; `shelfguard.static_check` else the reasons; an indicator is only imported
   (`importlib.import_module("s_<pid>")`); an entry is imported, must define `FAMILIES` with exactly one entry named
   `s_<pid>`, passes `families_mod.check_entry` and `check_library`, the name is not already registered; then
   `REGISTRY[name] = entry[:4]`, `MODULE_OF[name] = "s_<pid>"`, `LIBRARY[name] = ...`, and it joins the blocks the way
   `noise.join_blocks()` does (`blocks._wrap`, `BASES`, `WRAPPED`, `setattr`). Any exception → `ERRORS[pid] = str(e)`.

Because `zshelf` is imported inside `load()`, before `_flex.apply()` and `_flat.apply()`, shelf entries get the same
patches as repo families. `zshelf` must never add to `families.ERRORS`: its whole body is in `try/except Exception`.

`runner.code(family)`: for a shelf family, hash `shelfload.piece_file(family)` in place of
`families/<MODULE_OF[family]>.py`, plus every shelf indicator module the piece imports (found by `static_check`'s import
list), with the same core files. `blocklist.blocks()`: adds, from `shelfload.cards()` (no import), one row per listed
entry under `families` with `"shelf": {"piece", "version", "built_by", "mission"}` and its settings from the card, and a
`shelf_errors` list from the gate results; `blockcode` adds a "Shelf" group whose source is the piece file.
`toolkit_stamp()` and `research_stamp()` also take the mtime of the shelf's `index.json`.

- [ ] **Step 1: Read** `families/__init__.py` (`load`, 195-244; `check_entry`; `check_library`), `families/noise.py`
  (`join_blocks`), `runner.code`, `blocklist.families`/`blocks`, `blockcode`.
- [ ] **Step 2: Tests** (`test_shelfload.py`; a temp shelf with a toy entry `s_toy_v1`, a toy indicator, a broken entry,
  an edited entry; runs that need the env flag run in a subprocess with `HOMEBASE_SHELF_SANDBOXED=1` set but **without**
  `sandbox-exec`, since the flag is what the loader reads):
  - without the flag: `families.REGISTRY` has no `s_` name and `shelfload.ERRORS == {}` (nothing was imported: `"s_toy_v1" not in
    sys.modules`);
  - with the flag: `s_toy_v1` is in `REGISTRY` and `blocks.WRAPPED`; `families.ERRORS == {}`;
  - a piece that raises at import is in `shelfload.ERRORS`, `families.ERRORS == {}`, and `run_menus.registry()` does
    not raise;
  - an edited piece is in `ERRORS` with "changed after it was listed" and was not imported;
  - a piece named like a repo family is refused;
  - the toy entry gives identical trades at 1 worker and at 8 on the synthetic tape (spawned workers find the module);
  - `runner.code("s_toy_v1")` changes when the piece file's bytes change and is the same for the same bytes at another
    path;
  - `blocklist.blocks()` (no flag) lists `s_toy_v1` with `shelf.piece == "toy_v1"` and never imports it;
  - `engine/tests/test_families.py` still passes (the registry loads clean).
- [ ] **Step 3-6: fail, implement, pass, commit** `The toolkit reads the shelf: zshelf, the staleness hash, the block list`.

---

### Task 6: the gate

**Files:** Create `research/edge-library/blueprint/shelfgate.py`, `research/edge-library/tests/test_shelfgate.py`.
Modify `research/edge-library/blueprint/cli.py` (`shelf check <piece>`, `shelf list`).

**Interfaces — Produces:**

```python
CHECKS = ("imports alone", "meets the contract", "no look-ahead", "same trades at 1 worker and at 8",
          "the smoke run finishes", "draws its indicators", "its own test passes")
def check(pid: str, *, smoke="synthetic") -> dict
    # {"piece", "ok": bool, "checks": [{"check", "ok": bool, "why": str | None}]}    -- never a profit, a loss or a trade count
```

`bp.py shelf check <piece>` (it re-execs under the sandbox, Task 4) runs `check` on a **workbench** piece and prints the
result. The connector (Task 7), outside the sandbox, then calls `shelf.list_piece(pid, gate)` when `ok`, or writes
`gate.json` on the workbench when not. The seven checks, in order (a failed check stops the rest):

1. **imports alone:** `static_check` is clean, and the module imports in a fresh subprocess with the guard installed.
2. **meets the contract:** entry → `check_entry` and `check_library`, `FAMILIES` has exactly one entry named
   `s_<pid>`; indicator → every public function has a docstring and returns `None` or a number or list for a bar list
   (called once on a synthetic bar list).
3. **no look-ahead:** `lookahead.check(cls, unit inputs)` (Task 1); indicator → for each public function, the value at
   bar *k* is the same when bars after *k* are garbled.
4. **same trades at 1 worker and at 8:** the technique of
   `test_registered_family_gives_identical_trades_at_1_and_8_workers`, on the synthetic tape.
5. **the smoke run finishes:** `smoke="synthetic"` plays the synthetic tape; `smoke="months"` runs 3 in-sample months
   through `l2sim.run` with the 3:1 in-sample allow (`S.ALLOW_WF_IS`). Either way only "finished" or the error is kept.
6. **draws its indicators:** the class has a non-empty tuple `DRAWS`, and during the smoke run `plot` was called at
   least once for each name (wrap `plot` on the instance to count).
7. **its own test passes:** `pytest test_piece.py -q` in the piece's folder, in a subprocess with the guard installed.

- [ ] **Step 1: Tests** (temp shelf, toy pieces written by the test): a good entry passes all seven; a piece that
  imports `os` fails check 1 with the line; a class with no `SCHEMA` fails check 2; the cheating toy of Task 1 fails
  check 3; a piece with a module-level counter that changes its entries fails check 4; a piece that raises on the tape
  fails check 5 with the error text; a piece with no `DRAWS`, and one that declares a name it never plots, fail check 6;
  a failing `test_piece.py` fails check 7; a good indicator passes; the result of a passing and of a failing check
  holds no key or text matching `net|profit|loss|win|trades=\d` (assert on `json.dumps`).
- [ ] **Step 2-5: fail, implement, pass, commit** `The shelf's gate: seven checks, pass or fail`.

---

### Task 7: the connector's shelf tools

**Files:** Modify `homebase/claude_mcp/blueprint_tools.py` (five specs + handlers), `homebase/claude_mcp/mission.py`
(allowlist, guards), `homebase/missions.py` (`KINDS` gains `"piece"`), `homebase/claude_mcp/protocol.py` (the
instructions text). Test: `tests/test_claude_mcp_shelf.py`, `tests/test_claude_mcp_mission.py`, `tests/test_claude_mcp.py`
(the pinned tool names).

**Interfaces — Produces** (tools, for every chat and for mission mode):

| Tool | Arguments | Answer |
|---|---|---|
| `shelf_list` | – | the shelf and the workbench: id, kind, what it does, who built it, gate ok or what failed |
| `shelf_read` | `piece` | its card, `piece.py`, `test_piece.py`, the gate's result |
| `shelf_write` | `kind`, `name`, `code`, `test`, `card` | the new piece id (always a new version, on the workbench) |
| `shelf_check` | `piece` | pass or fail and what failed; on a pass the piece is listed and usable at once |
| `toolkit_code` | `file` | the source of one toolkit code file from a fixed list |

- `toolkit_code` serves only: `ENGINE.md`, `engine/l2sim.py`, `engine/indicators.py`, `engine/levels.py`, `engine/zones.py`,
  `engine/ranges.py`, `engine/families/README.md`, and `engine/families/<module>.py` for a module name matching
  `^[a-z][a-z0-9_]*$` that exists and is not `blocks` (too big: it answers with the Blocks contract section of
  `ENGINE.md` instead). It reads from the checkout the connector runs in. No other path, no `..`, no absolute path.
- `shelf_check` runs `self._bp(["shelf", "check", piece])` with a 1,200 s timeout, then `shelf.list_piece` on a pass
  (and adds one line at the top of the vault's RECENT.md list: `- <date> · code · New tool on the shelf: <piece>
  (<does>), built by <who>; waits for your yes to commit · [[shelf]]`), or saves `gate.json` on a fail.
- **Mission mode:** `BASE` gains the five. `shelf_write` records a ledger row `("piece", <pid>)` and stamps the card
  with `mission` and `built_by` (the role is not known to the connector: `built_by` = `"mission <id>"`). `shelf_check`
  and a second `shelf_write` of the same name are allowed only for a piece this mission's ledger holds (`_owned("piece",
  pid)`); `shelf_read` and `shelf_list` are open (a mission may build from any listed piece). None of them is a try.
  Outside mission mode `built_by` = `"chat"`.
- The instructions text gains: "New tools: shelf_list, shelf_read, toolkit_code (read how the toolkit is written),
  shelf_write (always a new version), shelf_check (pass or fail, never a profit or loss). A piece that passes is family
  s_<name>_v<n> in blueprint_blocks. An entry needs its 'why' written before any test."

- [ ] **Step 1: Tests:** each tool's happy path against a temp shelf (with `_bp` faked for `shelf_check`); `toolkit_code`
  serves `engine/l2sim.py` (a builder must read `Template`) and refuses `../ledger.csv`, `/etc/hosts`,
  `runs_wf/x/oos/run.json`, `blueprint/hmwf.py` and any file not on the list; in mission mode `shelf_check` of another mission's workbench piece is refused and
  logged; `shelf_write` records the ledger row and never counts as a try (`missions.tries` unchanged); the answer of
  `shelf_check` has no number-like result field; the RECENT.md line is added once per listed piece; the mission-mode
  tool list is now 14 (the smoke count of Plan 1's Task 7 becomes 14); the non-mission tool list gains exactly the five.
- [ ] **Step 2-5: fail, implement, pass, commit** `Connector: shelf_list, shelf_read, shelf_write, shelf_check, toolkit_code`.

---

### Task 8: his yes commits a piece into Homebase

**Files:** Create `research/edge-library/blueprint/shelfpromote.py`, `research/edge-library/tests/test_shelfpromote.py`.
Modify `research/edge-library/blueprint/cli.py` (`shelf promote <piece> --said "<his words>"`).

**Interfaces — Produces:**

```python
def promote(pid: str, said: str, *, repo: Path | None = None) -> dict     # {"piece", "commit", "files": [...]}
```

Steps, all or nothing:
1. Refuse: an empty `said`; a piece not listed; a piece not `intact`; an indicator that listed entries still import
   under its shelf name is promoted first or together (refuse an entry whose indicator is not yet in the repo, naming it).
2. `git worktree add <temp> main` (a clean copy of main; never the main checkout). In it write
   `research/edge-library/engine/families/s_<pid>.py` (the piece's bytes; for an indicator
   `research/edge-library/engine/s_<pid>.py`) and `research/edge-library/engine/tests/test_s_<pid>.py` (its own test).
   A file that already exists → refuse.
3. In the temp worktree run `engine/tests/test_families.py` and the piece's test with `.venv-research`. A failure →
   remove the worktree, refuse with the output's last lines.
4. Commit only those files: `Shelf: <pid> (<does>), committed on the owner's word: "<said>"` + the attribution line.
5. Move `main` to that commit only if `main` is still the commit the worktree was made from (`git update-ref
   refs/heads/main <new> <old>`); else refuse: "main moved; try again". Remove the worktree.
6. `shelf.unlist(pid, "committed into Homebase <commit>")`. From then on `zshelf` finds the name already registered by
   the repo's own module and skips it.

Because the committed file has the same bytes and the same family name, `runner.code()` is unchanged and every table
built on the piece stays current.

- [ ] **Step 1: Tests** (a temp git repo made by the test with a tiny `main`, a temp shelf, the test runner faked):
  the happy path makes one commit on `main` with exactly two files and the owner's words in the message; an empty
  `said` is refused; an edited piece is refused; a moved `main` is refused and leaves `main`, the shelf and the index
  untouched; a failing test leaves no commit and no worktree; a second promote of the same piece is refused (not
  listed); `git worktree list` has no temp entry after any outcome.
- [ ] **Step 2-5: fail, implement, pass, commit** `shelf promote: his yes commits a piece into Homebase`.

---

### Task 9 (Missions app): the Builder builds tools; "New tools"; the commit button

**Files (`~/missions`, branch `feat/shelf-app`):** Modify `missions/hb.py`, `missions/prompts/builder.md`,
`missions/prompts/doubter.md`, `missions/prompts/common.md`, `missions/engine.py`, `missions/api.py`,
`missions/static/js/home.js`, `missions/static/js/chat.js`. Create `missions/static/js/tools.js`,
`tests/test_tools.py`.

**Interfaces — Produces:**

```python
# hb.py
def shelf() -> dict                          # {"shelf": [...], "workbench": [...]} via <homebase>/.venv/bin/python -c ... homebase.shelf.listing()
def piece(pid) -> dict                       # card, code, test, gate
def promote(pid, said) -> dict               # bp.py shelf promote <pid> --said <said>   (Refused on a no)
```

- Routes: `GET /api/tools` (the shelf, newest first, each with `waits: true` until committed), `GET /api/tools/{pid}`,
  `POST /api/tools/{pid}/commit` `{said}`. The commit button reads "Commit into Homebase (it will reach the trading
  server)"; `said` = the button's words plus anything he types. A promote the server refuses shows its reason.
- The engine: after every Builder turn it compares `hb.shelf()["shelf"]` with the ids it knew; each new piece gets a
  Judge-voice chat line ("New tool on the shelf: foo_v1 — <does>. It can be used now; it waits for your yes to be
  committed."), an event `tool`, and `system.alert(mid, "tool")`.
- Prompts: the Builder may build a tool when the blocks cannot say the idea: `toolkit_code` to learn the contract,
  `shelf_write` (an entry needs `DRAWS`, its `why` first, and its own small test), `shelf_check`, fix and write a new
  version until it passes, then use family `s_<name>_v<n>` in a card. "Building a tool is not a try. Testing a version
  built with it is." The Doubter reads a new piece's code with `shelf_read` for look-ahead before its first table.
  A version built on a piece that is not listed is refused by the toolkit: say so.
- Home shows "New tools" (name, what it does, who built it, which mission, "waits for your yes" or the commit id) and a
  page per piece with its card, its code and its test (plain `<pre>`, no editor).

- [ ] **Step 1: Tests** (`FakeHB` gains `shelf`, `piece`, `promote`): a piece that appears after a Builder turn makes
  one chat line, one `tool` event and one alert, and not a second time on the next turn; `POST /commit` without `said`
  is refused; with it, `promote` is called with his words; a refusal is shown as text, status 409; `/api/tools` marks a
  committed piece.
- [ ] **Step 2-5: fail, implement, pass**, run with `MISSIONS_DEMO=1` (add two demo pieces to the fixture) and report
  console errors, **commit** `Tools: the Builder builds on the shelf, New tools, the commit button`.

---

### Task 10: the rules, the docs and the smoke test

**Files (Homebase worktree):** Modify `CLAUDE.md` (a "The shelf" section after "Missions"), `research/edge-library/ENGINE.md`
(a section 16, "The shelf"), `research/edge-library/engine/families/README.md` (one paragraph). Create the vault note
`30-Projects/Onyx-Trading/shelf.md` only on the planner's side (not in this task).

The CLAUDE.md section (write it in the file's own voice, about 130 columns): what the shelf is and where
(`~/.homebase/shelf`, its own git history); a piece is `s_<name>_v<n>`, never edited in place; any chat may write and
check a piece with the `shelf_*` tools; a piece runs only under the shelf sandbox, on this Mac, never on the mini or the
server; nothing built on a shelf piece goes on the Desk before the piece is committed; only the owner's yes in the
Missions app commits one (`shelf promote`); never copy a piece into the repo by hand; reusable filters are not built.

- [ ] **Step 1:** Write the three doc changes.
- [ ] **Step 2: The smoke test** (by hand, in the worktree, temp `HOMEBASE_SHELF`, synthetic smoke only — no real
  table): `shelf_write` a small honest entry through the connector's `Toolbox` in a Python one-liner, `shelf_check` it,
  see it listed, see `bp.py blocks --json` list `s_<name>_v1` with its shelf mark, see `bp.py shelf list`. Then write a
  piece that opens a file, check it, see it fail check 1 and stay on the workbench. Paste both outputs in the report.
- [ ] **Step 3: Run the whole of this plan's tests** (research and app). **Step 4: Commit** `CLAUDE.md, ENGINE.md: the shelf`.

---

## After the build (each needs the owner's word)

1. Merge Homebase `feat/shelf` into main (it ships to the trading server; the server never runs the toolkit).
2. Merge `~/missions` `feat/shelf-app`; restart the app.
3. One real check on the Mac: `bp.py shelf check <piece> --smoke=months` on a toy piece (3 in-sample months), then one
   real in-sample table of an idea built on it, to see the sandbox holds on a full run.
4. Decide ruling 1 (reusable filters).

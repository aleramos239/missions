# Plan 1: the Homebase fence and the Judge

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Missions a safe way into Homebase: a connector "mission mode" that shows workers only the tools a mission
may use, and the Judge (fixed code) that grades a version, measures the goal on the owner's prop accounts, and is the
only door to the test months.

**Architecture:** All code in this plan lives in the Homebase repo (`~/ramos-quant-homebase`), on its own branch. Mission
state is a few files per mission under `~/.homebase/missions/<id>/`. The connector gets a `--mission <id>` flag that swaps
in a subclass of its `Toolbox` with an allowlist and per-tool guards. The Judge is a research module plus a bash door
modeled on `research/edge-library/hunt/bp`. It reuses `hunt._box`, `real.check`, `api.wf_pick` / `api.wf_oos` and the
tester's own prop sim (`homebase/backtest/propsim.evaluate`), which reads all 18 of the owner's new accounts. The Missions
app itself (Plan 2) only calls these.

**Tech Stack:** Python 3 (the app's `.venv` for `homebase/`, `.venv-research` for `research/edge-library/`), pytest,
bash, numpy. No new dependency.

**Spec:** `~/missions/docs/specs/2026-11-14-missions-design.md` (approved 2026-11-14), sections 5, 6, 9 and 11, with the
accounts paragraph in section 5.

**How this plan is run (owner, 2026-11-14):** the code below was written by the planner (Fable 5.2) from a read of the
real files; Opus 5.5 subagents build it task by task. The code is the design. Where it disagrees with what the real
code in the repo does (a signature, a field name, a helper that already exists), **the real code wins**: fix the plan's
code to fit, keep the behaviour the tests pin, and say what you changed in your report. Never weaken a test to make it
pass; a test that cannot pass as written is reported, not edited away.

## Global Constraints

- Work only in the worktree `~/ramos-quant-homebase/.worktrees/missions-fence` (branch `feat/missions-fence`, off `main`). Never edit, commit or switch branch in the main checkout `~/ramos-quant-homebase` (it is on another branch with other people's uncommitted edits). A commit on `main` ships to the VPS by itself: this branch is merged only on the owner's word. Never push.
- The worktree has no venvs. App tests: `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/<file> -v` with the cwd at the worktree root. Research tests: `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/<file> -v` with the cwd at `<worktree>/research/edge-library`.
- The shell hook blocks any command that contains a recursive force-delete (`rm` with `-rf`). Use `tmp_path` in tests and Python `tempfile` for scratch files.
- While building, never run a real heat map, a real in-sample table or a test-month read, and never call the real chart service. Tests use temp folders, hand-made rows, monkeypatched seams and the `Fake` chart service (`tests/test_claude_mcp.py`).
- "i dont want to use the chicago server to backtest ever": every Judge function that runs the engine refuses when `~/.homebase/no_backtests` exists.
- NQ only. The pipeline stays off (never call `bp.py pipe`, never touch `pipe_*`). Never write `payout_enabled`.
- Mission ids are positive integers; every name a mission makes starts with `m<id>_` (e.g. `m7_v01`; its drafts are listed as `draft_m7_...`) and must still pass `ideastore.validate_name` / `draftstore.validate_name`.
- The test-month read is marked `who: mission:<id>`. One read per version, then the version is frozen.
- The read's bar: read number k of this mission needs points over > k − 1 (1st > 0, 2nd > +1, 3rd > +2; no cap). Close = under the bar by less than 1 point.
- The luck bar: t ≥ `real.T_BAR + real.T_PER_TRY × (tries − 1)` = 2.0 + 0.25 a try. A mission's count starts from the family's tries on file (`start_tries`, one function, so the rule is one line to change).
- Workers hear only: held or broke, which line, close or far. No dollars, %, months or trade counts from the test months ever reach a worker; those go to a file only the app shows the owner (`~/.homebase/missions/<id>/reads/<name>.json`).
- Eval goal: the tester's prop sim, pass within 10 weekdays (`horizon=10`), at a fixed risk = the account's drawdown (`trailing_mll`) ÷ 2.5, on the box re-run with worse fills (line 5's fills), each trade capped at the account's `cap_micros`. The target is a fraction (0.5 = 50 %).
- The accounts a goal may name are the 18 rule files of 2026-11-14. Lucid Flex and Lucid Pro are closed to the owner since 2026-11-14 ("I got moved to live and I can't use the flex or the pro accounts anymore").

## Review Focus

1. A worker names another mission's version (`m3_x` from mission 7) or a non-mission idea (`owner_fvg_odir_15_nl_new`) in any tool: refused and logged, never run.
2. An exact copy of a version that was already read is sent again under a new name: its in-sample run counts as a try, and the Judge refuses its read (same settings = frozen).
3. The Judge is started on the server (`~/.homebase/no_backtests` exists): it refuses before any engine call.
4. The re-run of the picked box gives different trades from its store (a changed family file, a repaired tape): the eval number is withheld with the reason, never shown as if it were right.
5. A goal names a closed (`lucid-flex-50k@2026-10-11`) or unknown account: refused with the reason; an old version of an open account resolves to its newest file.

---

## Words used below

- **box**: a row number of the idea's in-sample table as text (`"12"`), or the box's id; the same thing `hmwf.pick(name, box)` takes.
- **J.Refuse**: the blueprint toolkit's refusal (`research/edge-library/judge.py`, `import judge as J`, as `hmwf` imports it). It is an `Exception`, not a `ValueError`. The Judge raises it for every "no".
- **seam**: a small module-level function the tests replace with `monkeypatch.setattr` so no engine and no store is needed.

## File map

| File | Status | Responsibility |
|---|---|---|
| `homebase/missions.py` | new | Mission state: ids, the brief, the ledger, tries, frozen versions, refused calls |
| `homebase/claude_mcp/mission.py` | new | `MissionToolbox`: allowlist + guards over `Toolbox` |
| `homebase/claude_mcp/protocol.py` | modify `Server`, `main()` | `--mission <id>`; mission instructions; unknown-tool hook |
| `research/edge-library/blueprint/missionacct.py` | new | The owner's prop accounts: list, resolve, facts, bans |
| `research/edge-library/blueprint/missionjudge.py` | new | Box re-run, sizing, eval odds, charges, tries, gate, reach, the read |
| `research/edge-library/blueprint/missiondoor.py` | new | The Judge's CLI (JSON out) |
| `research/edge-library/missions/judge` | new | The bash door (like `hunt/bp`) |
| `CLAUDE.md` | modify | One Missions paragraph |
| Tests | new | `tests/test_missions_state.py`, `tests/test_claude_mcp_mission.py`, `research/edge-library/tests/test_mission_accounts.py`, `research/edge-library/tests/test_mission_judge.py`, `research/edge-library/tests/test_mission_door.py` |

---

### Task 1: Mission state

**Files:**
- Create: `homebase/missions.py`
- Test: `tests/test_missions_state.py`

**Interfaces:**
- Consumes: `homebase.paths.from_env(env, *default) -> Path`.
- Produces (used by Tasks 2, 5, 6):
  - `ENV = "HOMEBASE_MISSIONS"`; `root() -> Path` (default `~/.homebase/missions`)
  - `class MissionError(ValueError)`
  - `validate_id(mid) -> int`; `mission_dir(mid) -> Path`; `prefix(mid) -> str` (`"m7_"`)
  - `brief(mid) -> dict`: `{id, approved, owner_said, test_months: "team"|"ask", goal: {kind: "eval"|"points"|"net", target: float, rule: str|None}}`
  - `spec_hash(spec: dict) -> str` (16 hex)
  - `record(mid, kind, ref, spec=None, *, hash=None) -> dict`; kinds `"run"`, `"job"`, `"wf"`, `"card"`, `"draft"`, `"read"`
  - `ledger(mid) -> list[dict]`; `owns(mid, kind, ref) -> bool`; `tries(mid) -> int`
  - `freeze(mid, name, h) -> None`; `frozen(mid) -> dict[str, str]` (name → the version's settings id)
  - `refused(mid, tool, args, why) -> None`

- [ ] **Step 1: Write the failing tests** in `tests/test_missions_state.py`

```python
"""homebase.missions: mission state (the brief, the ledger, tries, frozen versions, refused calls)."""
import json

import pytest

from homebase import missions as M

GOAL = {"kind": "points", "target": 3.0}


@pytest.fixture(autouse=True)
def _root(tmp_path, monkeypatch):
    monkeypatch.setenv(M.ENV, str(tmp_path))


def write_brief(mid, **over):
    b = {"approved": True, "owner_said": "run it until the goal (test brief)", "test_months": "team", "goal": GOAL, **over}
    d = M.mission_dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.json").write_text(json.dumps(b))


def test_ids_are_positive_integers():
    assert M.validate_id(7) == 7 and M.validate_id("7") == 7
    for bad in (0, -1, True, "7a", None, 1.5, "", "٣"):
        with pytest.raises(M.MissionError):
            M.validate_id(bad)
    assert M.prefix(7) == "m7_" and M.mission_dir(7).name == "7"


def test_brief_must_be_approved_and_complete():
    with pytest.raises(M.MissionError, match="no brief"):
        M.brief(8)
    write_brief(7, approved=False)
    with pytest.raises(M.MissionError, match="not approved"):
        M.brief(7)
    write_brief(7, owner_said="  ")
    with pytest.raises(M.MissionError, match="owner_said"):
        M.brief(7)
    write_brief(7, test_months="maybe")
    with pytest.raises(M.MissionError, match="test_months"):
        M.brief(7)
    write_brief(7, goal={"kind": "sharpe", "target": 2})
    with pytest.raises(M.MissionError, match="goal.kind"):
        M.brief(7)
    write_brief(7)
    assert M.brief(7) == {"id": 7, "approved": True, "owner_said": "run it until the goal (test brief)", "test_months": "team",
                          "goal": {"kind": "points", "target": 3.0, "rule": None}}


def test_an_eval_goal_names_its_account_and_a_fraction():
    write_brief(7, goal={"kind": "eval", "target": 0.5})
    with pytest.raises(M.MissionError, match="goal.rule"):
        M.brief(7)
    write_brief(7, goal={"kind": "eval", "target": 50, "rule": "topstep-50k@2026-11-14"})
    with pytest.raises(M.MissionError, match="fraction"):
        M.brief(7)
    write_brief(7, goal={"kind": "eval", "target": 0.5, "rule": "topstep-50k@2026-11-14"})
    assert M.brief(7)["goal"] == {"kind": "eval", "target": 0.5, "rule": "topstep-50k@2026-11-14"}


def test_spec_hash_ignores_key_order():
    assert M.spec_hash({"a": 1, "b": [1, 2]}) == M.spec_hash({"b": [1, 2], "a": 1}) != M.spec_hash({"a": 2, "b": [1, 2]})
    assert len(M.spec_hash({})) == 16


def test_tries_count_distinct_specs_of_runs_tables_and_reads():
    M.record(7, "run", "r1", {"a": 1})
    M.record(7, "run", "r2", {"a": 1})                 # the same spec twice = 1 try
    M.record(7, "wf", "m7_v01", {"a": 2})
    M.record(7, "draft", "m7_d", {"a": 3})             # a draft, a card and a job are not tries
    M.record(7, "card", "m7_v01", {"a": 4})
    M.record(7, "job", "j1")
    assert M.tries(7) == 2
    M.record(7, "read", "m7_v01", hash="abc")          # a test-month read is a try
    assert M.tries(7) == 3
    assert M.owns(7, "run", "r2") and not M.owns(7, "run", "r9") and not M.owns(7, "job", "r2")
    assert [r["kind"] for r in M.ledger(7)] == ["run", "run", "wf", "draft", "card", "job", "read"]
    with pytest.raises(M.MissionError):
        M.record(7, "trade", "x")


def test_one_mission_never_reads_another():
    M.record(7, "run", "r1", {"a": 1})
    assert not M.owns(8, "run", "r1") and M.tries(8) == 0


def test_freeze_is_kept_and_a_broken_file_fails_closed():
    assert M.frozen(7) == {}
    M.freeze(7, "m7_v01", "abc")
    M.freeze(7, "m7_v02", "def")
    assert M.frozen(7) == {"m7_v01": "abc", "m7_v02": "def"}
    (M.mission_dir(7) / "frozen.json").write_text("{not json")
    with pytest.raises(M.MissionError, match="frozen"):
        M.frozen(7)


def test_refused_calls_are_logged_and_a_torn_ledger_line_is_skipped():
    M.refused(7, "backtest", {"range": "x"}, "range is not open to a mission")
    row = json.loads((M.mission_dir(7) / "refused.jsonl").read_text().strip())
    assert row["tool"] == "backtest" and row["args"] == {"range": "x"} and "not open" in row["why"]
    M.record(7, "run", "r1", {"a": 1})
    with open(M.mission_dir(7) / "ledger.jsonl", "a") as fh:
        fh.write('{"kind": "run", "ref"')
    assert M.owns(7, "run", "r1") and M.tries(7) == 1
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/test_missions_state.py -v`
Expected: FAIL (`ImportError: cannot import name 'missions' from 'homebase'`)

- [ ] **Step 3: Write `homebase/missions.py`**

```python
"""Mission state for the Missions app (the owner, 2026-11-14): one folder a mission, ~/.homebase/missions/<id>/.

    brief.json      written by the Missions app when the owner approves a mission; read here, never written
    ledger.jsonl    one line per thing the mission started or made: {"at", "kind", "ref", "hash"}
    frozen.json     {version name: its settings id}: versions whose test months were read; never run or read again
    refused.jsonl   one line per call the fence refused: {"at", "tool", "args", "why"}
    reads/<name>.json   the owner's numbers of a test-month read (written by the Judge, research/edge-library/blueprint/missionjudge.py)

Read by the connector's mission mode (homebase/claude_mcp/mission.py) and by the Judge. Standard library only.
Several workers write at once: every write holds the mission's lock file."""
from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path

from . import paths

ENV = "HOMEBASE_MISSIONS"
KINDS = ("run", "job", "wf", "card", "draft", "read")
TRY_KINDS = ("run", "wf", "read")       # a try = a distinct spec that was run (a backtest, an in-sample table) or a test-month read
GOALS = ("eval", "points", "net")
TEST_MONTHS = ("team", "ask")           # team: the Judge reads on the brief's words; ask: the owner's words for every read


class MissionError(ValueError):
    pass


def root() -> Path:
    return paths.from_env(ENV, ".homebase", "missions")


def validate_id(mid) -> int:
    s = str(mid)
    if isinstance(mid, bool) or not isinstance(mid, (int, str)) or not (s.isascii() and s.isdigit()) or int(s) < 1:
        raise MissionError(f"mission id {mid!r}: a whole number from 1")
    return int(s)


def mission_dir(mid) -> Path:
    return root() / str(validate_id(mid))


def prefix(mid) -> str:
    """What every name of this mission starts with: m7_ (a draft of it is listed as draft_m7_...)."""
    return f"m{validate_id(mid)}_"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def brief(mid) -> dict:
    """The mission's approved brief. MissionError: none on file, not approved by the owner, or not complete."""
    f = mission_dir(mid) / "brief.json"
    try:
        b = json.loads(f.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise MissionError(f"mission {mid}: no brief on file ({f})") from None
    except (OSError, ValueError) as e:
        raise MissionError(f"mission {mid}: its brief cannot be read ({e})") from None
    if not isinstance(b, dict) or b.get("approved") is not True:
        raise MissionError(f"mission {mid}: its brief is not approved by the owner")
    said = b.get("owner_said")
    if not isinstance(said, str) or not said.strip():
        raise MissionError(f"mission {mid}: its brief has no owner_said (the owner's words that start it)")
    if b.get("test_months") not in TEST_MONTHS:
        raise MissionError(f"mission {mid}: test_months is {' or '.join(TEST_MONTHS)}")
    g = b.get("goal")
    if not isinstance(g, dict) or g.get("kind") not in GOALS:
        raise MissionError(f"mission {mid}: goal.kind is one of {', '.join(GOALS)}")
    t = g.get("target")
    if isinstance(t, bool) or not isinstance(t, (int, float)):
        raise MissionError(f"mission {mid}: goal.target is a number")
    if g["kind"] == "eval":
        if not isinstance(g.get("rule"), str) or not g["rule"]:
            raise MissionError(f"mission {mid}: an eval goal names its account (goal.rule)")
        if not 0 < t <= 1:
            raise MissionError(f"mission {mid}: an eval goal's target is a fraction (0.5 = a 50 % pass rate)")
    return {"id": validate_id(mid), "approved": True, "owner_said": said.strip(), "test_months": b["test_months"],
            "goal": {"kind": g["kind"], "target": float(t), "rule": g.get("rule")}}


def spec_hash(spec: dict) -> str:
    """A spec's identity: the same settings in any key order are the same try."""
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:16]


@contextlib.contextmanager
def _locked(mid):
    d = mission_dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / ".lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield d


def _lines(mid, name: str) -> list:
    f = mission_dir(mid) / name
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue                    # a torn line (a crash mid-write) is skipped, never fatal
        if isinstance(row, dict):
            out.append(row)
    return out


def _append(d: Path, name: str, row: dict) -> None:
    with open(d / name, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def record(mid, kind: str, ref, spec: dict | None = None, *, hash: str | None = None) -> dict:  # noqa: A002
    """One ledger line. `spec` = what was run (hashed), or `hash` = its identity when the caller already has one."""
    if kind not in KINDS:
        raise MissionError(f"kind {kind!r}: one of {', '.join(KINDS)}")
    row = {"at": _now(), "kind": kind, "ref": str(ref), "hash": hash if spec is None else spec_hash(spec)}
    with _locked(mid) as d:
        _append(d, "ledger.jsonl", row)
    return row


def ledger(mid) -> list:
    return _lines(mid, "ledger.jsonl")


def owns(mid, kind: str, ref) -> bool:
    return any(r.get("kind") == kind and r.get("ref") == str(ref) for r in ledger(mid))


def tries(mid) -> int:
    """How many tries this mission has used: the distinct specs it ran, and its test-month reads."""
    return len({r["hash"] for r in ledger(mid) if r.get("kind") in TRY_KINDS and r.get("hash")})


def frozen(mid) -> dict:
    """{version name: its settings id}. A file that cannot be read is an error, never "nothing is frozen"."""
    f = mission_dir(mid) / "frozen.json"
    try:
        got = json.loads(f.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        raise MissionError(f"mission {mid}: its frozen list cannot be read ({e}): nothing runs until it is repaired") from None
    if not isinstance(got, dict):
        raise MissionError(f"mission {mid}: its frozen list is not a table: nothing runs until it is repaired")
    return got


def freeze(mid, name: str, h: str) -> None:
    with _locked(mid) as d:
        got = frozen(mid)
        got[str(name)] = str(h)
        tmp = d / "frozen.json.tmp"
        tmp.write_text(json.dumps(got, sort_keys=True, indent=1), encoding="utf-8")
        tmp.replace(d / "frozen.json")


def refused(mid, tool: str, args, why: str) -> None:
    with _locked(mid) as d:
        _append(d, "refused.jsonl", {"at": _now(), "tool": str(tool), "args": args, "why": str(why)})
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/test_missions_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homebase/missions.py tests/test_missions_state.py
git commit -m "Missions: mission state (brief, ledger, tries, frozen versions, refused calls)"
```

---

### Task 2: The connector's mission mode

**Files:**
- Create: `homebase/claude_mcp/mission.py`
- Modify: `homebase/claude_mcp/protocol.py` (`Server.__init__`, the `initialize` and `tools/call` branches of `Server.handle`, `main`)
- Test: `tests/test_claude_mcp_mission.py`

**Interfaces:**
- Consumes: Task 1 (`brief`, `prefix`, `record`, `ledger`, `owns`, `frozen`, `refused`); `tools.Toolbox` (`specs`, `names`, `call`, `_post_run(body) -> run_id`, `_catalog()`, `c.get`, `t_read_strategy`), `tools._table`, `tools._usd`; `BlueprintMixin._bp(args, *, stdin, timeout, root) -> dict` (its result carries `job: {id, state}` for a job); `draftstore.PREFIX` (`"draft_"`), `draftstore.is_draft_id`, `draftstore.draft_id`, `draftstore.path_for(name)`, `draftstore.DRAFT_TEMPLATE`; `client.ToolError`.
- Produces: `ALLOW: frozenset[str]`; `class MissionToolbox(tools.Toolbox)` with `__init__(self, mid, **kw)`, `.mid`, `specs()`, `names()`, `call(name, args)`, `on_unknown(name, args)`; `instructions(mid) -> str`; `protocol.Server(toolbox=None, instructions=None)`; `protocol._mission_arg(argv) -> str | None`; `protocol.main(argv=None) -> int`.

What each allowed tool is held to (a guard refuses with `ToolError`, and the refusal is logged through `missions.refused` first):

| Tool | Guard |
|---|---|
| `list_strategies`, `list_prop_rules`, `blueprint_blocks` | none |
| `read_strategy` | only this mission's drafts (`draft_m<id>_*`); a draft that is not written yet answers with the draft template |
| `write_strategy`, `delete_draft` | `name` has the prefix; `write_strategy` records `"draft"` |
| `set_group` | `strategy` is this mission's draft |
| `backtest` | `range`, `runs`, `run_ids` refused; `owner_said` dropped; a new run's `strategy` is this mission's draft; a `run_id` (waiting on a run) must be owned |
| `get_run`, `trades`, `montecarlo`, `prop_eval`, `day_types`, `cancel` | `run_id` must be owned; `grid_id`, `cell`, `walkforward_id`, `box` refused |
| `list_runs` | `kind` is `runs`; only owned runs are listed |
| `blueprint_card` | `name` has the prefix; records `"card"` |
| `blueprint_code_check` | `name` has the prefix; `store` and `trades_file` refused |
| `blueprint_wf` | `name` or `card["name"]` has the prefix; `owner_said` is replaced by the brief's `owner_said`, whatever the worker sent; records `"wf"` (a try) |
| `blueprint_status` | `name` has the prefix, or `job_id` is owned; neither = refused (it would list every idea) |
| `blueprint_heatmap` | `name` has the prefix |
| `blueprint_mc` | `name` has the prefix; `on` is always sent as `build` (`test` refused) |
| any of the above | a name that is frozen is refused ("already read") |

Everything else (`heatmap`, `walkforward`, `show_on_chart`, `blueprint_wf_pick`, `blueprint_wf_oos`, `blueprint_sim`,
`blueprint_portfolio`, `blueprint_eval_card`, every `desk_*`, `data_coverage`, `services_health`, `account_*`,
`export_*`) is not listed, answers "unknown tool", and the attempt is logged.

- [ ] **Step 1: Write the failing tests** in `tests/test_claude_mcp_mission.py`

```python
"""The connector's mission mode (homebase.claude_mcp.mission): the allowlist, the mission's own names, runs and jobs,
in-sample only, the owner's words taken from the brief, and every refusal logged."""
import json

import pytest

from homebase import missions as M
from homebase.claude_mcp import blueprint_tools, protocol
from homebase.claude_mcp import mission as MI
from homebase.claude_mcp.client import Client, ToolError
from tests.test_claude_mcp import BUNDLE, CATALOG, RID, fake, rpc  # noqa: F401  (fake: the fake chart service fixture)

BRIEF = {"approved": True, "owner_said": "run this mission until the goal (the owner, test brief)", "test_months": "team",
         "goal": {"kind": "points", "target": 3.0}}
DRAFT = "draft_m7_d"
CARD = {"family": "orb", "markets": ["NQ"], "bar_sizes": ["15"], "sessions": ["nyam"]}


def write_brief(mid, **over):
    d = M.mission_dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.json").write_text(json.dumps({**BRIEF, **over}))


def refused_log(mid) -> str:
    f = M.mission_dir(mid) / "refused.jsonl"
    return f.read_text() if f.exists() else ""


@pytest.fixture(autouse=True)
def _missions(tmp_path, monkeypatch):
    monkeypatch.setenv(M.ENV, str(tmp_path / "missions"))
    write_brief(7)


@pytest.fixture
def mbox(fake):  # noqa: F811
    fake.routes[("GET", "/api/tester/strategies")] = CATALOG + [{"id": DRAFT, "name": "d", "root": "NQ", "draft": True, "inputs": []}]
    return MI.MissionToolbox(7, client=Client(fake.url), sleep=lambda s: None)


@pytest.fixture
def bp_calls(monkeypatch):
    """The blueprint toolkit is never started: each command is recorded and answered as a job that is still going."""
    calls = []

    def fake_bp(self, args, *, stdin=None, timeout=0.0, root=None):
        calls.append({"args": list(args), "stdin": stdin})
        return {"ok": True, "command": " ".join(args[:2]), "job": {"id": f"j{len(calls)}", "state": "running", "progress": "1/120"}}

    monkeypatch.setattr(blueprint_tools.BlueprintMixin, "_bp", fake_bp)
    return calls


def test_lists_only_the_allowlist(mbox):
    assert set(mbox.names()) == MI.ALLOW
    assert {s["name"] for s in mbox.specs()} == MI.ALLOW
    for name in ("blueprint_wf_oos", "blueprint_wf_pick", "desk_status", "heatmap", "walkforward", "show_on_chart", "account_remove"):
        assert name not in mbox.names()


def test_an_unlisted_tool_is_unknown_and_the_attempt_is_logged(mbox):
    srv = protocol.Server(mbox, MI.instructions(7))
    got = rpc(srv, "tools/call", {"name": "blueprint_wf_oos", "arguments": {"name": "m7_v01", "box": "1", "owner_said": "x"}})
    assert got["error"]["code"] == -32602 and "blueprint_wf_oos" in refused_log(7)
    with pytest.raises(ToolError, match="unknown tool"):
        mbox.call("desk_status", {})
    assert "MISSION MODE" in rpc(srv, "initialize", {})["result"]["instructions"]
    assert {t["name"] for t in rpc(srv, "tools/list")["result"]["tools"]} == MI.ALLOW


def test_refuses_other_missions_and_plain_ideas(mbox, bp_calls):
    for name in ("m3_x", "owner_fvg_odir_15_nl_new", "m70_x", None):
        with pytest.raises(ToolError, match="not this mission"):
            mbox.call("blueprint_heatmap", {"name": name})
    assert not bp_calls and refused_log(7).count("blueprint_heatmap") == 4
    mbox.call("blueprint_heatmap", {"name": "m7_v01"})
    assert bp_calls[-1]["args"][:2] == ["heatmap", "m7_v01"]


def test_backtest_range_and_batches_are_closed(mbox, fake):  # noqa: F811
    for extra in ({"range": {"start": "2025-07-01", "end": "2025-08-01"}}, {"runs": [{}]}, {"run_ids": ["r1"]}):
        with pytest.raises(ToolError, match="not open to a mission"):
            mbox.call("backtest", {"strategy": DRAFT, **extra})
    for sid in ("nq930", "draft_m3_d", "m7_d"):
        with pytest.raises(ToolError, match="not this mission"):
            mbox.call("backtest", {"strategy": sid})
    assert not [r for r in fake.requests if r["method"] == "POST"]


def test_backtest_records_its_run_and_views_need_an_owned_run(mbox, fake):  # noqa: F811
    mbox.call("backtest", {"strategy": DRAFT, "owner_said": "run all data", "wait_s": 0})
    assert fake.last("POST")["body"]["range"] == {"kind": "wf_is", "root": "NQ"}      # nothing a worker says opens a range
    assert M.owns(7, "run", RID) and M.tries(7) == 1
    mbox.call("backtest", {"strategy": DRAFT, "wait_s": 0})                             # the same spec again: no new try
    assert M.tries(7) == 1
    assert mbox.call("get_run", {"run_id": RID})                                        # its own run: shown
    mbox.call("backtest", {"run_id": RID, "wait_s": 0})
    for tool in ("get_run", "trades", "montecarlo", "day_types", "cancel"):
        with pytest.raises(ToolError, match="not this mission"):
            mbox.call(tool, {"run_id": "someone-elses"})
    with pytest.raises(ToolError, match="not open to a mission"):
        mbox.call("get_run", {"grid_id": "g1", "cell": 1})
    with pytest.raises(ToolError, match="not this mission"):
        mbox.call("backtest", {"run_id": "someone-elses"})


def test_a_changed_draft_under_the_same_name_is_a_new_try(mbox, fake, drafts_dir):  # noqa: F811
    mbox.call("backtest", {"strategy": DRAFT, "wait_s": 0})
    (drafts_dir / "m7_d.py").write_text("# version 2 of the code\n")
    fake.routes.update({("POST", "/api/tester/run"): {"id": "run-2"}, ("GET", "/api/tester/run/run-2"): {"id": "run-2", "status": "done"},
                        ("GET", "/api/tester/run/run-2/bundle"): BUNDLE})
    mbox.call("backtest", {"strategy": DRAFT, "wait_s": 0})                             # the same inputs, new code: a new try
    assert M.owns(7, "run", "run-2") and M.tries(7) == 2
    fake.routes.update({("POST", "/api/tester/run"): {"id": "run-3"}, ("GET", "/api/tester/run/run-3"): {"id": "run-3", "status": "done"},
                        ("GET", "/api/tester/run/run-3/bundle"): BUNDLE})
    mbox.call("backtest", {"strategy": DRAFT, "wait_s": 0})                             # the same code and inputs again: no new try
    assert M.owns(7, "run", "run-3") and M.tries(7) == 2


def test_list_runs_shows_only_this_missions_runs(mbox, fake):  # noqa: F811
    fake.routes[("GET", "/api/tester/runs")] = [{"id": RID, "strategy": DRAFT, "status": "done", "range": {"label": "R"}, "trades": 2, "net_profit": 187.0},
                                                {"id": "other-run", "strategy": "nq930", "status": "done", "range": {"label": "R"}, "trades": 9, "net_profit": 1.0}]
    assert mbox.call("list_runs", {}) == "No runs."
    mbox.call("backtest", {"strategy": DRAFT, "wait_s": 0})
    out = mbox.call("list_runs", {})
    assert RID in out and "other-run" not in out
    with pytest.raises(ToolError, match="its own runs"):
        mbox.call("list_runs", {"kind": "walkforwards"})


def test_drafts_are_this_missions_only(mbox):
    for tool, args in (("write_strategy", {"name": "nq_orb_15", "code": "x"}), ("delete_draft", {"name": "m3_d"}),
                       ("set_group", {"strategy": "nq930", "group": "g"}), ("read_strategy", {"strategy": "nq930"}),
                       ("read_strategy", {"strategy": "draft_m3_d"})):
        with pytest.raises(ToolError, match="not this mission"):
            mbox.call(tool, args)
    assert "DRAFT TEMPLATE" in mbox.call("read_strategy", {"strategy": "draft_m7_new"})


def test_wf_uses_the_briefs_words_and_counts_a_try(mbox, bp_calls):
    mbox.call("blueprint_wf", {"card": {**CARD, "name": "m7_v01"}, "owner_said": "anything a worker types"})
    assert f"--owner-said={BRIEF['owner_said']}" in bp_calls[-1]["args"]
    assert M.owns(7, "wf", "m7_v01") and M.owns(7, "job", "j1") and M.tries(7) == 1
    mbox.call("blueprint_wf", {"card": {**CARD, "name": "m7_v02"}, "owner_said": "x"})      # the same settings, a new name: the same try
    assert M.tries(7) == 1
    mbox.call("blueprint_wf", {"card": {**CARD, "sessions": ["lon"], "name": "m7_v03"}, "owner_said": "x"})
    assert M.tries(7) == 2
    with pytest.raises(ToolError, match="not this mission"):
        mbox.call("blueprint_wf", {"card": {**CARD, "name": "m3_v01"}, "owner_said": "x"})


def test_a_card_then_wf_by_name_counts_the_cards_settings(mbox, bp_calls):
    mbox.call("blueprint_card", {"name": "m7_v05", "card": {"what": "x"}, "settings": {"family": "orb"}})
    assert M.owns(7, "card", "m7_v05") and M.tries(7) == 0
    mbox.call("blueprint_wf", {"name": "m7_v05", "owner_said": "x"})
    assert M.tries(7) == 1 and bp_calls[-1]["args"][:3] == ["wf", "run", "m7_v05"]


def test_status_is_this_missions_ideas_and_jobs_only(mbox, bp_calls):
    with pytest.raises(ToolError, match="every idea"):
        mbox.call("blueprint_status", {})
    with pytest.raises(ToolError, match="not this mission"):
        mbox.call("blueprint_status", {"job_id": "j9"})
    mbox.call("blueprint_wf", {"card": {**CARD, "name": "m7_v01"}, "owner_said": "x"})
    mbox.call("blueprint_status", {"job_id": "j1"})
    mbox.call("blueprint_status", {"name": "m7_v01"})
    assert bp_calls[-1]["args"] == ["status", "m7_v01"]


def test_a_frozen_version_is_closed_everywhere(mbox, bp_calls):
    M.freeze(7, "m7_v01", "abc")
    for tool, args in (("blueprint_heatmap", {"name": "m7_v01"}), ("blueprint_status", {"name": "m7_v01"}), ("blueprint_mc", {"name": "m7_v01"}),
                       ("blueprint_wf", {"name": "m7_v01", "owner_said": "x"}), ("write_strategy", {"name": "m7_v01", "code": "x"})):
        with pytest.raises(ToolError, match="already read"):
            mbox.call(tool, args)
    assert not bp_calls


def test_mc_is_in_sample_only_and_code_check_reads_only_the_ideas_own_store(mbox, bp_calls):
    with pytest.raises(ToolError, match="not open to a mission"):
        mbox.call("blueprint_mc", {"name": "m7_v01", "on": "test"})
    mbox.call("blueprint_mc", {"name": "m7_v01"})
    assert "--on=build" in bp_calls[-1]["args"]
    for extra in ({"store": "owner_fvg-NQ-tf15"}, {"trades_file": "/tmp/t.csv"}):
        with pytest.raises(ToolError, match="not open to a mission"):
            mbox.call("blueprint_code_check", {"name": "m7_v01", **extra})
    mbox.call("blueprint_code_check", {"name": "m7_v01", "looked": True})
    assert bp_calls[-1]["args"] == ["code-check", "m7_v01", "--looked"]


def test_no_approved_brief_no_server(monkeypatch):
    write_brief(9, approved=False)
    with pytest.raises(M.MissionError):
        MI.MissionToolbox(9)
    assert protocol._mission_arg(["--mission", "7"]) == "7" and protocol._mission_arg(["--mission=7"]) == "7"
    assert protocol._mission_arg([]) is None
    assert protocol.main(["--mission", "9"]) == 2 and protocol.main(["--mission", "x"]) == 2
```

`drafts_dir` is the autouse fixture of `tests/conftest.py` (a fresh temp drafts folder a test).

- [ ] **Step 2: Run them to make sure they fail**

Run: `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/test_claude_mcp_mission.py -v`
Expected: FAIL (`ImportError: cannot import name 'mission'`)

- [ ] **Step 3: Write `homebase/claude_mcp/mission.py`**

```python
"""The connector's MISSION MODE (the owner, 2026-11-14): `python -m homebase.claude_mcp --mission <id>`.

A Missions worker gets this server instead of the plain one. It lists only ALLOW, and every call is held to the
mission's own names (m<id>_*, drafts draft_m<id>_*), its own runs and jobs (the mission ledger, homebase/missions.py)
and the 3:1 in-sample months. The test months belong to the Missions Judge (research/edge-library/missions/judge):
no tool here reads one. A refused call is logged (missions.refused) and answered as a normal tool error."""
from __future__ import annotations

import hashlib

from .. import missions
from ..store import draftstore
from . import tools
from .client import ToolError

ALLOW = frozenset({
    "list_strategies", "list_prop_rules", "blueprint_blocks",
    "read_strategy", "write_strategy", "delete_draft", "set_group",
    "backtest", "get_run", "trades", "montecarlo", "prop_eval", "day_types", "cancel", "list_runs",
    "blueprint_card", "blueprint_code_check", "blueprint_wf", "blueprint_status", "blueprint_heatmap", "blueprint_mc",
})
RUN_VIEWS = frozenset({"get_run", "trades", "montecarlo", "prop_eval", "day_types", "cancel"})
NOT_RUN = ("grid_id", "cell", "walkforward_id", "box")      # the ways a view names something that is not one run
CLOSED = "is not open to a mission"


def instructions(mid) -> str:
    p = missions.prefix(mid)
    return (f"Homebase Strategy Tester, MISSION MODE (mission {missions.validate_id(mid)}). You work for one mission. Every draft and "
            f"idea you make is named {p}<something> (a draft is listed as draft_{p}<something>); other names are refused. backtest "
            "runs one run at a time, on the 3:1 in-sample months only; get_run, trades, montecarlo, prop_eval, day_types and cancel "
            "take the run_id of a run this mission started. For an idea built from the blocks: blueprint_blocks, blueprint_card, "
            "blueprint_code_check, blueprint_wf (the in-sample table of every hm40 box; the owner's words come from the mission's "
            "brief), blueprint_status, blueprint_heatmap, blueprint_mc. Every run and table you start counts as a try and raises the "
            "luck bar. The test months are read only by the Missions Judge, once a version: no tool here reads one, and a version "
            f"that was read is frozen (a change is a new name). read_strategy(strategy='draft_{p}<a new name>') shows the draft "
            "template. The strategy pipeline is off.")


class MissionToolbox(tools.Toolbox):
    def __init__(self, mid, **kw):
        super().__init__(**kw)
        self.mid = missions.validate_id(mid)
        self.brief = missions.brief(self.mid)           # MissionError: no approved brief, no server
        self.prefix = missions.prefix(self.mid)

    def specs(self) -> list[dict]:
        return [s for s in super().specs() if s["name"] in ALLOW]

    def names(self) -> list[str]:
        return [s["name"] for s in self.specs()]

    def on_unknown(self, name, args) -> None:
        """A tool that is not a mission's (the protocol answers "unknown tool"): the attempt is kept for the owner."""
        missions.refused(self.mid, str(name), args, "not a tool of a mission")

    def call(self, name: str, args: dict) -> str:
        if name not in ALLOW:
            self.on_unknown(name, args)
            raise ToolError(f"unknown tool {name!r}")
        try:
            args = self._guard(name, dict(args))
        except ToolError as e:
            missions.refused(self.mid, name, args, str(e))
            raise
        out = super().call(name, args)
        self._after(name, args)
        return out

    # ---- whose it is

    def _mine(self, name, what: str = "name") -> str:
        """A draft's or an idea's name of this mission (m<id>_...) that was not read on its test months."""
        if not isinstance(name, str) or not name.startswith(self.prefix):
            raise ToolError(f"{what} {name!r}: not this mission's (its names start with {self.prefix!r})")
        if name in missions.frozen(self.mid):
            raise ToolError(f"{name}: already read on its test months: frozen (a change is a new version name)")
        return name

    def _my_draft(self, sid) -> str:
        """A strategy id of this mission: draft_m<id>_..."""
        if not draftstore.is_draft_id(sid):
            raise ToolError(f"strategy {sid!r}: not this mission's (its drafts are {draftstore.draft_id(self.prefix)}...)")
        self._mine(sid[len(draftstore.PREFIX):], "strategy")
        return sid

    def _my_run(self, tool: str, a: dict) -> None:
        for k in NOT_RUN:
            if a.get(k) is not None:
                raise ToolError(f"{tool}: {k} {CLOSED} (its own runs only: run_id)")
        if a.get("run_id") is None or not missions.owns(self.mid, "run", a["run_id"]):
            raise ToolError(f"{tool}: run {a.get('run_id')!r} is not this mission's")

    # ---- the guards (each returns the arguments the tool is called with)

    def _guard(self, name: str, a: dict) -> dict:
        if name in RUN_VIEWS:
            self._my_run(name, a)
        elif name == "backtest":
            for k in ("range", "runs", "run_ids"):
                if a.get(k) is not None:
                    raise ToolError(f"backtest: {k} {CLOSED} (one run at a time, on the 3:1 in-sample months)")
            a.pop("owner_said", None)                   # nothing a worker says opens a range
            if a.get("run_id") is not None:
                if not missions.owns(self.mid, "run", a["run_id"]):
                    raise ToolError(f"backtest: run {a['run_id']!r} is not this mission's")
            else:
                self._my_draft(a.get("strategy"))
        elif name == "list_runs":
            if a.get("kind", "runs") != "runs":
                raise ToolError("list_runs: a mission lists its own runs only (kind: runs)")
        elif name in ("read_strategy", "set_group"):
            self._my_draft(a.get("strategy"))
        elif name in ("write_strategy", "delete_draft", "blueprint_card", "blueprint_heatmap"):
            self._mine(a.get("name"))
        elif name == "blueprint_code_check":
            self._mine(a.get("name"))
            for k in ("store", "trades_file"):
                if a.get(k) is not None:
                    raise ToolError(f"blueprint_code_check: {k} {CLOSED} (it checks the idea's own in-sample store)")
        elif name == "blueprint_wf":
            card = a.get("card")
            self._mine(a["name"] if a.get("name") is not None else card.get("name") if isinstance(card, dict) else None)
            a["owner_said"] = self.brief["owner_said"]  # the owner's words for a mission's tables are the brief's, whatever a worker sent
        elif name == "blueprint_status":
            if a.get("job_id") is not None:
                if not missions.owns(self.mid, "job", a["job_id"]):
                    raise ToolError(f"blueprint_status: job {a['job_id']!r} is not this mission's")
            elif a.get("name") is not None:
                self._mine(a["name"])
            else:
                raise ToolError("blueprint_status: give name or job_id (with neither it would list every idea)")
        elif name == "blueprint_mc":
            self._mine(a.get("name"))
            if a.get("on") not in (None, "build"):
                raise ToolError(f"blueprint_mc: on={a['on']!r} {CLOSED} (the in-sample table only)")
            a["on"] = "build"
        return a

    # ---- what a call that ran leaves in the mission ledger

    def _after(self, name: str, a: dict) -> None:
        if name == "write_strategy":
            missions.record(self.mid, "draft", a["name"])
        elif name == "blueprint_card":
            missions.record(self.mid, "card", a["name"], {"card": a["card"], "settings": a["settings"]})
        elif name == "blueprint_wf":
            card = a.get("card")
            if isinstance(card, dict):                  # the settings without the name: a copy under a new name is the same try
                missions.record(self.mid, "wf", card["name"], {k: v for k, v in card.items() if k != "name"})
            else:
                rows = [r for r in missions.ledger(self.mid) if r.get("kind") == "card" and r.get("ref") == a["name"]]
                h = rows[-1]["hash"] if rows else missions.spec_hash({"idea": a["name"]})
                missions.record(self.mid, "wf", a["name"], hash=h)

    def _post_run(self, body: dict) -> str:
        rid = super()._post_run(body)
        if not missions.owns(self.mid, "run", rid):     # (the parent may call itself again without the propsim field)
            spec = {k: v for k, v in body.items() if k not in ("propsim", "prop_rules")}
            try:                                        # a draft's code is part of the try: new code under the same name is a new try
                name = draftstore.name_of(str(body.get("strategy")))
                spec["code"] = hashlib.sha256(draftstore.path_for(name).read_bytes()).hexdigest()[:16]
            except (ValueError, OSError):
                pass
            missions.record(self.mid, "run", rid, spec)
        return rid

    def _bp(self, args: list, **kw) -> dict:
        r = super()._bp(args, **kw)
        job = r.get("job") if isinstance(r, dict) and isinstance(r.get("job"), dict) else {}
        if job.get("id") and not missions.owns(self.mid, "job", job["id"]):
            missions.record(self.mid, "job", job["id"])
        return r

    # ---- two tools a mission sees differently

    def t_read_strategy(self, strategy: str) -> str:
        if not any(s.get("id") == strategy for s in self._catalog()):
            return (f"No draft {strategy} yet: write_strategy(name={strategy[len(draftstore.PREFIX):]!r}, code=...) makes it.\n"
                    "===== DRAFT TEMPLATE (write_strategy follows this) =====\n" + draftstore.DRAFT_TEMPLATE)
        return super().t_read_strategy(strategy)

    def t_list_runs(self, kind: str = "runs", limit: int = 15) -> str:
        mine = {r["ref"] for r in missions.ledger(self.mid) if r.get("kind") == "run"}
        items = [r for r in (self.c.get("/api/tester/runs") or []) if r.get("id") in mine][:max(1, min(int(limit), 50))]
        rows = [[r.get("id"), r.get("strategy"), r.get("status"), (r.get("range") or {}).get("label", ""),
                 r.get("trades", "—"), tools._usd(r.get("net_profit"))] for r in items]
        return tools._table(["run_id", "strategy", "status", "range", "trades", "net $"], rows) if rows else "No runs."
```

- [ ] **Step 4: Wire it into `homebase/claude_mcp/protocol.py`**

`Server.__init__` becomes:

```python
    def __init__(self, toolbox: tools.Toolbox | None = None, instructions: str | None = None):
        self.tools = toolbox or tools.Toolbox()
        self.instructions = instructions or INSTRUCTIONS
```

In `Server.handle`, the `initialize` answer carries `"instructions": self.instructions` (not `INSTRUCTIONS`), and the
unknown-tool branch of `tools/call` tells the toolbox first:

```python
                if name not in self.tools.names():
                    getattr(self.tools, "on_unknown", lambda *_: None)(name, args)      # mission mode keeps the attempt
                    return _error(rid, -32602, f"unknown tool {name!r}")
```

`main` becomes (and `_mission_arg` is added above it):

```python
def _mission_arg(argv) -> str | None:
    """--mission <id> or --mission=<id>; None without it."""
    for i, a in enumerate(argv):
        if a == "--mission":
            return argv[i + 1] if i + 1 < len(argv) else ""
        if a.startswith("--mission="):
            return a.split("=", 1)[1]
    return None


def main(argv=None) -> int:
    mid = _mission_arg(sys.argv[1:] if argv is None else argv)
    if mid is None:
        _log(f"started (chart service {tools.describe_target()})")
        return serve()
    from .. import missions
    from . import mission
    try:
        box = mission.MissionToolbox(mid)
    except missions.MissionError as e:              # no approved brief: no server (the worker then has no connector at all)
        _log(f"mission mode refused: {e}")
        return 2
    _log(f"started in mission mode, mission {box.mid} (chart service {tools.describe_target()})")
    return serve(server=Server(box, mission.instructions(box.mid)))
```

- [ ] **Step 5: Run the tests (new and old)**

Run: `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/test_claude_mcp_mission.py tests/test_claude_mcp.py tests/test_claude_mcp_blueprint.py -v`
Expected: PASS. The old connector tests are untouched by the mission mode; `tests/test_claude_mcp.py` also pins what
words and routes the package may contain, so a failure there is about `mission.py`'s text, not about its logic.

- [ ] **Step 6: Commit**

```bash
git add homebase/claude_mcp/mission.py homebase/claude_mcp/protocol.py tests/test_claude_mcp_mission.py
git commit -m "Missions: connector mission mode (allowlist, own names and runs, in-sample only, wf words from the brief)"
```

---
### Task 3: The owner's prop accounts

The owner's new simulators (main d6f3fe2f, 2026-11-14) are 18 rule files in `homebase/backtest/propsim/rules/*@2026-11-14.json`:
Lucid Maxx 25K/50K, Lucid live 25K/50K, Topstep 50K (+DLL), Apex Legacy 50K/100K/300K, MFFU Builder 100K, MFFU Rapid
25K/50K/100K/150K, MFFU Rapid EOD 25K/50K (+DLL). This task makes them the accounts a mission goal can name.

**Files:**
- Create: `research/edge-library/blueprint/missionacct.py`
- Test: `research/edge-library/tests/test_mission_accounts.py`

**Interfaces:**
- Consumes: `propodds.app()` (the app's propsim module): `list_rules() -> [{"id", "name", "version", "confirmed"}]` (the newest file of each account), `load_rules(rule_id) -> dict` (`ValueError` when there is no such file). Rule file keys used: `name`, `account_size`, `trailing_mll`, `eval_target`, `cap_micros`, `trail` (`"intraday"` on Apex Legacy), `step2`, `funded`, `confirmed`.
- Produces (used by Tasks 4 and 6):
  - `SET = "2026-11-14"`, `RISK_DIV = 2.5`, `CLOSED: dict[str, str]`, `BANS: dict[str, str]`
  - `resolve(rule_id: str) -> str`: the newest file of that account; `J.Refuse` if closed or unknown
  - `facts(rule_id) -> dict`: `{id, name, size, drawdown, risk, target, cap_micros, two_step, funded_rules, intraday, confirmed, bans: [str]}`
  - `accounts() -> list[dict]`: `facts` of every open account (18 today)

- [ ] **Step 1: Write the failing tests** in `research/edge-library/tests/test_mission_accounts.py`

```python
"""blueprint/missionacct.py: the prop accounts a mission goal may name (the 18 rule files of 2026-11-14)."""
import pytest

import judge as J
from blueprint import missionacct as A


def test_the_18_new_accounts_are_open():
    ids = {a["id"] for a in A.accounts()}
    assert len(ids) == 18 and all(i.endswith("@2026-11-14") for i in ids)
    assert {"topstep-50k@2026-11-14", "topstep-50k-dll@2026-11-14", "apex-legacy-50k@2026-11-14", "apex-legacy-300k@2026-11-14",
            "mffu-rapid-eod-50k-dll@2026-11-14", "mffu-rapid-150k@2026-11-14", "mffu-builder-100k@2026-11-14",
            "lucid-maxx-50k@2026-11-14", "lucid-live-25k@2026-11-14"} <= ids


def test_flex_pro_and_anything_outside_the_set_are_closed_in_words():
    with pytest.raises(J.Refuse, match="no Flex"):
        A.resolve("lucid-flex-50k@2026-10-11")
    with pytest.raises(J.Refuse, match="no Pro"):
        A.resolve("lucid-pro-50k@2026-10-11")
    with pytest.raises(J.Refuse, match="not one of the 2026-11-14"):
        A.resolve("apex-eod-50k@2026-10-11")
    for bad in ("nobody-50k@2026-11-14", "", None, 7):
        with pytest.raises(J.Refuse, match="no account"):
            A.resolve(bad)


def test_an_old_version_resolves_to_the_newest_file():
    assert A.resolve("apex-legacy-50k@2026-10-11") == "apex-legacy-50k@2026-11-14"
    assert A.resolve("topstep-50k") == "topstep-50k@2026-11-14"


def test_facts_risk_is_drawdown_over_two_and_a_half_and_bans_are_attached():
    f = A.facts("topstep-50k@2026-11-14")
    assert f["drawdown"] == 2000 and f["risk"] == 800.0 and f["cap_micros"] == 50 and f["size"] == 50000 and f["confirmed"] is False
    assert any("VPS" in b for b in f["bans"]) and f["two_step"] is False and f["intraday"] is False
    assert A.facts("lucid-maxx-25k@2026-11-14")["two_step"] is True
    assert A.facts("apex-legacy-100k@2026-11-14")["intraday"] is True
    assert any("automation" in b for b in A.facts("apex-legacy-100k@2026-11-14")["bans"])
    assert A.facts("mffu-rapid-50k@2026-11-14")["funded_rules"] is True
    assert any("straddles" in b for b in A.facts("mffu-rapid-50k@2026-11-14")["bans"])
    assert any("no new eval" in b for b in A.facts("lucid-live-50k@2026-11-14")["bans"])
```

- [ ] **Step 2: Run them to make sure they fail**

Run (cwd `research/edge-library`): `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_accounts.py -v`
Expected: FAIL (`ImportError: cannot import name 'missionacct'`)

- [ ] **Step 3: Write `research/edge-library/blueprint/missionacct.py`**

```python
"""missionacct.py -- THE PROP ACCOUNTS A MISSION GOAL MAY NAME (the owner, 2026-11-14: "they're specific accounts that I'm planning on
buying").

The 18 rule files of 2026-11-14 in the app's prop simulator (homebase/backtest/propsim/rules/*@2026-11-14.json). An account is open
when it has a file of that set; a goal that names an older file of it gets its newest. Lucid Flex and Lucid Pro are closed in words
(he was moved to Lucid live). Each firm's bans are SHOWN (the brief, the Eval pass page) and never checked by code: news windows,
flat-by times and the other rules the simulator does not run stay the strategy's own job. Nothing here runs the engine."""
from __future__ import annotations

import judge as J

from . import propodds as PO

SET = "2026-11-14"                  # the owner's buying list: an account is open when it has a rule file of this set
RISK_DIV = 2.5                      # a mission's fixed risk a trade on an account = its drawdown / 2.5
CLOSED = {"lucid-flex-": "moved to Lucid live 2026-11-14: no Flex", "lucid-pro-": "moved to Lucid live 2026-11-14: no Pro"}
BANS = {                            # by the start of the account's name; read off the firms' pages (research/edge-library/prop_rules_2026-11-14/)
    "apex-": "Apex bans automation on every account, evals included: a bot cannot trade it inside the rules.",
    "topstep-": "Topstep: a VPS may watch but not place orders: the Chicago Desk cannot trade it.",
    "mffu-": "MFFU bans straddles and strangles on all news, every account; Tier-1 news (FOMC, minutes, NFP, CPI) is banned on Rapid sim funded.",
    "lucid-": "Lucid while live: no new eval of any kind until the live account is blown, plus a 2-week cooldown; no new Maxx while live.",
}


def _account(rule_id) -> str:
    """topstep-50k@2026-10-01 -> topstep-50k"""
    if not isinstance(rule_id, str) or not rule_id.partition("@")[0]:
        raise J.Refuse(f"account {rule_id!r}: no account of that name (`missions/judge accounts` lists them)")
    return rule_id.partition("@")[0]


def _newest() -> dict:
    """{account: its newest rule id} (propsim.list_rules offers the newest version of each)."""
    return {r["id"].partition("@")[0]: r["id"] for r in PO.app().list_rules()}


def _in_set(acct: str) -> bool:
    try:
        PO.app().load_rules(f"{acct}@{SET}")
        return True
    except ValueError:
        return False


def resolve(rule_id) -> str:
    """The rule id a goal runs on: the newest file of the account it names. Refused in words: closed, or no such account."""
    acct = _account(rule_id)
    for start, why in CLOSED.items():
        if acct.startswith(start):
            raise J.Refuse(f"account {acct}: closed ({why})")
    newest = _newest().get(acct)
    if newest is None:
        raise J.Refuse(f"account {rule_id!r}: no account of that name (`missions/judge accounts` lists them)")
    if not _in_set(acct):
        raise J.Refuse(f"account {acct}: closed (not one of the {SET} accounts)")
    return newest


def facts(rule_id) -> dict:
    rid = resolve(rule_id)
    r = PO.app().load_rules(rid)
    dd = float(r["trailing_mll"])
    return {"id": rid, "name": r.get("name") or rid, "size": r.get("account_size"), "drawdown": dd, "risk": dd / RISK_DIV,
            "target": r.get("eval_target"), "cap_micros": r.get("cap_micros"), "two_step": "step2" in r, "funded_rules": bool(r.get("funded")),
            "intraday": r.get("trail") == "intraday", "confirmed": r.get("confirmed") is not False,
            "bans": [text for start, text in BANS.items() if rid.startswith(start)]}


def accounts() -> list:
    """Every open account, a firm at a time, small to large."""
    out = []
    for acct in sorted(_newest()):
        try:
            out.append(facts(acct))
        except J.Refuse:
            continue                # closed
    return sorted(out, key=lambda a: (a["id"].split("-")[0], a["size"] or 0, a["id"]))
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_accounts.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add research/edge-library/blueprint/missionacct.py research/edge-library/tests/test_mission_accounts.py
git commit -m "Missions: the owner's prop accounts (the 18 files of 2026-11-14 open, Flex/Pro closed, bans shown)"
```

---

### Task 4: The picked box's full trades and its eval odds

Why a re-run: the 3:1 stores keep each trade's low (`mae`) but not its high, and `propodds` refuses 12 of the 18 new
accounts (Apex Legacy's intraday trail, Lucid Maxx's two steps, MFFU Rapid's funded block, the Lucid live and Builder
payout day counts). The tester's own `propsim.evaluate` reads all 18, but needs each trade's `mfe_usd`. So the Judge
re-runs the one picked box with the engine's full trade rows, the way `runner.cell_trades` does for charts, but on the
3:1 months, and holds the re-run against the store.

**Files:**
- Create: `research/edge-library/blueprint/missionjudge.py` (this task: the module head, the seams, `box_trades`, `sized_trades`, `eval_odds`)
- Test: `research/edge-library/tests/test_mission_judge.py`

**Interfaces:**
- Consumes: Task 3 (`facts`); `hmwf` as `H` (`store(name) -> Path`, `_load(home, sub=IS, period) -> (unit, meta)`, `is_table(name, home) -> rows`, `_lock(home)`, `_oos(home, rows)`, `_grid(meta, home) -> cells`, `OOS`); `runner` as `RUN` (`_kw(family)`, `worse_kw(two_sided)`, `_engine(kw)`, `_blocks().BASES[family][2]` = two-sided); `run_idea.cell_specs(cell, sessions)`; `run_menus.merge(results) -> {"trades", "skipped_by_error"}`; `l2sim.run_many(specs, days=, root=, workers=, allow_holdout=, **kw)`, `l2sim.ALLOW_WF_IS` / `ALLOW_WF_OOS`; `rules.template("compute")["block_days"]`; `library.pack(trades)`, `library.sized(x, root, risk_usd)` (its `micros`), `library.COMM_RT` (4.00), `MICRO_DIV` (10.0), `MICRO_RT_USD` (1.00); `propodds.app().evaluate(trades, rule_id, *, n_paths, horizon, contract)` (its `headline`, `trail_worst_case`, `size`, `caveat`; `{"skipped": why}` when it cannot run).
- Produces (used by Tasks 5 and 6):
  - `missions()` (the app's `homebase.missions` module); `class Mismatch(J.Refuse)`; `on_server() -> bool`
  - seam `_flag() -> Path`; seam `_box(name, box) -> {"home", "m", "rows", "row", "lock", "oos", "oos_days"}`; seam `_engine_trades(b, days, period, worse, workers) -> list[dict]`
  - `box_trades(name, box, on="is", worse=False, mid=None, workers=4) -> list[dict]`
  - `sized_trades(trades, root, risk_usd, cap_micros) -> list[dict]`
  - `eval_odds(name, box, rule_id, on="is", mid=None, n_paths=None) -> dict`: `{rule, account, risk, on, trades, unsized, pass_p, pass_ci, bust_p, days_to_pass, worst_case_pass_p, size, caveat, confirmed, bans}`

- [ ] **Step 1: Write the failing tests** in `research/edge-library/tests/test_mission_judge.py`

```python
"""blueprint/missionjudge.py: the picked box run again and held to its store, sized to the account, the eval odds on the owner's accounts.
No engine and no store: the seams _box and _engine_trades are replaced."""
import datetime as dt
import json
from pathlib import Path

import pytest

import judge as J
from blueprint import missionacct as A
from blueprint import missionjudge as MJ

M = MJ.missions()
REAL_FAMILY_TRIES = MJ.family_tries          # (Task 5; the autouse fixture below replaces it)
LOCK7 = {"box": "v0_atr1-r1", "who": "mission:7"}


def write_brief(mid=7, **over):
    b = {"approved": True, "owner_said": "run it until the goal (test brief)", "test_months": "team", "goal": {"kind": "points", "target": 3.0}, **over}
    d = M.mission_dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.json").write_text(json.dumps(b))


@pytest.fixture(autouse=True)
def _mission(tmp_path, monkeypatch):
    monkeypatch.setenv(M.ENV, str(tmp_path / "missions"))
    monkeypatch.setenv(MJ.DEAD_ENV, str(tmp_path / "dead.md"))
    monkeypatch.setattr(MJ, "_flag", lambda: tmp_path / "no_backtests")
    monkeypatch.setattr(MJ, "family_tries", lambda family, root="NQ", path=None: 0)
    monkeypatch.setattr(MJ, "_check", lambda name: True)
    write_brief()


def weekdays(n, start="2024-01-02"):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def trade_row(day="2024-03-05", net=96.0, mae=40.0, mfe=200.0, stop_pts=10.0, side="long"):
    """One engine trade row at 1 NQ contract ($20 a point)."""
    ms = int(dt.datetime.fromisoformat(f"{day}T14:35:00+00:00").timestamp() * 1000)
    return {"date": day, "side": side, "qty": 1, "entry_price": 100.0, "sl": 100.0 - stop_pts, "exit_price": 110.0, "exit_reason": "tp",
            "gross": net + 4.0, "commission": 4.0, "net": net, "mae_usd": mae, "mfe_usd": mfe, "seconds": 600.0,
            "entry_ms": ms, "exit_ms": ms + 600_000, "entry_ns": ms * 1_000_000, "exit_ns": (ms + 600_000) * 1_000_000}


def row(**over):
    """One row of an in-sample table that passes real.py's first five lines at 1 try."""
    return {"n": 12, "box": "v0_atr1-r1", "settings": {}, "trades": 300, "net": 9000.0, "t_stat": 3.4, "win_rate": 0.55, "years_n": 6,
            "years_green": 5, "best_year_share": 0.3, "worse_fills_net": 4000.0, "long_net": 5000.0, "short_net": 4000.0, **over}


def fake_box(monkeypatch, family="orb", lock=None, oos=None, oos_days=None, **over):
    r = row(**over)
    b = {"home": Path("/nowhere/m7_v01-NQ-tf15"), "rows": [r, row(n=13, box="v0_atr1-r2", net=100.0)], "row": r, "lock": lock, "oos": oos,
         "oos_days": oos_days,
         "m": {"idea": "m7_v01", "family": family, "root": "NQ", "tf": "15", "sessions": ["nyam"], "days": weekdays(60), "exits": "hm40",
               "fixed": {}, "limits": {}, "variants": {}}}
    monkeypatch.setattr(MJ, "_box", lambda name, box: b)
    return b


def engine(monkeypatch, rows):
    calls = []

    def run(b, days, period, worse, workers):
        calls.append({"period": period, "worse": worse, "days": list(days)})
        return list(rows)

    monkeypatch.setattr(MJ, "_engine_trades", run)
    return calls


# ---------------------------------------------------------------- Task 4: the box run again, sized, raced on an account

def test_box_trades_must_match_the_store(monkeypatch):
    rows = [trade_row(d, net=30.0) for d in weekdays(40)]
    fake_box(monkeypatch, trades=40, net=1200.0)
    calls = engine(monkeypatch, rows)
    assert len(MJ.box_trades("m7_v01", "12")) == 40
    assert calls == [{"period": MJ.S.ALLOW_WF_IS, "worse": False, "days": weekdays(60)}]
    engine(monkeypatch, rows[:39])
    with pytest.raises(MJ.Mismatch, match="differs from its store"):
        MJ.box_trades("m7_v01", "12")
    engine(monkeypatch, rows[:39] + [trade_row(net=25.0)])                   # the same count, one trade a tick off
    with pytest.raises(MJ.Mismatch):
        MJ.box_trades("m7_v01", "12")
    with pytest.raises(J.Refuse, match="is .* or oos"):
        MJ.box_trades("m7_v01", "12", "all")


def test_worse_fills_are_held_to_the_worse_fills_net_on_file(monkeypatch):
    rows = [trade_row(d, net=20.0) for d in weekdays(40)]
    fake_box(monkeypatch, trades=40, net=1200.0, worse_fills_net=800.0)
    calls = engine(monkeypatch, rows)
    assert len(MJ.box_trades("m7_v01", "12", worse=True)) == 40 and calls[-1]["worse"] is True
    fake_box(monkeypatch, worse_fills_net=700.0)
    with pytest.raises(MJ.Mismatch):
        MJ.box_trades("m7_v01", "12", worse=True)
    fake_box(monkeypatch, worse_fills_net=None)
    with pytest.raises(J.Refuse, match="worse-fills run is not on file"):
        MJ.box_trades("m7_v01", "12", worse=True)


def test_test_months_are_run_again_only_after_this_missions_read(monkeypatch):
    rows = [trade_row(d, net=10.0) for d in weekdays(70)]
    oos = {"record": {"trades": 70, "net": 700.0}, "blocks": []}
    engine(monkeypatch, rows)
    for lock in (None, {"box": "v0_atr1-r1", "who": "owner"}, {"box": "v0_atr1-r1", "who": "mission:8"}, {"box": "other", "who": "mission:7"}):
        fake_box(monkeypatch, lock=lock, oos=oos, oos_days=weekdays(70))
        with pytest.raises(J.Refuse, match="read by this mission"):
            MJ.box_trades("m7_v01", "12", "oos", mid=7)
    fake_box(monkeypatch, lock=LOCK7, oos=oos, oos_days=weekdays(70))
    with pytest.raises(J.Refuse, match="read by this mission"):
        MJ.box_trades("m7_v01", "12", "oos")                                 # no mission named
    fake_box(monkeypatch, lock=LOCK7, oos=None)
    with pytest.raises(J.Refuse, match="no test-month record"):
        MJ.box_trades("m7_v01", "12", "oos", mid=7)
    fake_box(monkeypatch, lock=LOCK7, oos={"state": "read used, no record (it stopped)"})
    with pytest.raises(J.Refuse, match="no test-month record"):
        MJ.box_trades("m7_v01", "12", "oos", mid=7)
    fake_box(monkeypatch, lock=LOCK7, oos=oos, oos_days=weekdays(70))
    calls = engine(monkeypatch, rows)
    assert len(MJ.box_trades("m7_v01", "12", "oos", worse=True, mid=7)) == 70
    assert [c["worse"] for c in calls] == [False, True] and {c["period"] for c in calls} == {MJ.S.ALLOW_WF_OOS}     # the plain re-run is held first


def test_sizing_matches_the_library_and_stops_at_the_contract_limit():
    rows = [trade_row(net=96.0, mae=40.0, mfe=200.0, stop_pts=10.0)]         # a 10-point stop = $20 a micro
    s = MJ.sized_trades(rows, "NQ", risk_usd=800.0, cap_micros=50)[0]
    assert s["qty"] == 40 and s["net"] == pytest.approx(40 * ((96.0 + 4.0) / 10 - 1.0))
    assert s["mae_usd"] == pytest.approx(40 * 40.0 / 10) and s["mfe_usd"] == pytest.approx(40 * 200.0 / 10) and s["commission"] == pytest.approx(40.0)
    assert s["date"] == rows[0]["date"] and s["entry_ms"] == rows[0]["entry_ms"] and rows[0]["qty"] == 1      # a copy: the row is not changed
    assert MJ.sized_trades(rows, "NQ", risk_usd=8000.0, cap_micros=50)[0]["qty"] == 50
    assert MJ.sized_trades(rows, "NQ", risk_usd=8000.0, cap_micros=None)[0]["qty"] == 400
    assert MJ.sized_trades([{**rows[0], "sl": None}], "NQ", 800.0, 50) == []  # no stop distance: it cannot be sized


def test_eval_odds_reads_every_kind_of_new_account(monkeypatch):
    rows = [trade_row(d, net=296.0 if i % 3 else -204.0, mae=60.0, mfe=320.0) for i, d in enumerate(weekdays(120))]
    net = sum(t["net"] for t in rows)
    fake_box(monkeypatch, trades=len(rows), net=net, worse_fills_net=net)
    calls = engine(monkeypatch, rows)
    for rid in ("topstep-50k@2026-11-14", "apex-legacy-50k@2026-11-14", "lucid-maxx-50k@2026-11-14", "mffu-rapid-50k@2026-11-14"):
        e = MJ.eval_odds("m7_v01", "12", rid, n_paths=400)
        assert 0.0 <= e["pass_p"] <= 1.0 and 0.0 <= e["bust_p"] <= 1.0 and e["risk"] == A.facts(rid)["risk"] and e["rule"] == rid
        assert e["trades"] == len(rows) and e["unsized"] == 0 and e["confirmed"] is False and e["bans"]
    assert all(c["worse"] for c in calls)                                    # "live is worse" = the worse-fills re-run
    assert MJ.eval_odds("m7_v01", "12", "apex-legacy-50k@2026-11-14", n_paths=400)["worst_case_pass_p"] is not None
    assert MJ.eval_odds("m7_v01", "12", "topstep-50k@2026-11-14", n_paths=400)["worst_case_pass_p"] is None
    assert MJ.eval_odds("m7_v01", "12", "topstep-50k@2026-10-01", n_paths=400)["rule"] == "topstep-50k@2026-11-14"
    with pytest.raises(J.Refuse, match="no Flex"):
        MJ.eval_odds("m7_v01", "12", "lucid-flex-50k@2026-10-11")


def test_a_rerun_that_differs_withholds_the_eval_number(monkeypatch):
    fake_box(monkeypatch, worse_fills_net=4000.0)
    engine(monkeypatch, [trade_row(d, net=10.0) for d in weekdays(40)])
    with pytest.raises(MJ.Mismatch, match="no number is worked out"):
        MJ.eval_odds("m7_v01", "12", "topstep-50k@2026-11-14", n_paths=400)


def test_the_server_never_runs_the_engine(monkeypatch, tmp_path):
    (tmp_path / "no_backtests").write_text("")
    fake_box(monkeypatch)
    calls = engine(monkeypatch, [])
    assert MJ.on_server()
    for fn in (lambda: MJ.box_trades("m7_v01", "12"), lambda: MJ.eval_odds("m7_v01", "12", "topstep-50k@2026-11-14")):
        with pytest.raises(J.Refuse, match="server"):
            fn()
    assert not calls
```

The sizing test pins `library.sized`'s micro model: micros = `max(1, round(risk_usd / (stop points × $2)))`; net =
micros × ((1-contract net + `COMM_RT` 4.00) / 10 − `MICRO_RT_USD` 1.00); MAE and MFE scale by micros / 10.

- [ ] **Step 2: Run them to make sure they fail**

Run (cwd `research/edge-library`): `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_judge.py -v`
Expected: FAIL (`ImportError: cannot import name 'missionjudge'`)

- [ ] **Step 3: Write `research/edge-library/blueprint/missionjudge.py`** (Task 5 adds to it; `_check`, `family_tries` and `DEAD_ENV`, which the test fixture names, are written here as shown so the file imports)

```python
"""missionjudge.py -- THE MISSIONS JUDGE (the owner, 2026-11-14). Fixed code: no model decides anything here.

A mission (homebase/missions.py) makes versions of an idea, named m<id>_*. For one box of a version's 3:1 in-sample table:
    real_lines   real.py's first five lines at the version's try count (the luck bar rises 0.25 a try)
    charges      the five fixed charges
    goal_value   the mission's goal, measured: points over (hunt.py), net, or the eval pass rate on one of the owner's accounts
    gate         all three: is the version clear in-sample?
    reach        can this family still reach the luck bar at all?
    read         THE ONLY DOOR TO A MISSION VERSION'S TEST MONTHS: the gate must be clear; then the toolkit's own pick and read
                 (api.wf_pick, api.wf_oos), marked who = mission:<id>, once; the version is frozen; the workers hear only held /
                 which line / close; the owner's numbers go to ~/.homebase/missions/<id>/reads/<name>.json

THE EVAL GOAL. A store keeps no trade high, and the prop sim's intraday trail (Apex Legacy) needs it; propodds reads only 6 of the 18
accounts of 2026-11-14. So the picked box is RUN AGAIN with the engine's full rows (box_trades), held against its store (the same
trade count and net, or Mismatch: no number), sized to the account (sized_trades) and handed to the tester's own prop sim
(homebase/backtest/propsim.evaluate). "Live is worse" = the re-run with line 5's worse fills.

SEAMS (the tests replace them): _flag, _box, _engine_trades, _points, _check, family_tries, family_best_t.
Never on the trading server (~/.homebase/no_backtests)."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import itertools
import json
import os
from pathlib import Path

import numpy as np

import judge as J
import l2sim as S
import library as LB
import run_idea as RI
import run_menus as RM

from . import api
from . import hmwf as H
from . import hunt as HU
from . import missionacct as A
from . import propodds as PO
from . import reads as RD
from . import real as REAL
from . import rules as R
from . import runner as RUN

HORIZON = 10                        # the owner's bar (2026-10-03): an eval is passed within 10 trading weekdays
CONTRACT = {"NQ": "MNQ", "ES": "MES", "GC": "MGC"}      # the micro a mission's trades are sized in
TOL = 1.0                           # $: a re-run within this of its store's net is the same trades (one NQ tick on one trade is $5;
#                                     a store keeps its nets as 32-bit floats, so a sum can sit a few cents off)
DEAD_ENV = "HOMEBASE_DEAD_FAMILIES"
STAGES = ("wf_is", "wf_oos", "build", "bp_build")       # a ledger row of these stages = one table of a family that someone looked at


class Mismatch(J.Refuse):
    """The re-run of a box did not give its store's trades: no number is worked out from it."""


def missions():
    """homebase/missions.py (mission state), imported from the repo by its path like the idea store."""
    api.ideastore()
    from homebase import missions as M
    return M


def _flag() -> Path:
    return Path.home() / ".homebase" / "no_backtests"


def on_server() -> bool:
    return _flag().exists()


def _no_server() -> None:
    if on_server():
        raise J.Refuse("this is the trading server (~/.homebase/no_backtests): the Judge never runs the engine here")


# ================================================================ a box of a version's 3:1 stores

def _box(name: str, box) -> dict:
    """What the Judge reads of one box: its store's folder and meta, the in-sample table and the box's row (`box` = its row number or
    its id), the lock if any, the test-month record if it was read, and the days that read ran on."""
    home = H.store(name)
    _, m = H._load(home)
    rows = H.is_table(name, home)
    by_n = isinstance(box, int) and not isinstance(box, bool) or isinstance(box, str) and box.isdigit()
    r = next((x for x in rows if (x["n"] == int(box) if by_n else x["box"] == box)), None)
    if r is None:
        raise J.Refuse(f"{box!r}: not a box of {home.name} (a row number 1..{len(rows)} of its in-sample table, or a box id)")
    oos = H._oos(home, rows)
    days = list(H._load(home, H.OOS, S.ALLOW_WF_OOS)[1]["days"]) if oos and not oos.get("state") else None
    return {"home": home, "m": m, "rows": rows, "row": r, "lock": H._lock(home), "oos": oos, "oos_days": days}


def _engine_trades(b: dict, days: list, period: str, worse: bool, workers: int) -> list:
    """The engine's own full rows (prices, mae_usd, mfe_usd) of the box on the named days: the call runner._pass makes for its store,
    for this one cell (hmwf._grid proves the idea's table is the one the store was run from). Worse = with line 5's worse fills
    (runner.worse_kw). The test switch takes one month a call. Nothing is written and nothing is booked: no new cell is tried."""
    m = b["m"]
    cell = next(c for c in H._grid(m, b["home"]) if c["id"] == b["row"]["box"])
    kw = dict(RUN._kw(m["family"]))
    if worse:
        kw.update(RUN.worse_kw(bool(RUN._blocks().BASES[m["family"]][2])))
    specs = RI.cell_specs(cell, list(m["sessions"]))
    step = max(1, int(R.template("compute")["block_days"])) if all(getattr(c, "session_independent", False) for c, _ in specs) else len(days)
    months = [list(g) for _, g in itertools.groupby(days, key=lambda d: d[:7])] if period == S.ALLOW_WF_OOS else [list(days)]
    out = []
    for chunk in (mo[i:i + step] for mo in months for i in range(0, len(mo), step)):
        res = RM.merge(S.run_many(specs, days=chunk, root=m["root"], workers=max(1, min(int(workers), S.MAX_WORKERS)), allow_holdout=period,
                                  **RUN._engine(kw)))
        if res["skipped_by_error"]:
            raise J.Refuse(f"{b['home'].name} box {cell['id']}: sessions were dropped by a strategy error")
        if any(t["date"] not in set(chunk) for t in res["trades"]):
            raise RuntimeError("the engine handed back a trade of a day that was not named")
        out += res["trades"]
    return out


def _held(b: dict, trades: list, n, net: float) -> None:
    got = round(float(sum(t["net"] for t in trades)), 2)
    if (n is not None and len(trades) != n) or abs(got - net) > TOL:
        raise Mismatch(f"{b['home'].name} box {b['row']['box']}: the re-run ({len(trades)} trades, net {got:,.2f}) differs from its store "
                       f"({'?' if n is None else n} trades, net {net:,.2f}): no number is worked out from it")


def box_trades(name: str, box, on: str = "is", worse: bool = False, mid=None, workers: int = 4) -> list:
    """THE FULL TRADE ROWS OF ONE BOX, run again and held to its store. on = "is": the in-sample months (worse: held to the row's
    worse-fills net). on = "oos": the test months, only after THIS mission read them (lock.who = mission:<mid>, the record on file);
    the test months have no worse-fills store, so a worse run is given only after the plain re-run was held to the record."""
    _no_server()
    if on not in ("is", "oos"):
        raise J.Refuse(f"on {on!r}: is (the in-sample months) or oos (the test months, after this mission's read)")
    b = _box(name, box)
    r, where = b["row"], f"{b['home'].name} box {b['row']['box']}"
    if on == "is":
        if worse and r["worse_fills_net"] is None:
            raise J.Refuse(f"{where}: its worse-fills run is not on file")
        trades = _engine_trades(b, list(b["m"]["days"]), S.ALLOW_WF_IS, worse, workers)
        _held(b, trades, None if worse else r["trades"], r["worse_fills_net"] if worse else r["net"])
        return trades
    lock, oos = b["lock"] or {}, b["oos"]
    if mid is None or lock.get("who") != f"mission:{int(mid)}" or lock.get("box") != r["box"]:
        raise J.Refuse(f"{where}: its test months are run again only after they were read by this mission")
    if not oos or oos.get("state") or not b.get("oos_days"):
        raise J.Refuse(f"{where}: no test-month record on file to run again")
    trades = _engine_trades(b, list(b["oos_days"]), S.ALLOW_WF_OOS, False, workers)
    _held(b, trades, oos["record"]["trades"], oos["record"]["net"])
    return _engine_trades(b, list(b["oos_days"]), S.ALLOW_WF_OOS, True, workers) if worse else trades


def sized_trades(trades: list, root: str, risk_usd: float, cap_micros) -> list:
    """The same trades in MICROS at about `risk_usd` a trade (library.sized: micros = max(1, round(risk / (stop points x the micro's
    point value)))), never more than the account's contract limit. Copies: each keeps its times and gets its dollars at that size.
    A trade without a stop distance cannot be sized and is left out (library.sized counts it as unsized)."""
    micros = np.asarray(LB.sized(LB.pack(trades), root, risk_usd)["micros"], np.int64)
    if cap_micros:
        micros = np.minimum(micros, int(cap_micros))
    out = []
    for t, n in zip(trades, (int(v) for v in micros)):
        if n < 1:
            continue
        out.append({**t, "qty": n, "net": n * ((t["net"] + LB.COMM_RT) / LB.MICRO_DIV - LB.MICRO_RT_USD), "commission": n * LB.MICRO_RT_USD,
                    "mae_usd": n * abs(t.get("mae_usd") or 0.0) / LB.MICRO_DIV, "mfe_usd": n * abs(t.get("mfe_usd") or 0.0) / LB.MICRO_DIV})
    return out


def eval_odds(name: str, box, rule_id: str, on: str = "is", mid=None, n_paths=None) -> dict:
    """THE EVAL GOAL'S NUMBER: the chance this box passes the account's eval within 10 trading weekdays, at one fixed risk a trade
    (the account's drawdown / 2.5, capped at its contract limit), on the box re-run with worse fills. Bust % beside it; on an account
    whose floor trails the intraday high, the careful bound too (every winner taken to make its low before its high)."""
    _no_server()
    f = A.facts(rule_id)
    b = _box(name, box)
    trades = box_trades(name, box, on, worse=True, mid=mid)
    rows = sized_trades(trades, b["m"]["root"], f["risk"], f["cap_micros"])
    if not rows:
        raise J.Refuse(f"{b['home'].name} box {b['row']['box']}: no trade that can be sized on {f['id']}")
    e = PO.app().evaluate(rows, f["id"], horizon=HORIZON, contract=CONTRACT.get(b["m"]["root"]), **({"n_paths": int(n_paths)} if n_paths else {}))
    if "skipped" in e:
        raise J.Refuse(f"{f['id']}: the prop sim did not run on this box ({e['skipped']})")
    h = e["headline"]
    return {"rule": f["id"], "account": f["name"], "risk": f["risk"], "on": on, "trades": len(rows), "unsized": len(trades) - len(rows),
            "pass_p": h["eval_pass_p"], "pass_ci": h["eval_pass_ci"], "bust_p": h["bust_p"], "days_to_pass": h["median_days_to_pass"],
            "worst_case_pass_p": (e.get("trail_worst_case") or {}).get("eval_pass_p"), "size": e.get("size"), "caveat": e.get("caveat"),
            "confirmed": f["confirmed"], "bans": f["bans"]}


# ================================================================ tries, the code check (Task 5 adds the charges, the gate and out of reach)

def _check(name: str):
    """Did the idea's code check pass (its check.json in the app's idea folder: api.code_check)? None: no check on file."""
    f = api._idea_file(name, None, "check.json")
    try:
        got = json.loads(Path(f).read_text(encoding="utf-8")) if f else None
    except (OSError, ValueError):
        return None
    return bool(got.get("passed")) if isinstance(got, dict) else None


def family_tries(family: str, root: str = "NQ", path=None) -> int:
    """How many tables of this family are on file in the ledger (ledger.csv: the distinct keys of its in-sample tables, test-month reads
    and old build tables on this market)."""
    f = Path(path or LB.LEDGER)
    if not f.exists():
        return 0
    with open(f, newline="", encoding="utf-8") as fh:
        return len({r["key"] for r in csv.DictReader(fh) if r.get("family") == family and r.get("root") == root and r.get("stage") in STAGES})
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_judge.py -v`
Expected: PASS (7 tests). `test_eval_odds_reads_every_kind_of_new_account` runs the real prop sim on hand-made trades
(400 paths): a few seconds.

- [ ] **Step 5: Commit**

```bash
git add research/edge-library/blueprint/missionjudge.py research/edge-library/tests/test_mission_judge.py
git commit -m "Missions Judge: the picked box run again with full trades, held to its store, sized to the account, eval odds on every new account"
```

---

### Task 5: Charges, tries, the gate and out of reach

**Files:**
- Modify: `research/edge-library/blueprint/missionjudge.py` (add below Task 4's code)
- Test: `research/edge-library/tests/test_mission_judge.py` (add below Task 4's tests)

**Interfaces:**
- Consumes: Task 1 (`brief`, `tries`); Task 4 (`_box`, `eval_odds`, `_check`, `family_tries`, `missions`); `real.check(s, tries) -> [{"line", "ok", "said"}]` with `s = {"is": rows, "lock": {"box": id}, "oos": None}` (its lines, in order: `boxes`, `trades`, `luck`, `years`, `worse fills`, then `test months`), `real.T_BAR` (2.0), `real.T_PER_TRY` (0.25); `hunt._box(x, root, days) -> {"points_over", "trades", "net", "per_week", ...}`; `library.unit_cell(unit, i)`, `library.load_unit(sub, home)`, `library.stats(net)["t"]`; `hmwf._load`, `hmwf.RUNS`, `hmwf.IS`, `hmwf.OOS`. An in-sample row carries `long_net` and `short_net`.
- Produces (used by Task 6):
  - `CHARGES: tuple[str, ...]` (the five, in order)
  - `dead_families() -> set[str]`; `start_tries(family, root="NQ") -> int`; `t_needed(tries) -> float`; `version_tries(mid, family, root="NQ") -> int`; `tries_of(mid, family, root="NQ") -> dict`
  - seam `family_best_t(family, root="NQ") -> float | None`; seam `_points(b, on="is") -> {"points_over", "trades", "net"}`
  - `real_lines(mid, b) -> list[dict]` (five lines); `charges(mid, name, box, b=None, lines=None) -> [{"charge", "held", "why"}]`
  - `goal_value(mid, name, b, on="is") -> {"kind", "target", "value", "met"}`
  - `gate(mid, name, box) -> {"name", "box", "clear", "lines", "charges", "goal", "tries"}`
  - `reach(mid, family, root="NQ") -> {"family", "tries", "needed_t", "best_t", "reachable"}`

The five charges (all run on every version; "held" = the version stands against the charge):

| Charge | Held when |
|---|---|
| One year carries it | `real.check`'s `years` line passes |
| Worse fills kill it | its `worse fills` line passes |
| It looks ahead | the idea's code check on file says passed |
| One side carries it | every side that traded has a net above $0 (a one-sided idea: its one side) |
| It is a dead family again | the family is not on the dead list |

- [ ] **Step 1: Add the failing tests** to `research/edge-library/tests/test_mission_judge.py`

```python
# ---------------------------------------------------------------- Task 5: charges, tries, the gate, out of reach

POINTS = {"points_over": 3.4, "trades": 300, "net": 9000.0}


def points(monkeypatch, over=3.4):
    monkeypatch.setattr(MJ, "_points", lambda b, on="is": {**POINTS, "points_over": over})


def test_family_tries_count_the_tables_on_file(tmp_path):
    f = tmp_path / "ledger.csv"
    f.write_text("stage,key,kind,family,root\n" + "\n".join(",".join(r) for r in (
        ("wf_is", "a-NQ-tf15/is", "unit", "orb", "NQ"), ("wf_oos", "a-NQ-tf15/oos", "unit", "orb", "NQ"), ("build", "b-NQ-tf15", "unit", "orb", "NQ"),
        ("wf_is", "a-NQ-tf15/is", "unit", "orb", "NQ"), ("null", "c-NQ-tf15", "pool", "orb", "NQ"), ("wf_is_worse", "a-NQ-tf15/is-nyam-worse", "worse", "orb", "NQ"),
        ("wf_is", "d-ES-tf15/is", "unit", "orb", "ES"), ("wf_is", "e-NQ-tf15/is", "unit", "fvg", "NQ"))) + "\n")
    assert REAL_FAMILY_TRIES("orb", path=f) == 3 and REAL_FAMILY_TRIES("fvg", path=f) == 1 and REAL_FAMILY_TRIES("none", path=f) == 0
    assert REAL_FAMILY_TRIES("orb", path=tmp_path / "missing.csv") == 0


def test_the_luck_bar_rises_a_quarter_a_try(monkeypatch):
    assert MJ.t_needed(1) == 2.0 and MJ.t_needed(5) == 3.0 and MJ.t_needed(0) == 2.0
    assert MJ.version_tries(7, "orb") == 1                                   # the version being judged is at least try 1
    monkeypatch.setattr(MJ, "family_tries", lambda family, root="NQ", path=None: 4)
    M.record(7, "wf", "m7_v01", {"a": 1})
    assert MJ.version_tries(7, "orb") == 5
    assert MJ.tries_of(7, "orb") == {"family": "orb", "family_on_file": 4, "mission": 1, "total": 5, "needed_t": 3.0}


def test_dead_list_reads_the_vault_table(tmp_path):
    assert MJ.dead_families() == set()                                       # no file: nothing is dead
    (tmp_path / "dead.md").write_text("---\nname: dead-families\n---\n\nThe list.\n\n| family | verdict | date | why |\n|---|---|---|---|\n"
                                      "| win_bracket | dead | 2026-11-14 | x |\n| `eve_rule` | dead | 2026-11-14 | y |\n")
    assert MJ.dead_families() == {"win_bracket", "eve_rule"}


def test_the_five_charges(monkeypatch, tmp_path):
    fake_box(monkeypatch)
    got = MJ.charges(7, "m7_v01", "12")
    assert [c["charge"] for c in got] == list(MJ.CHARGES) and len(MJ.CHARGES) == 5 and all(c["held"] is True and c["why"] for c in got)
    cases = (({"best_year_share": 0.7}, True, False, 0), ({"worse_fills_net": -5.0}, True, False, 1), ({}, False, False, 2), ({}, None, False, 2),
             ({"short_net": -300.0}, True, False, 3), ({"long_net": -1.0}, True, False, 3), ({}, True, True, 4))
    for over, checked, dead, broke in cases:
        fake_box(monkeypatch, **over)
        monkeypatch.setattr(MJ, "_check", lambda name, ok=checked: ok)
        (tmp_path / "dead.md").write_text("| family | verdict |\n|---|---|\n| orb | dead |\n" if dead else "")
        assert [i for i, c in enumerate(MJ.charges(7, "m7_v01", "12")) if not c["held"]] == [broke]
    (tmp_path / "dead.md").write_text("")
    monkeypatch.setattr(MJ, "_check", lambda name: True)
    fake_box(monkeypatch, short_net=0.0)                                     # a one-sided idea: its one side is the idea
    assert all(c["held"] for c in MJ.charges(7, "m7_v01", "12"))
    fake_box(monkeypatch, long_net=0.0, short_net=0.0)                       # nothing traded: nothing carries it
    assert MJ.charges(7, "m7_v01", "12")[3]["held"] is False


def test_gate_needs_the_five_lines_the_charges_and_the_goal(monkeypatch):
    fake_box(monkeypatch)
    points(monkeypatch)
    g = MJ.gate(7, "m7_v01", "12")
    assert g["clear"] is True and [x["line"] for x in g["lines"]] == ["boxes", "trades", "luck", "years", "worse fills"]
    assert g["goal"] == {"kind": "points", "target": 3.0, "value": 3.4, "met": True} and g["tries"] == 1 and g["box"] == "v0_atr1-r1"
    points(monkeypatch, 2.9)
    assert MJ.gate(7, "m7_v01", "12")["clear"] is False                      # the goal is not met
    points(monkeypatch, None)
    assert MJ.gate(7, "m7_v01", "12")["clear"] is False                      # no score: not met
    points(monkeypatch)
    fake_box(monkeypatch, trades=150)
    assert MJ.gate(7, "m7_v01", "12")["clear"] is False                      # a line fails (under 200 trades)
    fake_box(monkeypatch, short_net=-300.0)
    assert MJ.gate(7, "m7_v01", "12")["clear"] is False                      # a charge breaks


def test_the_bar_a_version_meets_rises_with_the_missions_tries(monkeypatch):
    fake_box(monkeypatch, t_stat=2.1)
    points(monkeypatch)
    M.record(7, "wf", "m7_v01", {"a": 1})
    assert MJ.gate(7, "m7_v01", "12")["clear"] is True                       # 1 try: t 2.0 needed
    M.record(7, "wf", "m7_v02", {"a": 2})
    g = MJ.gate(7, "m7_v01", "12")
    assert g["clear"] is False and g["tries"] == 2                           # 2 tries: t 2.25 needed


def test_net_and_eval_goals(monkeypatch):
    b = fake_box(monkeypatch)
    write_brief(goal={"kind": "net", "target": 8000.0})
    assert MJ.goal_value(7, "m7_v01", b) == {"kind": "net", "target": 8000.0, "value": 9000.0, "met": True}
    write_brief(goal={"kind": "eval", "target": 0.5, "rule": "topstep-50k@2026-11-14"})
    monkeypatch.setattr(MJ, "eval_odds", lambda name, box, rule, on="is", mid=None, n_paths=None: {"pass_p": 0.41})
    assert MJ.goal_value(7, "m7_v01", b) == {"kind": "eval", "target": 0.5, "value": 0.41, "met": False}


def test_out_of_reach_when_the_needed_t_beats_the_familys_best(monkeypatch):
    monkeypatch.setattr(MJ, "family_tries", lambda family, root="NQ", path=None: 20)
    monkeypatch.setattr(MJ, "family_best_t", lambda family, root="NQ": 4.1)
    assert MJ.reach(7, "orb") == {"family": "orb", "tries": 20, "needed_t": 7.0, "best_t": 4.1, "reachable": False}
    monkeypatch.setattr(MJ, "family_tries", lambda family, root="NQ", path=None: 0)
    assert MJ.reach(7, "orb")["needed_t"] == 2.0 and MJ.reach(7, "orb")["reachable"] is True
    monkeypatch.setattr(MJ, "family_best_t", lambda family, root="NQ": None)   # a family with no table on file: nothing says it cannot
    assert MJ.reach(7, "orb")["reachable"] is True
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_judge.py -v`
Expected: Task 4's tests PASS, the eight new ones FAIL (`AttributeError: ... has no attribute 't_needed'` and the like)

- [ ] **Step 3: Add to `research/edge-library/blueprint/missionjudge.py`**

```python
# ================================================================ tries and the luck bar

def start_tries(family: str, root: str = "NQ") -> int:
    """Where a mission's try count starts: the family's tries on file (the design, section 5). THE ONE LINE TO CHANGE if the owner
    rules that a mission counts only its own tries."""
    return max(0, family_tries(family, root))


def t_needed(tries: int) -> float:
    """real.py's luck bar after this many tries: 2.0, + 0.25 for each try after the first."""
    return REAL.T_BAR + REAL.T_PER_TRY * (max(int(tries), 1) - 1)


def _tries(mid, family: str, root: str = "NQ") -> int:
    return start_tries(family, root) + missions().tries(mid)


def version_tries(mid, family: str, root: str = "NQ") -> int:
    """The try count a version of this mission is judged at (it is itself at least try 1)."""
    return max(1, _tries(mid, family, root))


def tries_of(mid, family: str, root: str = "NQ") -> dict:
    on_file, mine = start_tries(family, root), missions().tries(mid)
    return {"family": family, "family_on_file": on_file, "mission": mine, "total": on_file + mine, "needed_t": t_needed(on_file + mine)}


def family_best_t(family: str, root: str = "NQ"):
    """The best in-sample t-statistic any box of this family has on file (every 3:1 in-sample store of the family on this market):
    what the family has shown it can reach. None: no table of it on file."""
    best = None
    for f in sorted(H.RUNS.glob(f"*-{root}-tf*/{H.IS}/run.json")):
        try:
            m = json.loads(f.read_text())
            if m.get("family") != family:
                continue
            u = LB.load_unit(H.IS, f.parent.parent)
            ts = [LB.stats(LB.unit_cell(u, i)["net"])["t"] for i in range(len(m["cells"]))]
        except (OSError, ValueError, KeyError):
            continue                # a store that cannot be read says nothing
        ts = [t for t in ts if t is not None]
        if ts:
            best = max(ts) if best is None else max(best, max(ts))
    return best


def reach(mid, family: str, root: str = "NQ") -> dict:
    """OUT OF REACH: the t the mission's NEXT version needs, against the best t this family has ever shown in-sample."""
    n = _tries(mid, family, root)
    need, best = t_needed(n + 1), family_best_t(family, root)
    return {"family": family, "tries": n, "needed_t": need, "best_t": best, "reachable": best is None or need <= best}


# ================================================================ the five lines, the five charges, the goal, the gate

CHARGES = ("One year carries it", "Worse fills kill it", "It looks ahead", "One side carries it", "It is a dead family again")


def dead_families() -> set:
    """The dead-family list: the first column of the table in the owner's vault note (or the file $HOMEBASE_DEAD_FAMILIES names).
    Rows come only from the owner. No file: nothing is dead."""
    f = Path(os.environ.get(DEAD_ENV) or Path.home() / "Obsidian" / "Vault" / "30-Projects" / "Onyx-Trading" / "dead-families.md").expanduser()
    try:
        text = f.read_text(encoding="utf-8")
    except OSError:
        return set()
    out = set()
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        first = line.strip().strip("|").split("|")[0].strip().strip("`")
        if first and first != "family" and not set(first) <= set("-: "):
            out.add(first)
    return out


def _points(b: dict, on: str = "is") -> dict:
    """The owner's score of the box (hunt.py: full-target % minus the % needed, every trade at $1,000 of risk) on its in-sample trades,
    or on its test months once they were read."""
    home, m = b["home"], b["m"]
    if on == "is":
        u, days = H._load(home)[0], m["days"]
        i = next(k for k, c in enumerate(m["cells"]) if c["id"] == b["row"]["box"])
    else:
        u, mo = H._load(home, H.OOS, S.ALLOW_WF_OOS)
        days, i = mo["days"], 0
    x = LB.unit_cell(u, i)
    if not len(x["net"]):
        return {"points_over": None, "trades": 0, "net": 0.0}
    r = HU._box(x, m["root"], days)
    return {"points_over": float(r["points_over"]), "trades": int(r["trades"]), "net": float(r["net"])}


def _ok(v) -> bool:
    return v is not None and bool(v)


def real_lines(mid, b: dict) -> list:
    """real.py's first five lines for this box at the version's try count. (check finds the box through the lock, and before the read
    there is none: the box is named here.)"""
    s = {"is": b["rows"], "lock": {"box": b["row"]["box"]}, "oos": None}
    return REAL.check(s, version_tries(mid, b["m"]["family"], b["m"]["root"]))[:5]


def charges(mid, name: str, box, b=None, lines=None) -> list:
    """The five fixed charges against one box, each {"charge", "held", "why"}: held = the version stands."""
    b = b or _box(name, box)
    by = {x["line"]: x for x in (lines if lines is not None else real_lines(mid, b))}
    long_, short = float(b["row"]["long_net"]), float(b["row"]["short_net"])
    traded = [v for v in (long_, short) if v]         # a side with no trade has a net of exactly 0
    checked, fam, dead = _check(name), b["m"]["family"], dead_families()
    held = (_ok(by["years"]["ok"]), _ok(by["worse fills"]["ok"]), checked is True, bool(traded) and all(v > 0 for v in traded), fam not in dead)
    why = (by["years"]["said"], by["worse fills"]["said"],
           "its code check passed" if checked else "its code check failed" if checked is False else "no code check of it is on file (blueprint_code_check)",
           f"long net {long_:,.0f}, short net {short:,.0f}", f"family {fam} is {'on' if fam in dead else 'not on'} the dead list")
    return [{"charge": c, "held": bool(h), "why": w} for c, h, w in zip(CHARGES, held, why)]


def goal_value(mid, name: str, b: dict, on: str = "is") -> dict:
    """The mission's goal measured on this box: in-sample, or (on="oos") on its test months alone."""
    g = missions().brief(mid)["goal"]
    if g["kind"] == "points":
        v = _points(b, on)["points_over"]
    elif g["kind"] == "net":
        v = b["row"]["net"] if on == "is" else b["oos"]["record"]["net"]
    else:
        v = eval_odds(name, b["row"]["box"], g["rule"], on, mid)["pass_p"]
    return {"kind": g["kind"], "target": g["target"], "value": None if v is None else float(v), "met": v is not None and float(v) >= g["target"]}


def gate(mid, name: str, box) -> dict:
    """IS THIS VERSION CLEAR IN-SAMPLE? The five lines all pass, every charge is held, and the goal is met. Only then may its test
    months be read."""
    b = _box(name, box)
    lines = real_lines(mid, b)
    ch = charges(mid, name, box, b, lines)
    goal = goal_value(mid, name, b, "is")
    clear = all(_ok(x["ok"]) for x in lines) and all(c["held"] for c in ch) and goal["met"]
    return {"name": name, "box": b["row"]["box"], "clear": bool(clear), "lines": lines, "charges": ch, "goal": goal,
            "tries": version_tries(mid, b["m"]["family"], b["m"]["root"])}
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_judge.py tests/test_real.py tests/test_blueprint_hunt.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/edge-library/blueprint/missionjudge.py research/edge-library/tests/test_mission_judge.py
git commit -m "Missions Judge: the five charges, tries from the family's file, the gate, out of reach"
```

---

### Task 6: The Judge's door and the read

**Files:**
- Modify: `research/edge-library/blueprint/missionjudge.py` (add `spec_id`, `verdict_for_workers`, `read` below Task 5's code)
- Create: `research/edge-library/blueprint/missiondoor.py`
- Create: `research/edge-library/missions/judge` (bash, executable: `chmod +x`)
- Test: `research/edge-library/tests/test_mission_door.py`

**Interfaces:**
- Consumes: Task 1 (`validate_id`, `brief`, `prefix`, `frozen`, `freeze`, `record`, `ledger`, `mission_dir`); Task 3 (`accounts`); Task 4 (`_box`, `_no_server`); Task 5 (`gate`, `_points`, `goal_value`, `tries_of`, `reach`, `charges`); `api.wf_pick(name, box, who)` (the lock; `who` is written into `lock.json`), `api.wf_oos(name, box, owner_said, workers=None, progress=None, who="owner")` (the one read of the picked box's test months; it claims the read in the one-read log before a day is opened); `reads.wf_oos_on_file(store, box) -> list` (the claims on file); `real.MIN_TRADES_OOS` (60).
- Produces: `LINES: tuple[str, ...]`; `spec_id(m) -> str`; `verdict_for_workers(test, k) -> {"held", "line", "close"}`; `read(mid, name, box, said=None) -> {"held", "line", "close"}`; `missiondoor.parser()`, `missiondoor.run(a)`, `missiondoor.main(argv=None) -> int`.

| Command | Prints |
|---|---|
| `accounts` | every open account with its facts and bans (Task 3) |
| `tries <mid> <family>` | `{family, family_on_file, mission, total, needed_t}` |
| `reach <mid> <family>` | Task 5's `reach` |
| `charges <mid> <name> <box>` | Task 5's `charges` (in-sample; workers may see it) |
| `gate <mid> <name> <box>` | Task 5's `gate` (in-sample; workers may see it) |
| `read <mid> <name> <box> [--said TEXT]` | ONLY `{"held", "line", "close"}`; the owner's numbers go to `<mission dir>/reads/<name>.json` |

The read, in order:
1. Refuse on the server, without an approved brief, for a name without the mission's prefix, for a frozen name, and for a version whose settings (`spec_id` of its store's meta) are those of a frozen one (a copy under a new name).
2. `test_months == "ask"` needs `--said` (the owner's words, passed on verbatim as `owner_said`); `"team"` uses the brief's `owner_said`.
3. The gate must be clear; else refuse with what failed. No test month is touched.
4. `api.wf_pick(name, box, "mission:<mid>")`, then `api.wf_oos(name, box, owner_said, who="mission:<mid>")`.
5. The version is frozen and the read recorded (a try) straight after the read, before any number is worked out, so a crash later still leaves it frozen. A read that stopped after its claim is frozen too; one refused before its claim (the tester is busy) is not used and not frozen.
6. The owner's numbers: test trades, net, win rate, points over, the goal's measure (an eval number that cannot be worked out is filed as withheld, with the reason), the bar of this read, the blocks.
7. The workers' verdict. Read k needs points over > k − 1. The lines, the first that breaks wins: too few trades (< 60); lost money (net ≤ $0); flipped direction (points over ≤ 0); under the bar; missed the goal. `close` is said only for "flipped direction" and "under the bar": true when the bar minus points over is under 1.

- [ ] **Step 1: Write the failing tests** in `research/edge-library/tests/test_mission_door.py`

```python
"""The Judge's door (blueprint/missiondoor.py) and the test-month read (missionjudge.read): the gate first, the toolkit's pick and read
marked mission:<id>, frozen at once, the workers hear only held / line / close, the owner's numbers in a file. The toolkit's pick and
read, the stores and the gate are faked."""
import json
import subprocess
from pathlib import Path

import pytest

import judge as J
from blueprint import missiondoor as D
from blueprint import missionjudge as MJ

M = MJ.missions()
JUDGE = Path(__file__).resolve().parent.parent / "missions" / "judge"
BOX = "v0_atr1-r1"
SAID = "run it until the goal (test brief)"


def write_brief(mid=7, **over):
    b = {"approved": True, "owner_said": SAID, "test_months": "team", "goal": {"kind": "points", "target": 1.0}, **over}
    d = M.mission_dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.json").write_text(json.dumps(b))


class Read:
    """The toolkit's pick and read, faked: what was called, and the test-month record the Judge then finds on file."""

    def __init__(self, monkeypatch, tmp_path):
        self.picks, self.reads, self.settings = [], [], {}
        self.record, self.points, self.clear = {"trades": 80, "net": 900.0, "win_rate": 0.5}, 1.4, True
        self.claimed, self.boom = True, None
        monkeypatch.setenv(M.ENV, str(tmp_path / "missions"))
        monkeypatch.setattr(MJ, "_flag", lambda: tmp_path / "no_backtests")
        monkeypatch.setattr(MJ, "_box", self.box)
        monkeypatch.setattr(MJ, "gate", lambda mid, name, box: {
            "name": name, "box": BOX, "clear": self.clear, "lines": [{"line": "luck", "ok": self.clear, "said": "t 1.2 in-sample"}],
            "charges": [], "goal": {"met": True}, "tries": 1})
        monkeypatch.setattr(MJ, "_points", lambda b, on="is": {"points_over": self.points, "trades": self.record["trades"], "net": self.record["net"]})
        monkeypatch.setattr(MJ.api, "wf_pick", lambda name, box, who="owner": self.picks.append((name, box, who)))
        monkeypatch.setattr(MJ.api, "wf_oos", self.oos)
        monkeypatch.setattr(MJ.RD, "wf_oos_on_file", lambda store, box=None, root=None: [{"claim": 1}] if self.claimed and self.reads else [])

    def box(self, name, box):
        read = any(r[0] == name for r in self.reads)
        return {"home": Path(f"/nowhere/{name}-NQ-tf15"), "rows": [], "row": {"n": 12, "box": BOX, "trades": 300, "net": 9000.0, "t_stat": 3.4},
                "lock": {"box": BOX, "who": "mission:7"} if read else None, "oos_days": None,
                "oos": {"record": dict(self.record), "blocks": [{"i": 1, "oos": "2022-01", "trades": 5, "win_rate": 0.6, "net": 50.0}]} if read else None,
                "m": {"idea": name, "family": "orb", "root": "NQ", "tf": "15", "sessions": ["nyam"], "days": [], "exits": "hm40", "fixed": {},
                      "limits": {}, "variants": self.settings.get(name, {"v": name})}}

    def oos(self, name, box, owner_said, workers=None, progress=None, who="owner"):
        self.reads.append((name, box, owner_said, who))
        if self.boom:
            raise self.boom


@pytest.fixture
def R(monkeypatch, tmp_path):
    r = Read(monkeypatch, tmp_path)
    write_brief()
    return r


def door(argv):
    return D.run(D.parser().parse_args(argv))


def test_read_prints_only_held_line_close_and_files_the_owners_numbers(R):
    assert door(["read", "7", "m7_v01", "12"]) == {"held": True, "line": None, "close": None}
    assert R.picks == [("m7_v01", BOX, "mission:7")] and R.reads == [("m7_v01", BOX, SAID, "mission:7")]
    saved = json.loads((M.mission_dir(7) / "reads" / "m7_v01.json").read_text())
    assert saved["net"] == 900.0 and saved["trades"] == 80 and saved["points_over"] == 1.4 and saved["who"] == "mission:7"
    assert saved["read_number"] == 1 and saved["bar"] == 0 and saved["box"] == BOX and saved["verdict"]["held"] is True and saved["blocks"]
    assert "m7_v01" in M.frozen(7) and M.tries(7) == 1                       # frozen, and the read is a try


def test_the_bar_rises_one_point_a_read(R):
    assert door(["read", "7", "m7_v01", "12"])["held"] is True               # the 1st read: over 0
    R.points = 0.6
    assert door(["read", "7", "m7_v02", "12"]) == {"held": False, "line": "under the bar", "close": True}      # the 2nd: over +1
    R.points = 0.5
    assert door(["read", "7", "m7_v03", "12"]) == {"held": False, "line": "under the bar", "close": False}     # the 3rd: over +2


def test_the_lines_in_their_order():
    v = MJ.verdict_for_workers
    assert MJ.LINES == ("too few trades", "lost money", "flipped direction", "under the bar", "missed the goal")
    assert v({"trades": 40, "net": -50.0, "points_over": -2.0, "goal_met": False}, 1) == {"held": False, "line": "too few trades", "close": None}
    assert v({"trades": 80, "net": -50.0, "points_over": -2.0, "goal_met": False}, 1) == {"held": False, "line": "lost money", "close": None}
    assert v({"trades": 80, "net": 50.0, "points_over": -0.4, "goal_met": False}, 1) == {"held": False, "line": "flipped direction", "close": True}
    assert v({"trades": 80, "net": 50.0, "points_over": -2.0, "goal_met": False}, 1) == {"held": False, "line": "flipped direction", "close": False}
    assert v({"trades": 80, "net": 50.0, "points_over": None, "goal_met": False}, 1) == {"held": False, "line": "flipped direction", "close": False}
    assert v({"trades": 80, "net": 50.0, "points_over": 1.0, "goal_met": True}, 2) == {"held": False, "line": "under the bar", "close": True}   # exactly the bar is not over it
    assert v({"trades": 80, "net": 50.0, "points_over": 1.5, "goal_met": False}, 2) == {"held": False, "line": "missed the goal", "close": None}
    assert v({"trades": 80, "net": 50.0, "points_over": 1.5, "goal_met": True}, 2) == {"held": True, "line": None, "close": None}


def test_a_version_is_read_once_and_a_copy_under_a_new_name_is_not_read(R):
    door(["read", "7", "m7_v01", "12"])
    with pytest.raises(J.Refuse, match="already read"):
        door(["read", "7", "m7_v01", "12"])
    R.settings["m7_v02"] = {"v": "m7_v01"}                                    # the same settings under a new name
    with pytest.raises(J.Refuse, match="same settings as m7_v01"):
        door(["read", "7", "m7_v02", "12"])
    assert len(R.reads) == 1 and len(R.picks) == 1


def test_frozen_before_any_number_is_worked_out(R, monkeypatch):
    def boom(b, on="is"):
        raise RuntimeError("the score crashed")
    monkeypatch.setattr(MJ, "_points", boom)
    with pytest.raises(RuntimeError):
        door(["read", "7", "m7_v01", "12"])
    assert "m7_v01" in M.frozen(7) and M.tries(7) == 1


def test_a_read_that_stopped_after_its_claim_is_used_and_one_refused_before_it_is_not(R):
    R.boom = J.Refuse("the test months of box x are used: this read stopped")
    with pytest.raises(J.Refuse):
        door(["read", "7", "m7_v01", "12"])
    assert "m7_v01" in M.frozen(7)                                            # claimed: the read is used
    R.claimed, R.boom = False, J.Refuse("the tester is busy")
    with pytest.raises(J.Refuse, match="busy"):
        door(["read", "7", "m7_v02", "12"])
    assert "m7_v02" not in M.frozen(7)                                        # refused before the claim: not used


def test_ask_mode_needs_the_owners_words(R):
    write_brief(test_months="ask")
    with pytest.raises(J.Refuse, match="--said"):
        door(["read", "7", "m7_v01", "12"])
    assert not R.reads
    door(["read", "7", "m7_v01", "12", "--said", "yes, read m7_v01"])
    assert R.reads[-1][2] == "yes, read m7_v01"


def test_a_version_that_fails_the_gate_never_touches_the_test_months(R):
    R.clear = False
    with pytest.raises(J.Refuse, match="not clear in-sample .*luck"):
        door(["read", "7", "m7_v01", "12"])
    assert not R.picks and not R.reads and "m7_v01" not in M.frozen(7)


def test_other_names_an_unapproved_brief_and_the_server_are_refused(R, tmp_path):
    for name in ("m3_v01", "owner_fvg_odir_15_nl_new"):
        with pytest.raises(J.Refuse, match="not a version of mission 7"):
            door(["read", "7", name, "12"])
    write_brief(approved=False)
    with pytest.raises(ValueError, match="not approved"):
        door(["read", "7", "m7_v01", "12"])
    write_brief()
    (tmp_path / "no_backtests").write_text("")
    with pytest.raises(J.Refuse, match="server"):
        door(["read", "7", "m7_v01", "12"])
    assert not R.picks and not R.reads


def test_an_eval_number_that_cannot_be_worked_out_is_filed_as_withheld(R, monkeypatch):
    def differs(mid, name, b, on="is"):
        raise MJ.Mismatch("the re-run differs from its store: no number is worked out from it")
    monkeypatch.setattr(MJ, "goal_value", differs)
    assert door(["read", "7", "m7_v01", "12"]) == {"held": False, "line": "missed the goal", "close": None}
    goal = json.loads((M.mission_dir(7) / "reads" / "m7_v01.json").read_text())["goal"]
    assert goal["value"] is None and goal["met"] is False and "differs from its store" in goal["withheld"]


def test_the_other_commands(R, monkeypatch):
    monkeypatch.setattr(MJ, "family_tries", lambda family, root="NQ", path=None: 4)
    monkeypatch.setattr(MJ, "family_best_t", lambda family, root="NQ": 4.1)
    assert door(["tries", "7", "orb"]) == {"family": "orb", "family_on_file": 4, "mission": 0, "total": 4, "needed_t": 2.75}
    assert door(["reach", "7", "orb"])["reachable"] is True
    assert door(["gate", "7", "m7_v01", "12"])["clear"] is True
    assert len(door(["accounts"])) == 18
    with pytest.raises(ValueError):
        door(["tries", "x", "orb"])


def test_main_prints_json_and_a_refusal_is_exit_1(R, capsys):
    assert D.main(["read", "7", "m7_v01", "12"]) == 0
    assert json.loads(capsys.readouterr().out) == {"held": True, "line": None, "close": None}
    assert D.main(["read", "7", "m7_v01", "12"]) == 1
    assert "already read" in json.loads(capsys.readouterr().out)["refused"]
    assert D.main(["tries", "0", "orb"]) == 1


def test_the_bash_door_runs_only_its_commands():
    for argv in (["pipe", "list"], ["wf", "oos", "m7_v01", "1"], []):
        r = subprocess.run([str(JUDGE), *argv], capture_output=True, text=True)
        assert r.returncode == 2 and "refused" in r.stdout
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_door.py -v`
Expected: FAIL (`ImportError: cannot import name 'missiondoor'`)

- [ ] **Step 3: Add the read to `research/edge-library/blueprint/missionjudge.py`**

```python
# ================================================================ the test months: one read a version, then frozen

LINES = ("too few trades", "lost money", "flipped direction", "under the bar", "missed the goal")
CLOSE = 1.0                         # "close" = under the bar by less than this many points


def spec_id(m: dict) -> str:
    """What a version IS, whatever it is named: the settings its in-sample store was run from."""
    keys = ("family", "root", "tf", "sessions", "exits", "fixed", "limits", "variants")
    return hashlib.sha256(json.dumps({k: m.get(k) for k in keys}, sort_keys=True, default=str).encode()).hexdigest()[:16]


def verdict_for_workers(test: dict, k: int) -> dict:
    """ALL A WORKER HEARS OF A READ: held or broke, which line, close or far. test = {"trades", "net", "points_over", "goal_met"} of the
    test months; k = which read of the mission this is (1 = its first): it needs points over above k - 1."""
    bar, pts = float(k - 1), test["points_over"]
    if test["trades"] < REAL.MIN_TRADES_OOS:
        return {"held": False, "line": LINES[0], "close": None}
    if test["net"] <= 0:
        return {"held": False, "line": LINES[1], "close": None}
    if pts is None or pts <= 0:
        return {"held": False, "line": LINES[2], "close": pts is not None and bar - pts < CLOSE}
    if pts <= bar:
        return {"held": False, "line": LINES[3], "close": bar - pts < CLOSE}
    if not test["goal_met"]:
        return {"held": False, "line": LINES[4], "close": None}
    return {"held": True, "line": None, "close": None}


def _failed(g: dict) -> str:
    bad = [f"{x['line']}: {x['said']}" for x in g["lines"] if not _ok(x["ok"])] + [f"{c['charge']}: {c['why']}" for c in g["charges"] if not c["held"]]
    return "; ".join(bad) or "the goal is not met in-sample"


def read(mid, name: str, box, said=None) -> dict:
    """THE TEST-MONTH READ OF ONE VERSION (module docstring): -> only what the workers may hear, {"held", "line", "close"}."""
    _no_server()
    M = missions()
    mid = M.validate_id(mid)
    br = M.brief(mid)                                # (a MissionError, a ValueError: no approved brief)
    if not isinstance(name, str) or not name.startswith(M.prefix(mid)):
        raise J.Refuse(f"{name!r}: not a version of mission {mid} (its names start with {M.prefix(mid)!r})")
    b = _box(name, box)
    bid, sid, froz = b["row"]["box"], spec_id(b["m"]), M.frozen(mid)
    if name in froz:
        raise J.Refuse(f"{name}: already read on its test months: frozen")
    twin = next((n for n, h in froz.items() if h == sid), None)
    if twin:
        raise J.Refuse(f"{name}: the same settings as {twin}, which was already read: a copy under a new name is not read again")
    if br["test_months"] == "ask":
        if not isinstance(said, str) or not said.strip():
            raise J.Refuse(f"mission {mid} asks the owner before every read: give his words (--said)")
        owner_said = said.strip()
    else:
        owner_said = br["owner_said"]
    g = gate(mid, name, box)
    if not g["clear"]:
        raise J.Refuse(f"{name} box {bid}: not clear in-sample ({_failed(g)}): no test month is read")
    who = f"mission:{mid}"

    def used() -> None:                              # frozen, and the read is a try
        M.freeze(mid, name, sid)
        M.record(mid, "read", name, hash=sid)

    api.wf_pick(name, bid, who)
    try:
        api.wf_oos(name, bid, owner_said, who=who)
    except BaseException:
        if RD.wf_oos_on_file(b["home"].name, bid):   # it stopped after its claim: the read is used all the same
            used()
        raise                                        # refused before the claim (the tester is busy): the read is not used
    used()                                           # before any number is worked out: a crash below still leaves it frozen
    b = _box(name, bid)                              # now with the lock and the test-month record on file
    rec, pts = b["oos"]["record"], _points(b, "oos")
    k = sum(1 for r in M.ledger(mid) if r.get("kind") == "read")
    try:
        goal = goal_value(mid, name, b, "oos")
    except J.Refuse as e:                            # (a Mismatch: the number is withheld, with the reason)
        goal = {"kind": br["goal"]["kind"], "target": br["goal"]["target"], "value": None, "met": False, "withheld": str(e)}
    v = verdict_for_workers({"trades": rec["trades"], "net": rec["net"], "points_over": pts["points_over"], "goal_met": goal["met"]}, k)
    owner = {"mission": mid, "name": name, "box": bid, "who": who, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "read_number": k, "bar": k - 1, "trades": rec["trades"], "net": rec["net"], "win_rate": rec.get("win_rate"),
             "points_over": pts["points_over"], "goal": goal, "blocks": b["oos"].get("blocks"), "verdict": v,
             "in_sample": {k2: g2 for k2, g2 in b["row"].items() if k2 in ("n", "trades", "net", "t_stat", "win_rate")}}
    d = M.mission_dir(mid) / "reads"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(owner, indent=1, default=str), encoding="utf-8")
    return v
```

- [ ] **Step 4: Write `research/edge-library/blueprint/missiondoor.py`**

```python
"""missiondoor.py -- THE MISSIONS JUDGE'S COMMAND LINE (research/edge-library/missions/judge runs it). JSON on stdout.

    accounts                                the prop accounts a goal may name (missionacct.accounts)
    tries <mid> <family>                    the family's tries on file + the mission's, and the t a version needs now
    reach <mid> <family>                    can the family still reach the t the next version needs?
    charges <mid> <name> <box>              the five charges (in-sample: a worker may see it)
    gate <mid> <name> <box>                 the five lines, the charges and the goal (in-sample: a worker may see it)
    read <mid> <name> <box> [--said TEXT]   the test months, once: prints ONLY {"held", "line", "close"}

A refusal prints {"refused": why} and exits 1."""
from __future__ import annotations

import argparse
import json
import sys

import judge as J

from . import missionacct as A
from . import missionjudge as MJ


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="missions/judge", description="The Missions Judge")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("accounts")
    for c in ("tries", "reach"):
        s = sub.add_parser(c)
        s.add_argument("mid")
        s.add_argument("family")
    for c in ("charges", "gate", "read"):
        s = sub.add_parser(c)
        s.add_argument("mid")
        s.add_argument("name")
        s.add_argument("box")
        if c == "read":
            s.add_argument("--said", help="the owner's words for this read (a mission whose brief says test_months: ask)")
    return p


def run(a):
    if a.cmd == "accounts":
        return A.accounts()
    mid = MJ.missions().validate_id(a.mid)
    if a.cmd == "tries":
        return MJ.tries_of(mid, a.family)
    if a.cmd == "reach":
        return MJ.reach(mid, a.family)
    if a.cmd == "charges":
        return MJ.charges(mid, a.name, a.box)
    if a.cmd == "gate":
        return MJ.gate(mid, a.name, a.box)
    return MJ.read(mid, a.name, a.box, a.said)


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    try:
        out = run(a)
    except (J.Refuse, ValueError) as e:
        print(json.dumps({"refused": str(e)}))
        return 1
    print(json.dumps(out, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Write `research/edge-library/missions/judge`** and make it executable (`chmod +x research/edge-library/missions/judge`)

```bash
#!/bin/bash
# The Missions Judge's ONLY door (owner, 2026-11-14). A Missions worker or the Missions app can ask it for the accounts, the tries, whether a
# family is still in reach, the charges and the gate of a version (all in-sample), and for the one read of a version's test months, which
# prints only held / which line / close. Nothing else runs: no bp.py, no pick, no oos by hand.
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PY="${MISSIONS_PY:-$HERE/../../.venv-research/bin/python}"
cd "$HERE" || exit 2
case "${1:-}" in
  accounts|tries|reach|charges|gate|read) exec "$PY" -m blueprint.missiondoor "$@";;
esac
echo "refused: the Missions Judge runs only: accounts | tries | reach | charges | gate | read"; exit 2
```

- [ ] **Step 6: Run them to make sure they pass**

Run: `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_door.py tests/test_mission_judge.py tests/test_mission_accounts.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add research/edge-library/blueprint/missiondoor.py research/edge-library/blueprint/missionjudge.py research/edge-library/missions/judge research/edge-library/tests/test_mission_door.py
git commit -m "Missions Judge: the door (accounts, tries, reach, charges, gate, read); a read is frozen first, workers hear held/line/close"
```

---

### Task 7: The CLAUDE.md paragraph and the smoke test

**Files:**
- Modify: `CLAUDE.md` (one section, straight after the section "The hunt loop tests by itself, on the mini (owner, 2026-11-09)" and before "Sharpe counts only the days that traded")

The dead-family list (`~/Obsidian/Vault/30-Projects/Onyx-Trading/dead-families.md`) is a vault note, not a repo file: the
controller writes it, not this task.

- [ ] **Step 1: Add this section to `CLAUDE.md`, word for word**

```markdown
## Missions (owner, 2026-11-14)

Missions is its own app (`~/missions`): a team of Claude agents chases one strategy goal. Its workers reach Homebase only through
the connector's mission mode (`python -m homebase.claude_mcp --mission <id>`, `homebase/claude_mcp/mission.py`): a short tool list,
their own names only (`m<id>_*`, drafts `draft_m<id>_*`), the in-sample months only. **Only the Missions Judge**
(`research/edge-library/missions/judge`, fixed code) may read a mission version's test months: once a version, marked
`who: mission:<id>`, then the version is frozen and its workers hear only held / which line / close. This is for Missions only:
every other agent still needs the owner's word for a heat map and for the test months. A mission's state is
`~/.homebase/missions/<id>/` (its brief, its ledger of tries, its frozen versions, its refused calls, the owner's numbers of each
read). An eval goal names one of the 18 prop accounts of 2026-11-14 (`missions/judge accounts`; Lucid Flex and Pro are closed).
The Judge never runs on the server. Never edit a mission's files by hand, and never use an `m<id>_*` name for anything else.
```

- [ ] **Step 2: Smoke test, no engine** (cwd: the worktree root)

```bash
T=$(mktemp -d) && mkdir -p "$T/999" && printf '%s' '{"approved": true, "owner_said": "smoke test brief", "test_months": "team", "goal": {"kind": "points", "target": 3}}' > "$T/999/brief.json"
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"blueprint_wf_oos","arguments":{"name":"m999_x","box":"1","owner_said":"x"}}}' | HOMEBASE_MISSIONS="$T" ~/ramos-quant-homebase/.venv/bin/python -m homebase.claude_mcp --mission 999 > "$T/out.jsonl"
~/ramos-quant-homebase/.venv/bin/python -c "import json,sys; o=[json.loads(l) for l in open(sys.argv[1])]; print('MISSION MODE' in o[0]['result']['instructions'], len(o[1]['result']['tools']), o[2]['error']['message'])" "$T/out.jsonl"
cat "$T/999/refused.jsonl"
MISSIONS_PY=~/ramos-quant-homebase/.venv-research/bin/python research/edge-library/missions/judge accounts | ~/ramos-quant-homebase/.venv/bin/python -c "import json,sys; a=json.load(sys.stdin); print(len(a), a[0]['id'])"
```

Expected: the second command prints `True 21 unknown tool 'blueprint_wf_oos'`; `refused.jsonl` holds one line naming
`blueprint_wf_oos`; the last prints `18 apex-legacy-50k@2026-11-14`.

- [ ] **Step 3: Run every test this plan added, plus the old connector, prop sim, hunt and real-or-luck tests**

Run (worktree root): `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/test_missions_state.py tests/test_claude_mcp_mission.py tests/test_claude_mcp.py tests/test_claude_mcp_blueprint.py tests/test_backtest_propsim.py -q`
Run (`research/edge-library`): `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/test_mission_accounts.py tests/test_mission_judge.py tests/test_mission_door.py tests/test_blueprint_hunt.py tests/test_real.py -q`
Expected: all PASS

- [ ] **Step 4: Commit, and stop**

```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: Missions (mission mode, the Judge's door, m<id>_ names)"
```

The branch stays unmerged and unpushed. Merging it to `main` (which ships to the VPS) waits for the owner's word.

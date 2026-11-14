# Plan 1: the Homebase fence and the Judge

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Missions a safe way into Homebase: a connector "mission mode" that shows workers only the tools a mission
may use, and the Judge (fixed code) that grades a version, measures the goal on the owner's prop accounts, and is the
only door to the test months.

**Architecture:** All code in this plan lives in the Homebase repo (`~/ramos-quant-homebase`), on its own branch. Mission
state is a few files per mission under `~/.homebase/missions/<id>/`. The connector gets a `--mission <id>` flag that swaps
in a subclass of its `Toolbox` with an allowlist and per-tool guards. The Judge is a research module plus a bash door
modeled on `research/edge-library/hunt/bp`. It reuses `hunt.score`, `real.check`, `hmwf.pick/run_oos` and the tester's
own prop sim (`homebase/backtest/propsim.evaluate`), which reads all 18 of the owner's new accounts. The Missions app
itself (Plan 2) only calls these.

**Tech Stack:** Python 3 (the app's `.venv` for `homebase/`, `.venv-research` for `research/edge-library/`), pytest,
bash, numpy. No new dependency.

**Spec:** `~/missions/docs/specs/2026-11-14-missions-design.md` (approved 2026-11-14), sections 5, 6, 9 and 11, plus the
accounts amendment in section 5 (added with this plan).

## Global Constraints

- Work in a worktree on branch `feat/missions-fence` off `main`: `git worktree add ../homebase-missions-fence -b feat/missions-fence main`. Never commit in the main checkout (it is on another branch with other people's edits). A commit on `main` ships to the VPS by itself, so the branch is merged only on the owner's word.
- While building, never run a real heat map, a real in-sample table or a test-month read. Tests use temp folders, hand-made stores (`tests/blueprint_synth.py`), a fake `hmwf` and the `Fake` chart service (`tests/test_claude_mcp.py`).
- "i dont want to use the chicago server to backtest ever": every Judge command that runs the engine refuses when `~/.homebase/no_backtests` exists.
- NQ only. The pipeline stays off (never call `bp.py pipe`, never touch `pipe_*`). Never write `payout_enabled`.
- Mission ids are positive integers; every name a mission makes starts with `m<id>_` (e.g. `m7_v01`) and must still pass `ideastore.validate_name` / `draftstore.validate_name`.
- The test-month read is marked `who: mission:<id>`. One read per version, then the version is frozen.
- The read's bar: read number k of this mission needs points over > k − 1 (1st > 0, 2nd > +1, 3rd > +2; no cap). Close = under the bar by less than 1 point.
- The luck bar: t ≥ `real.T_BAR + real.T_PER_TRY × (tries − 1)` = 2.0 + 0.25 a try. A mission starts from `max(0, the family's tries on file)` (spec section 5; see the open question in the handoff).
- Workers hear only: held or broke, which line, close or far. No dollars, %, months or trade counts from the test months ever reach a worker; those go to a file only the app shows the owner.
- Eval goal: the tester's prop sim, pass within 10 weekdays (`horizon=10`), at a fixed risk = the account's drawdown (`trailing_mll`) ÷ 2.5, on the box re-run with worse fills (line 5's fills), each trade capped at the account's `cap_micros`.
- Lucid Flex and Lucid Pro are closed to the owner since 2026-11-14 ("I got moved to live and I can't use the flex or the pro accounts anymore"): a goal may not name them.

## Review Focus

1. A worker names another mission's version (`m3_x` from mission 7) or a non-mission idea (`owner_fvg_odir_15_nl_new`) in any tool: refused and logged, never run.
2. An exact copy of a frozen version is sent again under a new name (same spec hash): refused as already read; a changed copy is a new try and raises the bar.
3. The Judge is started on the server (`~/.homebase/no_backtests` exists): it refuses before any engine call.
4. The re-run of the picked box gives different trades from its store (a changed family file, a repaired tape): the eval number is withheld with the reason, never shown as if it were right.
5. A goal names a closed (`lucid-flex-50k@2026-10-11`) or unknown account: refused with the reason; an old version of an open account resolves to its newest file.

---

## Words used below

- **box**: a row number of the idea's in-sample table as text (`"12"`), the same thing `hmwf.pick(name, box)` takes.
- **J.Refuse**: the blueprint toolkit's refusal (`research/edge-library/judge.py`, `import judge as J`, as `hmwf` imports it); the Judge raises it for every "no".

## File map

| File | Status | Responsibility |
|---|---|---|
| `homebase/missions.py` | new | Mission state: ids, the brief, the ledger, tries, frozen versions, refused calls |
| `homebase/claude_mcp/mission.py` | new | `MissionToolbox`: allowlist + guards over `Toolbox` |
| `homebase/claude_mcp/protocol.py` | modify `Server.__init__`, `main()` | `--mission <id>`; mission instructions text |
| `research/edge-library/blueprint/missionacct.py` | new | The owner's prop accounts: list, resolve, facts, bans |
| `research/edge-library/blueprint/missionjudge.py` | new | Box re-run, sizing, eval odds, charges, tries, gate, reach, the read's verdict |
| `research/edge-library/blueprint/missiondoor.py` | new | The Judge's CLI (JSON out) |
| `research/edge-library/missions/judge` | new | The bash door (like `hunt/bp`) |
| `CLAUDE.md` | modify | One Missions paragraph |
| `~/Obsidian/Vault/30-Projects/Onyx-Trading/dead-families.md` | new (vault, not the repo) | The dead-family list, empty table |
| Tests | new | `tests/test_missions_state.py`, `tests/test_claude_mcp_mission.py`, `research/edge-library/tests/test_mission_accounts.py`, `research/edge-library/tests/test_mission_judge.py`, `research/edge-library/tests/test_mission_door.py` |

Commands used below:
- App tests: `cd ../homebase-missions-fence && .venv/bin/python -m pytest tests/<file> -v`
- Research tests: `cd ../homebase-missions-fence/research/edge-library && ../../.venv-research/bin/python -m pytest tests/<file> -v`

(The worktree has no venvs of its own: use the main checkout's by absolute path, `~/ramos-quant-homebase/.venv/bin/python` and `~/ramos-quant-homebase/.venv-research/bin/python`, with the cwd inside the worktree.)

---

### Task 1: Mission state

**Files:**
- Create: `homebase/missions.py`
- Test: `tests/test_missions_state.py`

**Interfaces:**
- Consumes: `homebase.paths.from_env` (as `ideastore.ideas_root()` uses it).
- Produces:
  - `ENV = "HOMEBASE_MISSIONS"`; `root() -> Path` (default `~/.homebase/missions`)
  - `class MissionError(ValueError)`
  - `validate_id(mid) -> int`; `mission_dir(mid) -> Path`; `prefix(mid) -> str` (`"m7_"`)
  - `brief(mid) -> dict`: `{id, approved, owner_said, test_months: "team"|"ask", goal: {kind: "eval"|"points"|"net", target: float, rule: str|None}}`
  - `spec_hash(spec: dict) -> str` (16 hex)
  - `record(mid, kind: str, ref: str, spec: dict | None = None) -> dict`; kinds `"run"`, `"job"`, `"wf"`, `"draft"`, `"read"`
  - `owns(mid, kind, ref) -> bool`
  - `tries(mid) -> int`
  - `freeze(mid, name: str, h: str) -> None`; `frozen(mid) -> dict[str, str]` (name → spec hash)
  - `refused(mid, tool: str, args: dict, why: str) -> None`

- [ ] **Step 1: Write the failing tests** (an autouse fixture sets `HOMEBASE_MISSIONS` to `tmp_path`)

```python
def test_ids_are_positive_integers():
    assert M.validate_id(7) == 7 and M.validate_id("7") == 7
    for bad in (0, -1, True, "7a", None, 1.5):
        with pytest.raises(M.MissionError):
            M.validate_id(bad)
    assert M.prefix(7) == "m7_"

def test_brief_must_be_approved_and_complete(tmp_path):
    write_brief(7, approved=False)
    with pytest.raises(M.MissionError, match="not approved"):
        M.brief(7)
    write_brief(7, approved=True, test_months="maybe")
    with pytest.raises(M.MissionError, match="test_months"):
        M.brief(7)
    write_brief(7, approved=True, goal={"kind": "eval", "target": 0.5, "rule": "topstep-50k@2026-11-14"})
    assert M.brief(7)["goal"]["kind"] == "eval"
    with pytest.raises(M.MissionError, match="no brief"):
        M.brief(8)

def test_tries_count_distinct_specs_of_runs_and_wf_only():
    M.record(7, "run", "r1", {"a": 1}); M.record(7, "run", "r2", {"a": 1})   # same spec twice = 1 try
    M.record(7, "wf", "m7_v01", {"a": 2}); M.record(7, "draft", "m7_d", {"a": 3})
    assert M.tries(7) == 2 and M.owns(7, "run", "r2") and not M.owns(7, "run", "r9")

def test_spec_hash_ignores_key_order():
    assert M.spec_hash({"a": 1, "b": 2}) == M.spec_hash({"b": 2, "a": 1})

def test_freeze_and_refused_are_kept():
    M.freeze(7, "m7_v01", "abc"); assert M.frozen(7) == {"m7_v01": "abc"}
    M.refused(7, "backtest", {"range": "x"}, "range is closed")
    assert "range is closed" in (M.mission_dir(7) / "refused.jsonl").read_text()
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `.venv/bin/python -m pytest tests/test_missions_state.py -v`
Expected: FAIL (`ModuleNotFoundError: homebase.missions`)

- [ ] **Step 3: Implement `homebase/missions.py`**

Files per mission: `brief.json` (written by the app in Plan 2; this module only reads it), `ledger.jsonl`,
`frozen.json`, `refused.jsonl`. `record` and `freeze` take an `fcntl.flock` on `mission_dir/.lock`, because several
workers write at once. `spec_hash` = `sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")))[:16]`.
`tries` counts distinct hashes of kinds `"run"` and `"wf"` only (my call: every submitted spec counts, even one that
later errors; that only raises the bar, and the connector cannot see when an async run finishes).

- [ ] **Step 4: Run them to make sure they pass**

Run: `.venv/bin/python -m pytest tests/test_missions_state.py -v`
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
- Modify: `homebase/claude_mcp/protocol.py` (`Server.__init__` takes `instructions: str | None = None`; `main()` reads `--mission <id>`)
- Test: `tests/test_claude_mcp_mission.py` (reuse `Fake` and the `fake` fixture from `tests/test_claude_mcp.py`)

**Interfaces:**
- Consumes: Task 1 (`brief`, `prefix`, `record`, `owns`, `frozen`, `refused`, `spec_hash`); `tools.Toolbox`, `tools.ToolError`; `Toolbox._post_run(body) -> run_id`; `BlueprintMixin._bp(args, ...) -> dict`.
- Produces: `class MissionToolbox(tools.Toolbox)` with `__init__(self, mid, **kw)`, `specs()`, `names()`, `call(name, args)`; `ALLOW: frozenset[str]`; `MISSION_INSTRUCTIONS: str`.

The allowlist and the guards (a guard refuses with `ToolError`, and logs through `missions.refused` first):

| Tool | Guard |
|---|---|
| `list_strategies`, `list_prop_rules`, `blueprint_blocks` | none |
| `read_strategy` | only drafts with the mission's prefix (docstrings elsewhere can hold test-month numbers) |
| `write_strategy`, `delete_draft`, `set_group` | name has the prefix; `write_strategy` records `"draft"` |
| `backtest` | refuse `range`, `runs`, `run_ids`; `strategy` has the prefix; `run_id` (waiting on a run) must be owned; `owner_said` dropped (in-sample only) |
| `get_run`, `trades`, `montecarlo`, `prop_eval`, `day_types`, `cancel` | `run_id` must be owned; `grid_id`, `cell`, `walkforward_id` refused |
| `list_runs` | result filtered to owned run ids |
| `blueprint_card` | name has the prefix |
| `blueprint_code_check` | name has the prefix; `store` and `trades_file` refused |
| `blueprint_wf` | `name` or `card["name"]` has the prefix; `owner_said` replaced by the brief's `owner_said` (whatever the worker sent); records `"wf"` with the card as spec; refused if that spec's hash is already frozen |
| `blueprint_status` | `name` has the prefix, or `job_id` is owned; neither = refused (it would list every idea) |
| `blueprint_heatmap` | name has the prefix |
| `blueprint_mc` | name has the prefix; `on="test"` refused |
| any tool | a name that is frozen is refused ("already read: frozen") |

Not in `ALLOW` (so not listed and refused): `heatmap`, `walkforward` (no Judge route in v1), `show_on_chart`,
`blueprint_wf_pick`, `blueprint_wf_oos` (only the Judge reads test months), `blueprint_sim`, `blueprint_portfolio`,
`blueprint_eval_card`, every `desk_*`, `data_coverage`, `services_health`, `account_*`, `export_*`, `write_strategy`
for a name without the prefix.

- [ ] **Step 1: Write the failing tests**

```python
def test_lists_only_the_allowlist(mbox):
    assert set(mbox.names()) == MI.ALLOW
    assert "blueprint_wf_oos" not in mbox.names() and "desk_status" not in mbox.names()

def test_refuses_other_missions_and_plain_ideas(mbox):
    for args in ({"name": "m3_x"}, {"name": "owner_fvg_odir_15_nl_new"}):
        with pytest.raises(ToolError, match="not this mission"):
            mbox.call("blueprint_heatmap", args)
    assert "blueprint_heatmap" in refused_log(7)

def test_backtest_range_and_batches_are_closed(mbox):
    for extra in ({"range": {"start": "2025-07-01"}}, {"runs": [{}]}, {"run_ids": ["r1"]}):
        with pytest.raises(ToolError):
            mbox.call("backtest", {"strategy": "m7_d", **extra})

def test_backtest_records_its_run_and_views_need_an_owned_run(mbox, fake):
    mbox.call("backtest", {"strategy": "m7_d", "wait_s": 0})
    rid = only_run_id(7)                       # the id the Fake service handed out
    mbox.call("get_run", {"run_id": rid})      # owned: allowed
    with pytest.raises(ToolError, match="not this mission"):
        mbox.call("get_run", {"run_id": "someone-elses"})

def test_wf_uses_the_brief_words_and_refuses_a_frozen_copy(mbox, bp_calls):
    mbox.call("blueprint_wf", {"name": "m7_v01", "owner_said": "anything a worker types"})
    assert bp_calls[-1]["owner_said"] == BRIEF["owner_said"]
    M.freeze(7, "m7_v01", M.spec_hash(CARD_V01))
    with pytest.raises(ToolError, match="already read"):
        mbox.call("blueprint_wf", {"card": {**CARD_V01, "name": "m7_v02"}, "owner_said": "x"})

def test_mc_on_test_months_and_code_check_sources_are_refused(mbox):
    with pytest.raises(ToolError): mbox.call("blueprint_mc", {"name": "m7_v01", "on": "test"})
    with pytest.raises(ToolError): mbox.call("blueprint_code_check", {"name": "m7_v01", "store": "x"})

def test_unapproved_brief_stops_the_server_from_starting():
    write_brief(9, approved=False)
    with pytest.raises(M.MissionError):
        MI.MissionToolbox(9)
```

`mbox` builds `MissionToolbox(7, client=fake_client)` over an approved brief; `bp_calls` replaces `_bp` with a
recorder that returns `{"ok": True, "job_id": "j1"}` and keeps the `--owner-said=` value it was given. Only the brief's
`owner_said` key matters for the wf test; how the card spec is turned into `CARD_V01` follows `t_blueprint_wf`.

- [ ] **Step 2: Run them to make sure they fail**

Run: `.venv/bin/python -m pytest tests/test_claude_mcp_mission.py -v`
Expected: FAIL (`ModuleNotFoundError: homebase.claude_mcp.mission`)

- [ ] **Step 3: Implement `MissionToolbox` in `homebase/claude_mcp/mission.py`**

Override `specs()` and `names()` to filter by `ALLOW`. `call()` checks `ALLOW`, the frozen names, then a guard
table `{tool: fn(self, args) -> args}` that may rewrite args (the wf words), then `super().call`. Override
`_post_run(body)` to record `"run"` with `body` as spec, and `_bp(...)` to record any top-level `job_id` in its
result as `"job"`. `list_runs` filters its result after `super().call`. `MISSION_INSTRUCTIONS` is a short text: this
is mission <id>, names start with `m<id>_`, in-sample only, the test months belong to the Judge.

- [ ] **Step 4: Wire `--mission` in `protocol.py`**

`main()`: if `sys.argv` has `--mission <id>`, `serve(server=Server(MissionToolbox(id), instructions=MISSION_INSTRUCTIONS))`;
otherwise unchanged. `Server.handle("initialize")` returns `self.instructions or INSTRUCTIONS`. A bad id or an
unapproved brief: log it and exit 2 (the worker then has no connector, which is the safe failure).

- [ ] **Step 5: Run the tests (new and old)**

Run: `.venv/bin/python -m pytest tests/test_claude_mcp_mission.py tests/test_claude_mcp.py -v`
Expected: PASS (the old connector tests are untouched by the mission mode)

- [ ] **Step 6: Commit**

```bash
git add homebase/claude_mcp/mission.py homebase/claude_mcp/protocol.py tests/test_claude_mcp_mission.py
git commit -m "Missions: connector mission mode (allowlist, owned names and runs, wf words from the brief)"
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
- Consumes: `propodds.app()` (the app's propsim module: `list_rules()`, `load_rules(rule_id)`).
- Produces:
  - `SET = "2026-11-14"`: an account is open only when it has a file of this set (his buying list: exactly the 18)
  - `CLOSED = {"lucid-flex-": "moved to Lucid live 2026-11-14: no Flex", "lucid-pro-": "moved to Lucid live 2026-11-14: no Pro"}`; any other account without a `SET` file (today `apex-eod-50k`) is closed as "not one of the 2026-11-14 accounts"
  - `BANS: dict[str, str]`, keyed by rule-id prefix
  - `accounts() -> list[dict]`: `facts` of the newest file of every open account (18 today), sorted by firm then size
  - `resolve(rule_id: str) -> str`: the newest file of that account (`topstep-50k@2026-10-01` → `topstep-50k@2026-11-14`); `J.Refuse` if closed or unknown
  - `facts(rule_id) -> dict`: `{id, name, size, drawdown, risk, target, cap_micros, two_step, funded_rules, intraday, confirmed, bans: [str]}`, where `risk = drawdown / 2.5`

`BANS` (exact text, from the 2026-11-14 audit, `research/edge-library/prop_rules_2026-11-14/*.md`):
- `"apex-"`: "Apex bans automation on every account, evals included: a bot cannot trade it inside the rules."
- `"topstep-"`: "Topstep: a VPS may watch but not place orders: the Chicago Desk cannot trade it."
- `"mffu-"`: "MFFU bans straddles and strangles on all news, every account; Tier-1 news (FOMC, minutes, NFP, CPI) is banned on Rapid sim funded."
- `"lucid-"`: "Lucid while live: no new eval of any kind until the live account is blown, plus a 2-week cooldown; no new Maxx while live."

These are shown (on the brief and the Eval pass page), not checked by code: news windows, flat-by times and the other
"not simulated" rules in the audit stay the strategy's own job.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_18_new_accounts_are_open_and_flex_pro_are_closed():
    ids = {a["id"] for a in A.accounts()}
    assert {"topstep-50k@2026-11-14", "apex-legacy-50k@2026-11-14", "mffu-rapid-eod-50k-dll@2026-11-14",
            "lucid-maxx-50k@2026-11-14", "lucid-live-25k@2026-11-14", "mffu-builder-100k@2026-11-14"} <= ids
    assert len(ids) == 18 and all(i.endswith("@2026-11-14") for i in ids)
    with pytest.raises(J.Refuse, match="no Flex"):
        A.resolve("lucid-flex-50k@2026-10-11")
    with pytest.raises(J.Refuse, match="not one of the 2026-11-14"):
        A.resolve("apex-eod-50k@2026-10-11")
    with pytest.raises(J.Refuse, match="no account"):
        A.resolve("nobody-50k@2026-11-14")

def test_an_old_version_resolves_to_the_newest_file():
    assert A.resolve("apex-legacy-50k@2026-10-11") == "apex-legacy-50k@2026-11-14"

def test_facts_risk_is_drawdown_over_two_and_a_half_and_bans_are_attached():
    f = A.facts("topstep-50k@2026-11-14")
    assert f["drawdown"] == 2000 and f["risk"] == 800.0 and f["cap_micros"] == 50
    assert any("VPS" in b for b in f["bans"])
    assert A.facts("lucid-maxx-25k@2026-11-14")["two_step"] is True
    assert A.facts("apex-legacy-100k@2026-11-14")["intraday"] is True
    assert A.facts("mffu-rapid-50k@2026-11-14")["funded_rules"] is True
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_accounts.py -v`
Expected: FAIL (`ModuleNotFoundError: blueprint.missionacct`)

- [ ] **Step 3: Implement `research/edge-library/blueprint/missionacct.py`**

The account name is the id before `@`; "newest" sorts on the text after `@` (dates, and suffixes like `2026-09-27b`).
`two_step = "step2" in r`, `funded_rules = bool(r.get("funded"))`, `intraday = r.get("trail") == "intraday"` (or the
funded block's trail), `confirmed = r.get("confirmed") is not False`.

- [ ] **Step 4: Run them to make sure they pass**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_accounts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/edge-library/blueprint/missionacct.py research/edge-library/tests/test_mission_accounts.py
git commit -m "Missions: the owner's prop accounts (the 18 new files open, Flex/Pro closed, bans shown)"
```

---

### Task 4: The picked box's full trades and its eval odds

Why a re-run: the 3:1 stores keep each trade's low (`mae`) but not its high, and `propodds` refuses 12 of the 18 new
accounts (Apex Legacy's intraday trail, Lucid Maxx's two steps, MFFU Rapid's funded block, the Lucid live and Builder
payout day counts). The tester's own `propsim.evaluate` reads all 18, but needs each trade's `mfe_usd`. So the Judge
re-runs the one picked box with the engine's full trade rows, the way `runner.cell_trades` does for charts, but on the
3:1 months, and checks the re-run against the store.

**Files:**
- Create: `research/edge-library/blueprint/missionjudge.py` (this task: `box_trades`, `sized_trades`, `eval_odds`, `on_server`)
- Test: `research/edge-library/tests/test_mission_judge.py`

**Interfaces:**
- Consumes: Task 3 (`resolve`, `facts`); `runner.cell_trades` (the pattern), `runner.worse_kw(two_sided)`, `l2sim.run_many(..., allow_holdout=S.ALLOW_WF_IS | S.ALLOW_WF_OOS)`, `wfmonths.is_days(root)`, `hmwf.show(name)`, `library.pack`, `library.sized(x, root, risk_usd)`, `propodds.app().evaluate(trades, rule_id, horizon=, contract=)`.
- Produces:
  - `class Mismatch(J.Refuse)`
  - `on_server() -> bool` (`~/.homebase/no_backtests` exists)
  - `box_trades(name, box, on: "is"|"oos", worse: bool = False, mid: int | None = None) -> list[dict]`
  - `sized_trades(trades: list[dict], root: str, risk_usd: float, cap_micros: int) -> list[dict]`
  - `eval_odds(name, box, rule_id, on: "is"|"oos" = "is", mid=None) -> dict`: `{rule, risk, pass_p, pass_ci, bust_p, days_to_pass, worst_case_pass_p, size, caveat}`

- [ ] **Step 1: Write the failing tests** (the engine is replaced by a fake that returns hand-made trade rows with `mae_usd` and `mfe_usd`; `blueprint_synth.no_engine()` guards that nothing else runs)

```python
def test_box_trades_must_match_the_store(fake_box):
    fake_box(store_trades=40, store_net=1200.0, rerun_trades=40, rerun_net=1200.0)
    assert len(MJ.box_trades("m7_v01", "12", "is")) == 40
    fake_box(store_trades=40, store_net=1200.0, rerun_trades=39, rerun_net=1100.0)
    with pytest.raises(MJ.Mismatch, match="differs from its store"):
        MJ.box_trades("m7_v01", "12", "is")

def test_test_months_rerun_only_after_this_missions_read(fake_box):
    fake_box(lock_who="owner")
    with pytest.raises(J.Refuse, match="read by this mission"):
        MJ.box_trades("m7_v01", "12", "oos", mid=7)

def test_sizing_matches_the_library_and_stops_at_the_contract_limit():
    rows = [trade_row(net=96.0, mae=40.0, mfe=200.0, stop_pts=10.0)]          # 1 NQ contract, $20 a point
    s = MJ.sized_trades(rows, "NQ", risk_usd=800.0, cap_micros=50)[0]
    assert s["qty"] == 40 and s["net"] == pytest.approx(40 * ((96.0 + 4.0) / 10 - 1.0))
    assert s["mfe_usd"] == pytest.approx(40 * 200.0 / 10) and s["commission"] == pytest.approx(40 * 1.0)
    assert MJ.sized_trades(rows, "NQ", risk_usd=8000.0, cap_micros=50)[0]["qty"] == 50

def test_eval_odds_reads_every_new_account_shape(fake_box):
    fake_box(store_trades=60, store_net=3000.0, rerun_trades=60, rerun_net=3000.0)
    for rid in ("topstep-50k@2026-11-14", "apex-legacy-50k@2026-11-14", "lucid-maxx-50k@2026-11-14", "mffu-rapid-50k@2026-11-14"):
        e = MJ.eval_odds("m7_v01", "12", rid)
        assert 0.0 <= e["pass_p"] <= 1.0 and e["risk"] == A.facts(rid)["risk"]
    assert MJ.eval_odds("m7_v01", "12", "apex-legacy-50k@2026-11-14")["worst_case_pass_p"] is not None

def test_the_server_never_runs_the_engine(monkeypatch, tmp_path):
    flag_server(monkeypatch, tmp_path)                     # HOME with .homebase/no_backtests
    with pytest.raises(J.Refuse, match="server"):
        MJ.box_trades("m7_v01", "12", "is")
```

The sizing test pins `library.sized`'s micro model: micros = `max(1, round(risk_usd / (stop_pts × $2)))`; net =
micros × ((1-contract net + `COMM_RT` 4.00) / 10 − `MICRO_RT_USD` 1.00); MAE and MFE scale by micros / 10.

- [ ] **Step 2: Run them to make sure they fail**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_judge.py -v`
Expected: FAIL (`ModuleNotFoundError: blueprint.missionjudge`)

- [ ] **Step 3: Implement `box_trades`**

Refuse first if `on_server()`. Read the idea's store meta and the box's settings (`hmwf.show(name)`), the same cell
`runner.cell_trades` would find. Days: `on="is"` = the store's own months (`run.json` `days`, as `hmwf.run_is` uses);
`on="oos"` = the read's months (the oos store's days), refused unless `lock.json` `who == f"mission:{mid}"` and the oos
store exists, and run one month a call (`ALLOW_WF_OOS` allows one). `worse=True` adds `runner.worse_kw(...)` exactly
as `runner.worse_part` does. Parity: the re-run's trade count and its net (1 contract) equal the store's for that box
(the row's `worse_fills_net` when `worse=True`), to the cent; else `Mismatch` naming both numbers.

- [ ] **Step 4: Implement `sized_trades` and `eval_odds`**

`sized_trades` packs the rows with `library.pack`, gets each trade's micros from `library.sized`, caps them at
`cap_micros`, then scales `net`, `mae_usd`, `mfe_usd`, `commission` and sets `qty` (micros) on copies of the rows.
`eval_odds` = `resolve` → `facts` → `box_trades(..., worse=True)` → `sized_trades(..., facts["risk"], facts["cap_micros"])`
→ `propsim.evaluate(rows, rule_id, horizon=10, contract="MNQ")`; it returns the headline's `eval_pass_p`,
`eval_pass_ci`, `bust_p`, `median_days_to_pass`, `trail_worst_case.eval_pass_p` (intraday accounts, else None),
`size` and `caveat`.

- [ ] **Step 5: Run them to make sure they pass**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_judge.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add research/edge-library/blueprint/missionjudge.py research/edge-library/tests/test_mission_judge.py
git commit -m "Missions Judge: the picked box re-run with full trades, sized to the account, eval odds on every new account"
```

---

### Task 5: Charges, tries, the gate and out of reach

**Files:**
- Modify: `research/edge-library/blueprint/missionjudge.py`
- Test: `research/edge-library/tests/test_mission_judge.py` (more tests)

**Interfaces:**
- Consumes: Task 1 (`brief`, `tries`, the ledger); Task 4 (`eval_odds`); `hunt.score(name)` (its `rows`, `pick`, `over`); `real.check(s, tries)` and its constants; `hmwf.is_table`, `hmwf.RUNS`; `research/edge-library/ledger.csv`.
- Produces:
  - `DEAD_ENV = "HOMEBASE_DEAD_FAMILIES"`; `dead_families() -> set[str]`
  - `family_tries(family, root="NQ") -> int`; `start_tries(family) -> int`; `t_needed(tries) -> float`
  - `family_best_t(family, root="NQ") -> float | None`
  - `sides(name, box) -> {"long": float, "short": float}`
  - `charges(mid, name, box) -> list[{"charge", "held": bool, "why"}]`
  - `goal_in_sample(mid, name, box) -> {"kind", "target", "value", "met": bool}`
  - `gate(mid, name, box) -> {"clear": bool, "lines": [...], "charges": [...], "goal": {...}, "tries": int}`
  - `reach(mid, family) -> {"needed_t", "best_t", "reachable": bool}`

The five charges (all run on every version):

| Charge | Held when |
|---|---|
| One year carries it | `real.check` line 4 (years) passes |
| Worse fills kill it | line 5 (worse fills) passes |
| It looks ahead | the idea's code check result (`check.json`) says passed |
| One side carries it | long net > $0 and short net > $0 (a one-sided idea: its one side > $0) |
| It is a dead family again | the family is not on the dead list |

- [ ] **Step 1: Write the failing tests**

```python
def test_tries_bar_and_start_from_the_family_on_file(ledger_csv):
    ledger_csv([("wf_is", "a-NQ-tf15/is", "orb"), ("wf_oos", "a-NQ-tf15/oos", "orb"),
                ("build", "b-NQ-tf15", "orb"), ("null", "c-NQ-tf15", "orb"), ("wf_is", "d-ES-tf15/is", "orb")])
    assert MJ.family_tries("orb") == 3               # wf_is / wf_oos / build / bp_build keys, NQ only, distinct
    assert MJ.t_needed(1) == 2.0 and MJ.t_needed(5) == 3.0

def test_dead_list_reads_the_vault_table(tmp_path, monkeypatch):
    (tmp_path / "dead.md").write_text("| family | verdict | date | why |\n|---|---|---|---|\n| win_bracket | dead | 2026-11-14 | x |\n")
    monkeypatch.setenv(MJ.DEAD_ENV, str(tmp_path / "dead.md"))
    assert MJ.dead_families() == {"win_bracket"}

def test_one_side_carries_it(fake_store):
    fake_store(long_net=2000.0, short_net=-300.0)
    c = {x["charge"]: x for x in MJ.charges(7, "m7_v01", "12")}
    assert c["One side carries it"]["held"] is False

def test_gate_needs_the_five_lines_the_charges_and_the_goal(fake_store):
    fake_store(passing=True, goal={"kind": "points", "target": 3.0}, points_over=3.4)
    assert MJ.gate(7, "m7_v01", "12")["clear"] is True
    fake_store(passing=True, goal={"kind": "points", "target": 3.0}, points_over=2.9)
    assert MJ.gate(7, "m7_v01", "12")["clear"] is False

def test_out_of_reach_when_the_needed_t_beats_the_familys_best(fake_store):
    fake_store(family_best_t=4.1, family_tries_on_file=20)        # needed = 2 + 0.25 x 20 = 7.0
    assert MJ.reach(7, "orb")["reachable"] is False
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_judge.py -v`
Expected: the new tests FAIL (`AttributeError`)

- [ ] **Step 3: Implement them in `missionjudge.py`**

- `family_tries`: distinct `key` values in `ledger.csv` with `family == f`, `root == root` and `stage` in `wf_is`, `wf_oos`, `build`, `bp_build`, plus this machine's `wf_oos` read rows for that family (`api.ideastore().reads(root)`).
- `start_tries(f) = max(0, family_tries(f))` (one function, so the start rule is one line to change).
- A version's tries for `real.check` = `start_tries(family) + missions.tries(mid)`.
- `t_needed(n) = real.T_BAR + real.T_PER_TRY * (n - 1)`.
- `family_best_t`: the max `t_stat` over `hmwf.is_table(idea)` rows of every store under `hmwf.RUNS` whose meta family is `f`; None without one.
- `dead_families`: the first column of the markdown table at `$HOMEBASE_DEAD_FAMILIES`, default `~/Obsidian/Vault/30-Projects/Onyx-Trading/dead-families.md`; a missing file = empty set.
- `sides`: from the in-sample store's cell of the box, `x["net"]` split on `x["side"]`.
- `goal_in_sample`: `points` = the box's `points_over` from `hunt.score`; `net` = the box's net; `eval` = `eval_odds(..., on="is")["pass_p"]`; met = value ≥ target.
- `gate`: `real.check({**hmwf.show(name), "lock": {"box": <the row's id>}, "oos": None}, tries)` (check finds the box through the lock, and there is no lock before the read), its first five lines all `ok`, every charge held, the goal met.
- `reach`: needed = `t_needed(start_tries(f) + missions.tries(mid) + 1)`; reachable = best is None or needed ≤ best.

- [ ] **Step 4: Run them to make sure they pass**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_judge.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/edge-library/blueprint/missionjudge.py research/edge-library/tests/test_mission_judge.py
git commit -m "Missions Judge: charges, tries from the family's file, the gate, out of reach"
```

---

### Task 6: The Judge's door and the read

**Files:**
- Create: `research/edge-library/blueprint/missiondoor.py` (`python -m blueprint.missiondoor <command> ...`, JSON on stdout)
- Create: `research/edge-library/missions/judge` (bash, executable, like `hunt/bp`: `cd` to `research/edge-library`, run `../../.venv-research/bin/python -m blueprint.missiondoor "$@"`)
- Modify: `research/edge-library/blueprint/missionjudge.py` (`read`, `verdict_for_workers`)
- Test: `research/edge-library/tests/test_mission_door.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 4, 5; `hmwf.pick(name, box, who=)`, `hmwf.run_oos(name, box, owner_said, who=)`, `hmwf.show(name)`.
- Produces: the commands below; `read(mid, name, box, said=None) -> dict` (the workers' part); `verdict_for_workers(test: dict, k: int) -> {"held": bool, "line": str | None, "close": bool | None}`.

| Command | Prints |
|---|---|
| `accounts` | every open account with its facts and bans (Task 3) |
| `tries <mid> <family>` | `{family_on_file, mission, total, needed_t}` |
| `reach <mid> <family>` | Task 5's `reach` |
| `charges <mid> <name> <box>` | Task 5's `charges` (in-sample; workers may see it) |
| `gate <mid> <name> <box>` | Task 5's `gate` (in-sample; workers may see it) |
| `read <mid> <name> <box> [--said TEXT]` | ONLY `{"held", "line", "close"}`; the owner's numbers go to `<mission dir>/reads/<name>.json` |

The read, in order:
1. Refuse if `on_server()`, the brief is not approved, the name lacks the prefix, or the name or its spec hash is frozen.
2. `test_months == "ask"` needs `--said` (the owner's words, passed through verbatim as `owner_said`); `"team"` uses the brief's `owner_said`.
3. `gate` must be clear; else refuse with the failing line (no test month is touched).
4. `hmwf.pick(name, box, who=f"mission:{mid}")`, then `hmwf.run_oos(name, box, owner_said, who=f"mission:{mid}")`.
5. `missions.freeze(mid, name, hash)` and `missions.record(mid, "read", name)` straight after `run_oos` returns, before any number is worked out, so a crash later still leaves it frozen.
6. The owner's numbers: test trades, net, points over (the `hunt.over` arithmetic on the oos store's cell of the box), the goal's measure (`eval_odds(..., on="oos", mid=mid)` for an eval goal; a `Mismatch` is written as the reason instead of the number), the bar for this read.
7. The workers' verdict. Read k needs points over > k − 1. The lines, first that breaks wins: too few trades (< `real.MIN_TRADES_OOS` = 60); lost money (net ≤ $0); flipped direction (points over ≤ 0); under the bar; missed the goal. `close` is set only for "under the bar" and "flipped direction": True when the bar minus points over is under 1.

- [ ] **Step 1: Write the failing tests** (`hmwf.pick` / `run_oos` replaced by fakes that write a hand-made oos store with `blueprint_synth.store`)

```python
def test_read_prints_only_held_line_close(fake_read):
    fake_read(test_trades=80, test_net=900.0, points_over=1.4)
    out = door(["read", "7", "m7_v01", "12"])
    assert set(out) == {"held", "line", "close"} and out["held"] is True
    saved = json.loads((M.mission_dir(7) / "reads" / "m7_v01.json").read_text())
    assert saved["net"] == 900.0 and saved["who"] == "mission:7"

def test_the_bar_rises_one_point_a_read(fake_read):
    fake_read(points_over=1.4); door(["read", "7", "m7_v01", "12"])          # 1st read: > 0, held
    fake_read(points_over=0.6)
    out = door(["read", "7", "m7_v02", "12"])                                # 2nd read: needs > +1
    assert out == {"held": False, "line": "under the bar", "close": True}

def test_lines_in_order(fake_read):
    fake_read(test_trades=40, test_net=-50.0, points_over=-2.0)
    assert door(["read", "7", "m7_v01", "12"])["line"] == "too few trades"

def test_a_version_is_read_once_and_frozen_before_numbers(fake_read, explode_after_run_oos):
    with pytest.raises(Exception):
        door(["read", "7", "m7_v01", "12"])
    assert "m7_v01" in M.frozen(7)
    with pytest.raises(J.Refuse, match="frozen"):
        door(["read", "7", "m7_v01", "12"])

def test_ask_mode_needs_the_owners_words(fake_read):
    write_brief(7, approved=True, test_months="ask")
    with pytest.raises(J.Refuse, match="--said"):
        door(["read", "7", "m7_v01", "12"])

def test_a_version_that_fails_the_gate_never_touches_the_test_months(fake_read, gate_fails):
    with pytest.raises(J.Refuse):
        door(["read", "7", "m7_v01", "12"])
    assert fake_read.oos_calls == 0

def test_bash_door_refuses_unknown_commands():
    r = subprocess.run([JUDGE, "pipe"], capture_output=True, text=True)
    assert r.returncode == 2
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_door.py -v`
Expected: FAIL (`ModuleNotFoundError: blueprint.missiondoor`)

- [ ] **Step 3: Implement `read`, `verdict_for_workers`, `missiondoor.py` and the bash `judge`**

`missiondoor.main(argv)` parses with `argparse`, prints `json.dumps(result)`, and turns `J.Refuse` into
`{"refused": "<why>"}` with exit code 1. The bash door passes only the six commands above; any other word exits 2
(like `hunt/bp`'s fallthrough).

- [ ] **Step 4: Run them to make sure they pass**

Run: `../../.venv-research/bin/python -m pytest tests/test_mission_door.py tests/test_mission_judge.py tests/test_mission_accounts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/edge-library/blueprint/missiondoor.py research/edge-library/blueprint/missionjudge.py research/edge-library/missions/judge research/edge-library/tests/test_mission_door.py
git commit -m "Missions Judge: the door (accounts, tries, reach, charges, gate, read); a read is frozen first, workers hear held/line/close"
```

---

### Task 7: Docs, the dead list and the smoke test

**Files:**
- Modify: `CLAUDE.md` (one paragraph after "The hunt loop tests by itself, on the mini")
- Create (vault, not committed to the repo): `~/Obsidian/Vault/30-Projects/Onyx-Trading/dead-families.md`

- [ ] **Step 1: Add the CLAUDE.md paragraph**

Heading `## Missions (owner, 2026-11-14)`, at most 8 lines: Missions is its own app (`~/missions`); its workers reach Homebase
only through the connector's mission mode (`python -m homebase.claude_mcp --mission <id>`); only the Missions Judge
(`research/edge-library/missions/judge`) may read a mission version's test months, once, marked `who: mission:<id>`, and only
for Missions; every other agent's rules are unchanged; names `m<id>_*` belong to missions; the Judge never runs on the server.

- [ ] **Step 2: Write the dead list** (frontmatter `name: dead-families`, `type: reference`; one line on what it is; the
empty table `| family | verdict | date | why |`; a link to `[[what-lives-what-is-dead-2026-11-07]]`). Rows come only from the
owner or from a mission's report he accepts.

- [ ] **Step 3: Smoke test, no engine**

Write an approved brief for mission 999 into a temp `HOMEBASE_MISSIONS`, then:

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"blueprint_wf_oos","arguments":{"name":"m999_x","box":"1","owner_said":"x"}}}' | HOMEBASE_MISSIONS=/tmp/mtest .venv/bin/python -m homebase.claude_mcp --mission 999
```

Expected: the tool list holds exactly `ALLOW`; call 3 comes back as an error ("unknown tool" / not allowed); `/tmp/mtest/999/refused.jsonl` has one line.
Then `research/edge-library/missions/judge accounts` prints the open accounts (no engine runs for `accounts`).

- [ ] **Step 4: Run every test this plan added, plus the old connector and prop sim tests**

Run: `.venv/bin/python -m pytest tests/test_missions_state.py tests/test_claude_mcp_mission.py tests/test_claude_mcp.py tests/test_backtest_propsim.py -v`
and `../../.venv-research/bin/python -m pytest tests/test_mission_accounts.py tests/test_mission_judge.py tests/test_mission_door.py tests/test_blueprint_hunt.py tests/test_real.py -v`
Expected: all PASS

- [ ] **Step 5: Commit, and stop**

```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: Missions paragraph (mission mode, the Judge's door, m<id>_ names)"
```

The branch stays unmerged. Merging it to `main` (which ships to the VPS) waits for the owner's word.

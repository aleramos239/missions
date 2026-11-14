# Plan 2: the Missions app

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Missions app itself: the owner types a goal, a team of Claude workers runs fixed rounds against the
Homebase fence and Judge (Plan 1, on Homebase main b39f9b6f), and he watches and texts the team from one local page.

**Architecture:** A FastAPI app in `~/missions` on `127.0.0.1:8860`. The round order is Python code (`engine.py`), a state
machine saved to disk after every step. Each worker is one `claude -p` process per turn with **no built-in tools**: its only
tools are the Homebase mission-mode connector. The engine, never a worker, calls the Judge's door, waits on jobs, counts
limits and starts the one test-month read. The page is vanilla JS over the copied Homebase styles, fed by one
server-sent-event stream per mission. Three small owner-side commands are added to the Judge's door in Homebase (Task 1).

**Tech Stack:** Python 3.12, FastAPI, uvicorn, pytest, httpx (tests). Vanilla JS, no build step, `node --test` for the
formatters. The `claude` CLI 2.1.321 (the desktop engine's binary). No database: JSON and JSONL files.

**Spec:** `~/missions/docs/specs/2026-11-14-missions-design.md` (approved 2026-11-14), sections 5, 6, 8, 9, 10, 12.
The shelf (section 7) is Plan 3.

**How this plan is run (owner, 2026-11-14):** the planner (Fable 5.2) wrote this from a read of the real files; Opus 5.5
subagents build it task by task. Where the plan's code disagrees with the real code (a signature, a field, a flag), **the
real code wins**: fit the plan's code to it, keep the behaviour the tests pin, and say what you changed in your report.
Never weaken a test to make it pass.

## Facts this plan stands on (checked 2026-11-14)

- **The CLI.** `--restricted`, `--strict-mcp-config`, `--tools`, `--permission-mode dontAsk`, `--mcp-config` (file or JSON
  string), `--model fable|opus|sonnet|haiku`, `--effort low|medium|high|xhigh|max`, `--output-format stream-json`
  (`--verbose` with it), `--resume <session id>`, `--allowedTools`, `--disallowedTools` all exist in 2.1.321. A real run
  with `--restricted --strict-mcp-config --tools "Read"` listed `tools: ["Read"]`, `mcp_servers: []`, and saw no CLAUDE.md
  or memory. `--bare` needs an API key: never use it. Pass `</dev/null` as stdin. `--max-turns` is accepted but not in
  `--help`: do not rely on it. Not run: `--tools ""` with one MCP server (Task 4 proves it).
- **The stream.** One JSON object a line. `system`/`init` (`session_id`, `tools`, `mcp_servers`, `model`), `assistant`
  (`message.content` = blocks: `thinking`, `text`, `tool_use`), `user` (tool results), `rate_limit_event`
  (`rate_limit_info`: `status` allowed|allowed_warning|rejected, `resetsAt` epoch s, `unifiedWindows.{five_hour,seven_day}`
  `.utilization` 0-1), `result` (`subtype`, `is_error`, `result`, `total_cost_usd`, `num_turns`, `duration_ms`,
  `api_error_status`, `session_id`). What a plan-limit stop looks like was not seen: treat `rate_limit_info.status ==
  "rejected"`, or a `result` with `is_error` and `api_error_status == 429`, as "plan used up".
- **Binaries.** `/opt/homebrew/bin/claude` is 2.1.285 (old). The 2.1.321 binary is
  `~/Library/Application Support/Claude/claude-code/<version>/<hash>/claude.app/Contents/MacOS/claude`.
- **The fence (Homebase main).** `python -m homebase.claude_mcp --mission <id>`: 9 tools (`list_strategies`,
  `list_prop_rules`, `blueprint_blocks`, `blueprint_card`, `blueprint_code_check`, `blueprint_wf`, `blueprint_status`,
  `blueprint_heatmap`, `blueprint_mc`), NQ only, hm40 only, names `m<id>_*`, refusals logged. It needs the chart service
  on `127.0.0.1:8852`. It exits 2 when the brief is missing or not approved.
- **The brief file** `~/.homebase/missions/<id>/brief.json` is written by this app, read by Homebase on every call:
  `{"approved": true, "owner_said": "<his words>", "test_months": "team"|"ask", "goal": {"kind": "eval"|"points"|"net",
  "target": <number>, "rule": "<account id>" (eval only; target a fraction in (0, 1])}}`.
- **The Judge's door** `<homebase>/research/edge-library/missions/judge <cmd> ...` prints JSON; a refusal prints
  `{"refused": why}` and exits 1. `accounts` | `tries <mid> <family>` → `{family, family_on_file, mission, total,
  needed_t}` | `reach <mid> <family>` → `{family, tries, needed_t, best_t, reachable}` | `charges <mid> <name> <box>` |
  `gate <mid> <name> <box>` → `{name, box, clear, lines[5]{line, ok, said}, charges[5]{charge, held, why}, goal{kind,
  target, value, met}, tries}` | `read <mid> <name> <box> [--said TEXT]` → only `{held, line, close}`. `read` runs the
  engine on the test months and has no timeout. The owner's numbers land in
  `~/.homebase/missions/<id>/reads/<name>.json`; `refused.jsonl` and `read.log` sit beside it.
- **The box the read takes** is the one `hunt.score(name)["pick"]["box"]` names; `read` refuses any other.
- **Homebase patterns.** launchd plists are filled from templates by an install script (`deploy/install.sh`). The only
  alerts Homebase has are `osascript -e 'display notification ...'`. Slots: `homebase/backtest/slots.py` `status()`.
  The hunt is paused by `PAUSE: yes` in the vault note `30-Projects/Onyx-Trading/Hunt/hunt-steering.md`.

## Rulings made in this plan (the owner can overrule; each is one place to change)

1. **Workers get no built-in tool at all** (`--tools ""`): not Read, Glob, Grep, Write or Edit. The design listed those
   with a trimmed code copy; Plan 1 found the repo holds test-month stores, and with drafts off a worker has nothing to
   write. The Doubter checks look-ahead with `blueprint_code_check`. Cost if wrong: a worker cannot read block source
   until the shelf adds `toolkit_code` (Plan 3).
2. **Only the engine talks to the Judge.** No worker has Bash, so no worker can run the door. The engine posts the
   Judge's in-sample answers into the chat. Cost: none known.
3. **`"drafts": true` is refused** by Homebase for every mission (Task 1). The app has no switch for it. Whole
   strategies come with the shelf. Cost: v1 teams build from blocks only.
4. **Box numbers.** A box is shown as `<main-setting value> · #<cell>`, where `#<cell>` is the box's place in the hm40
   grid (the order of `blocks.menu_hm40`, 1-40, or 1-20 for a family with no stop of its own). The door's new `table`
   command gives both; the app never numbers a box itself.
5. **Alerts.** A macOS notification always. A phone alert through ntfy.sh only after he types a topic on the Connections
   page (off by default): it sends words to an outside service, so the text never carries a number, a strategy name or
   his goal, only "Mission 7: goal reached". Cost: no phone alert until he sets it.
6. **Mic.** The browser's speech recognition (`webkitSpeechRecognition`), as in the mockup. Chrome sends the audio to
   Google. Local Whisper is not built.
7. **Claude usage.** Read from the `rate_limit_event` of every worker turn. The usage limit is "the 7-day window moved
   this many points since the mission started" (other chats on his login count too, and the page says so). The reserve:
   no worker turn starts while any window is at 90 % or more.
8. **Out of reach.** Before a round is built, an idea whose family `reach` says is not reachable is dropped. Two rounds
   in a row with no idea left stop the mission as "out of reach", even with "Run until the goal" on.
9. **One read a round**, for the cleared version with the best in-sample goal value.
10. **The tries rule is unchanged** (a mission starts from the family's tries on file). The owner's open question on it
    is one line in Homebase (`start_tries`), not in this app.
11. **App state lives in `~/.missions/`** (not in the repo, not in `~/.homebase`). Worker folders are
    `~/.missions/_work/<id>/<role>/`, empty, outside every repo.

## Global Constraints

- **Two repos.** App code: `~/missions`, branch `feat/app` (its own git history; nothing deploys from it). Homebase code
  (Task 1 only): worktree `~/ramos-quant-homebase/.worktrees/missions-door`, branch `feat/missions-door`, off `main`.
  Never edit, commit or switch branch in the main checkout `~/ramos-quant-homebase`. A commit on Homebase `main` ships to
  the trading server by itself: `feat/missions-door` is merged only on the owner's word. Never push either repo.
- The shell hook blocks any command with a recursive force-delete. Use `tmp_path` and `tempfile`.
- **While building, never start a real mission, a real heat map, a real in-sample table or a test-month read**, and never
  call the real Judge's door on a real mission. Tests use fakes: `tests/fakes/judge` (a script), `tests/fakes/claude` (a
  script that prints a canned stream) and `FakeHB`. The single real `claude` call is Task 4 (haiku, one turn).
- Homebase tests (Task 1): app `~/ramos-quant-homebase/.venv/bin/python -m pytest tests/<file>` with the cwd at the
  worktree root; research `~/ramos-quant-homebase/.venv-research/bin/python -m pytest tests/<file> -W error` with the
  cwd at `<worktree>/research/edge-library`.
- App tests: `~/missions/.venv/bin/python -m pytest -q` with the cwd at `~/missions`. Every test sets `MISSIONS_HOME`
  and `HOMEBASE_MISSIONS` to temp folders: no test touches `~/.missions` or `~/.homebase`.
- **Blind for real.** No text built for a worker (a prompt, a chat line shown to workers, a scoreboard) may be built from
  `reads/<name>.json`, `refused.jsonl`, `read.log`, `runs_wf/*/oos`, RECENT.md or a memory index. Worker text comes only
  from: the brief, the vault digest, the connector's own answers, and the door's `tries`, `reach`, `gate`, `table`
  (in-sample) and the one-line answer of `read`.
- The app never places, cancels or manages an order, never touches an account or the Desk, never commits to Homebase,
  and never runs anything on the trading server.
- NQ only. The pipeline stays off. Never write `payout_enabled`.
- Words on screen: plain and minimal. RR and points, full-target % against the % needed, dollars, trades a week, per
  year then combined. No "t-stat", "cell", "R" decimals on screen: the luck bar reads "needs 3.5 after 7 tries; has 3.1".
- The look is the Homebase look, copied, not redesigned. Green and red mean money only. Every number keeps its + or −.
- Sharpe is never worked out in this app: it shows the number Homebase gives.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, name explicit paths (no `git add -A`).

## Review Focus

1. A test-month number planted in a fake `reads/m7_v03.json` must never appear in any worker prompt, any chat event
   marked for workers, or the scoreboard (Task 7 pins it with a sentinel).
2. The app is killed mid-round (during a worker turn, during a job wait, during a read): on restart the mission resumes
   at the saved step, makes no second copy of a version, and never starts a second read of the same version.
3. A worker's reply has no JSON block, or broken JSON, or names a version the mission's ledger does not hold: one retry,
   then the step goes on without it and says so in the chat; nothing a worker claims is trusted without the ledger.
4. The plan runs out mid-turn: the mission waits for the reset and goes on by itself; it never asks him and never stops.
5. A page from another site, or a request with a foreign `Host`, tries to POST to the app: refused (403).

---

## File map

| File | Responsibility |
|---|---|
| Homebase `research/edge-library/blueprint/missiondoor.py`, `missionjudge.py` | Task 1: `table`, `odds`, `mc` |
| Homebase `homebase/missions.py` | Task 1: `drafts: true` refused |
| `missions/config.py` | Paths, the port, where Homebase and the `claude` binary are |
| `missions/store.py` | Mission folders: ids, `mission.json`, `events.jsonl` |
| `missions/hb.py` | Every call into Homebase: the door, the brief file, jobs, slots, the owner's files |
| `missions/worker.py` | One worker turn: the command, the stream, the caps |
| `missions/blindcheck.py` | The test worker that proves what a worker can see |
| `missions/roles.py`, `missions/prompts/*.md` | The four roles, their prompts, the reply contract |
| `missions/digest.py` | The Lead's vault digest (verdict words, no numbers) |
| `missions/briefing.py` | The brief: questions, the page, his yes |
| `missions/engine.py` | The round order, limits, the read, resume |
| `missions/system.py` | Usage, the reserve, keep-awake, alerts, the hunt pause |
| `missions/wrapup.py` | The vault note, RECENT.md, the strategy map line |
| `missions/api.py`, `missions/__main__.py` | Routes, the event stream, the host guard |
| `missions/static/` | `index.html`, `hb/*.css` (copied), `missions.css`, `js/*.js` |
| `tools/sync_css.py` | Copies the Homebase styles and records the commit |
| `deploy/` | The launchd plist template and `install.sh` |

---

### Task 1 (Homebase): the door's owner-side commands

**Files (worktree `missions-door`):**
- Modify: `research/edge-library/blueprint/missiondoor.py`, `research/edge-library/blueprint/missionjudge.py`,
  `research/edge-library/missions/judge` (the allowed-command list), `homebase/missions.py`
- Test: `research/edge-library/tests/test_mission_door.py`, `tests/test_missions_state.py`

**Interfaces — Produces** (all in-sample; none opens a test month):
- `judge table <mid> <name>` → `{"name", "family", "root", "tf", "values": [<main-setting values, in order>],
  "cells": <20|40>, "frozen": bool, "pick": <box id or null>, "why_no_pick": <text or null>, "verdict": "weak|maybe|strong",
  "rows": [{"box", "value", "cell": 1..40, "stop": "<plain words, e.g. ATR x 1>", "target_r", "stop_pts", "net",
  "trades", "per_week", "win_rate", "breakeven", "points_over", "usd_trade", "pf", "sharpe", "t_stat", "long_net",
  "short_net", "worse_fills_net", "neighbours_green", "years": [[year, trades, points_over, net]]}]}`.
  The name must carry this mission's prefix; a frozen name is allowed (it is the owner's view, in-sample).
- `judge odds <mid> <name> <box> [--rule ID]` → a list of `eval_odds` dicts, one per open account (or the one named),
  best pass first. One engine re-run of the box (worse fills) serves every account. Saved to
  `~/.homebase/missions/<id>/odds/<name>__<box id>.json` and reused while the version's `spec_id` is the same.
- `judge mc <mid> <name> <box>` → `{"paths", "worst_drawdown": {"typical", "one_in_20"}, "losing_streak": {"typical",
  "one_in_20"}, "net_one_in_20", "below_zero_pct"}` from `homebase/backtest/stats/montecarlo.run(trades, mode="bootstrap",
  paths=2000, seed=seed_for("<name>:<box id>"))` on the box's in-sample `{date, net}` trades.
- `homebase.missions.brief(mid)` raises `MissionError("mission N: drafts are off for missions (a draft can read the test
  months)")` when `drafts` is true.

- [ ] **Step 1: Read first.** `missionjudge.py` (`_box`, `_version`, `eval_odds`, `box_trades`, `spec_id`),
  `blueprint/hunt.py` (`score`, the row fields), `blueprint/hmwf.py` (`is_table`), `engine/families/blocks.py`
  (`menu_hm40`), `homebase/backtest/stats/montecarlo.py` (`run`, `seed_for`). Note how `charges`/`gate` check the name.

- [ ] **Step 2: Write the failing tests** in `test_mission_door.py`, with the file's existing fakes (`FAKERUN`, a fake
  `HU.score`, a fake `_box`):

```python
def test_table_numbers_each_box_by_its_place_in_the_hm40_grid(door, fake_store):
    out = door("table", "7", "m7_v01")
    row = next(r for r in out["rows"] if r["box"] == fake_store.box_at(value=20, stop="atr", stop_val=1.0, tgt_r=1.5))
    assert (row["value"], row["cell"]) == (20, 9)          # row 2 (ATR x 1), column 4 (1:1.5) = (2-1)*5 + 4
    assert out["cells"] == 40 and out["values"] == [10, 20, 30]

def test_table_of_a_family_with_no_own_stop_has_20_cells(door, fake_store_no_own): ...
def test_table_refuses_another_missions_name_before_loading_a_store(door, box_must_not_load): ...
def test_table_shows_a_frozen_version(door, frozen): assert door("table", "7", "m7_v01")["frozen"] is True
def test_table_carries_no_test_month_field(door, fake_store_with_oos):
    assert "oos" not in json.dumps(door("table", "7", "m7_v01"))
def test_odds_runs_the_engine_once_for_all_accounts(door, count_box_trades):
    out = door("odds", "7", "m7_v01", "12"); assert count_box_trades.n == 1 and len(out) == 18
    assert [o["pass_p"] for o in out] == sorted((o["pass_p"] for o in out), reverse=True)
def test_odds_is_reused_until_the_settings_change(door, count_box_trades): ...
def test_odds_refuses_on_the_server(door, on_server): ...
def test_mc_uses_bootstrap(door, spy_mc): door("mc", "7", "m7_v01", "12"); assert spy_mc.kw["mode"] == "bootstrap"
def test_mc_below_zero_is_a_percent_of_paths(door, fixed_trades): ...
```

  and in `tests/test_missions_state.py`:

```python
def test_a_brief_with_drafts_true_is_refused(tmp_missions):
    write_brief(7, drafts=True)
    with pytest.raises(M.MissionError, match="drafts are off"): M.brief(7)
```

- [ ] **Step 3: Run them; they fail** (unknown command / no refusal).
- [ ] **Step 4: Implement.** `MJ.table(mid, name)`, `MJ.odds(mid, name, box, rule=None)`, `MJ.mc(mid, name, box)`;
  three sub-parsers in `missiondoor.parser()` and three branches in `run()`; add `table|odds|mc` to the bash door's
  list. `cell` = 1 + the index of the row's exit in `blocks.menu_hm40(...)` for that family. If `montecarlo.run` does not
  return the share of paths that end below $0, work it out from what it returns (its histogram or final-net percentiles)
  and say how in the report: do not edit `montecarlo.py`. The existing draft tests in `tests/test_claude_mcp_mission.py`
  that use `drafts=True` now meet a refused brief: change them to assert the refusal, keep the `DRAFT_TOOLS` code.
- [ ] **Step 5: Run** the research tests (`test_mission_judge.py test_mission_door.py test_mission_accounts.py -W error`)
  and the app tests (`test_missions_state.py test_claude_mcp_mission.py test_claude_mcp.py`). All pass.
- [ ] **Step 6: Commit** (explicit paths): `Missions Judge: table, odds and mc for the owner's pages; drafts refused`.

---

### Task 2: the app's skeleton, config and store

**Files:** Create `pyproject.toml`, `requirements.txt` (`fastapi`, `uvicorn`, `httpx`, `pytest`), `missions/__init__.py`,
`missions/config.py`, `missions/store.py`, `tests/conftest.py`, `tests/test_store.py`, `.gitignore` (`.venv/`,
`__pycache__/`, `.pytest_cache/`). Build `.venv` with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

**Interfaces — Produces:**

```python
# config.py
PORT = 8860
def home() -> Path                 # $MISSIONS_HOME or ~/.missions
def work_dir(mid, role) -> Path    # home()/"_work"/str(mid)/role  (made empty; never inside a repo)
def homebase() -> Path             # $MISSIONS_HOMEBASE or ~/ramos-quant-homebase
def hb_missions() -> Path          # $HOMEBASE_MISSIONS or ~/.homebase/missions
def vault() -> Path                # $MISSIONS_VAULT or ~/Obsidian/Vault
def claude_bin() -> Path           # settings["claude"] if set; else the newest .../claude-code/<ver>/<hash>/claude.app/
                                   # Contents/MacOS/claude by version; else shutil.which("claude"); else ConfigError
def settings() -> dict; def save_settings(d) -> None      # home()/"settings.json": {"claude", "ntfy_topic"}

# store.py
ROLES = ("lead", "builder", "doubter", "defender")
STATUS = ("briefing", "ready", "queued", "running", "paused", "waiting_plan", "waiting_owner",
          "achieved", "limit", "out_of_reach", "stopped", "crashed")
DONE = ("achieved", "limit", "out_of_reach", "stopped")
def new_mission(sentence: str, team: dict, limits: dict, test_months: str) -> dict
def load(mid) -> dict; def save(m: dict) -> None           # atomic: temp file + os.replace
def missions() -> list[dict]                               # newest first
def event(mid, type, who, text="", data=None, to=None, for_workers=True) -> dict   # appends {n, at, type, who, to, text, data, for_workers}
def events(mid, after=0) -> list[dict]
```

`new_mission` picks the id as 1 + the largest id found in **both** `home()` and `hb_missions()` (an id is never reused,
because Homebase keys the ledger and the names on it). The mission dict:

```python
{"id": 7, "title": <first 40 chars of the sentence>, "sentence": ..., "created": <utc iso>, "status": "briefing",
 "team": {"lead": {"model": "opus", "effort": "high"}, "builder": {"model": "fable", "effort": "high"},
          "doubter": {"model": "sonnet", "effort": "high"}, "defender": {"model": "opus", "effort": "high"}},
 "limits": {"until_goal": False, "tries": {"on": True, "n": 40}, "hours": {"on": True, "n": 8},
            "usage": {"on": True, "pct": 40}},
 "test_months": "team", "brief": None, "round": 0, "step": None, "sessions": {}, "versions": [], "pending": {},
 "empty_rounds": 0, "run_seconds": 0, "usage_start": None, "cost_usd": 0.0, "reads": 0, "result": None}
```

- [ ] **Step 1: Tests** (`tests/test_store.py`): the id skips ids used on either side; `save` then `load` round-trips;
  a torn last line in `events.jsonl` is skipped; `events(after=n)` returns only later rows; event numbers rise by 1 even
  from two threads (lock the file with `fcntl`); `claude_bin()` picks `2.1.321` over `2.1.285` from a fake folder tree
  and prefers the setting when it is set; a model outside `fable|opus|sonnet|haiku` or an effort outside
  `low|medium|high|xhigh|max` is refused by `new_mission` (`ValueError`).
- [ ] **Step 2: Run; fail. Step 3: Implement. Step 4: Run; pass. Step 5: Commit** `App skeleton: config and the mission store`.

---

### Task 3: the Homebase adapter

**Files:** Create `missions/hb.py`, `tests/fakes/judge` (executable Python script: answers from `$FAKE_JUDGE` JSON file,
keyed by the joined argv; unknown key → `{"refused": "no such fake"}`, exit 1), `tests/fakes/hb.py` (`FakeHB`, the
in-memory twin used by the engine tests), `tests/test_hb.py`.

**Interfaces — Produces** (the only module that knows Homebase's paths):

```python
class Refused(Exception): ...            # the door said no; str(e) is its words
class Down(Exception): ...               # Homebase is not there (no door, no chart service)

def door(*args, timeout=600) -> dict | list      # runs <homebase>/research/edge-library/missions/judge; Refused on exit 1
def accounts() -> list[dict]
def tries(mid, family) -> dict;  def reach(mid, family) -> dict
def gate(mid, name, box) -> dict                 # timeout 1800 (an eval goal re-runs the box)
def table(mid, name) -> dict;  def odds(mid, name, box) -> list[dict];  def mc(mid, name, box) -> dict

def write_brief(mid, brief: dict) -> None        # hb_missions()/<id>/brief.json, atomic; refuses a brief with "drafts"
def unapprove(mid) -> None                       # sets approved false: the connector lists nothing from then on
def ledger(mid) -> list[dict]                    # read-only parse of ledger.jsonl
def made(mid, name) -> dict | None               # {"wf": bool, "job_id": str|None} from the ledger rows of that name
def family_of(name) -> str | None                # from ~/.homebase/ideas/<name>/spec.json (or idea.json): the card's family
def job(job_id) -> dict                          # {"done": bool, "ok": bool, "said": str, "progress": [k, n] | None}
def slots() -> dict                              # {"cap", "running"} or {"off": True}
def health() -> dict                             # {"chart_service": bool, "door": bool, "claude": "<version>"|None}

# owner-only: NEVER used to build worker text (the engine never imports these three)
def owner_read(mid, name) -> dict | None         # reads/<name>.json
def owner_refused(mid) -> list[dict]             # refused.jsonl, newest first
def start_read(mid, name, box, said=None) -> int # see below; returns the pid
def read_result(mid, name) -> dict | None        # {"held","line","close"} | {"refused": text} | None while it runs
```

`start_read` starts the door detached, so neither a worker's time limit nor an app restart can kill it:

```python
out = store_dir(mid) / f"read_{name}.json"
cmd = f'{shlex.quote(str(JUDGE))} read {mid} {shlex.quote(name)} {shlex.quote(box)}' + (f' --said {shlex.quote(said)}' if said else '')
subprocess.Popen(["/bin/sh", "-c", f'{cmd} > {shlex.quote(str(out))}.tmp 2>/dev/null; mv {shlex.quote(str(out))}.tmp {shlex.quote(str(out))}'],
                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
```

and writes the pid to `read_<name>.pid`. `read_result` returns the parsed file when it exists; if it does not and the pid
is gone, it returns `{"refused": "the read stopped; the owner has the details"}` (the version is spent: Homebase counts a
frozen name as a read).

- [ ] **Step 1: Read first** how a job's state is asked for: `research/edge-library/blueprint/cli.py` (`job`, `status`),
  `homebase/claude_mcp/blueprint_tools.py` (`t_blueprint_status`), and where an idea's card and spec are saved
  (`homebase/store/ideastore.py`). Fit `job()` and `family_of()` to them; `job()` runs
  `<homebase>/.venv-research/bin/python bp.py job <id> --json` (cwd `research/edge-library`) unless the real code has a
  cheaper read.
- [ ] **Step 2: Tests** (`tests/test_hb.py`, all against `tests/fakes/judge` via `MISSIONS_JUDGE`): `door` returns the
  JSON; exit 1 raises `Refused` with the door's words; a missing door raises `Down`; `write_brief` writes exactly the
  keys Homebase validates and refuses `drafts`; `made` finds a `wf` row and its `job` row; `start_read` then
  `read_result` gives the fake's answer; `read_result` with a dead pid and no file gives the fixed "stopped" refusal;
  `start_read` twice for one name does not start a second process while the first runs.
- [ ] **Step 3: `FakeHB`** (`tests/fakes/hb.py`): the same function names over dicts a test fills (`fake.tables[name]`,
  `fake.gates[(name, box)]`, `fake.reads[name]`, `fake.jobs[id]`, `fake.reach[family]`), plus `fake.calls` (a list of
  every call) and `fake.owner_files` (so a test can plant a sentinel). `engine` takes the module as a parameter
  (`Engine(mid, hb=hb, run_turn=worker.run_turn)`), so tests pass `FakeHB`.
- [ ] **Step 4: Run; pass. Step 5: Commit** `Homebase adapter: the door, the brief file, jobs, the detached read`.

---

### Task 4: one worker turn, and the proof of what a worker sees

**Files:** Create `missions/worker.py`, `missions/blindcheck.py`, `tests/fakes/claude` (executable: prints the stream in
`$FAKE_CLAUDE_STREAM`, one line every `$FAKE_CLAUDE_DELAY` seconds, records its argv to `$FAKE_CLAUDE_ARGV`),
`tests/test_worker.py`.

**Interfaces — Produces:**

```python
@dataclass
class Turn:
    text: str                 # every assistant text block, joined
    session_id: str | None
    ok: bool                  # a result came and is_error is false
    why: str | None           # "plan" (plan used up) | "timeout" | "too many tool calls" | "crash: ..." | None
    cost_usd: float
    tool_calls: list[dict]    # [{"name", "input"}]
    rate: dict | None         # the last rate_limit_info seen
    resets_at: int | None

def command(mid: int, role: str, model: str, effort: str, session_id: str | None) -> list[str]
async def run_turn(mid, role, prompt, *, model, effort, session_id=None, max_tool_calls=40, timeout_s=1200,
                   on_event=None) -> Turn
```

The command, exactly (the prompt is the last argument; stdin is `/dev/null`):

```python
def command(mid, role, model, effort, session_id):
    hbr = config.homebase()
    mcp = {"mcpServers": {"homebase": {"command": str(hbr / ".venv/bin/python"),
                                       "args": ["-m", "homebase.claude_mcp", "--mission", str(mid)],
                                       "env": {"PYTHONPATH": str(hbr), "HOMEBASE_MISSIONS": str(config.hb_missions())}}}}
    cmd = [str(config.claude_bin()), "-p", "--restricted", "--strict-mcp-config", "--mcp-config", json.dumps(mcp),
           "--tools", "", "--allowedTools", "mcp__homebase", "--permission-mode", "dontAsk",
           "--model", model, "--effort", effort, "--output-format", "stream-json", "--verbose"]
    return cmd + (["--resume", session_id] if session_id else [])
```

`run_turn` appends the prompt as the last argument, runs it with `cwd=config.work_dir(mid, role)`, `stdin=DEVNULL`, and
reads stdout line by line. It kills the process (and reports `why`) when: `timeout_s` passes; the count of `tool_use`
blocks goes over `max_tool_calls`; a `tool_use` names a tool that does not start with `mcp__homebase__` (this cannot
happen if the flags hold: it is the alarm that they did not). `why == "plan"` when a `rate_limit_event` says `rejected`
or the result has `is_error` and `api_error_status == 429`. `on_event(kind, data)` is called for `text`, `tool`
(name + input), and `rate`.

- [ ] **Step 1: Tests** (`tests/test_worker.py`, `MISSIONS_CLAUDE` → the fake): the command carries `--restricted`,
  `--strict-mcp-config`, `--tools ""`, `--permission-mode dontAsk`, the mission id inside the MCP JSON, and never
  `--bare`, `bypassPermissions` or `--add-dir`; a canned stream gives `text`, `session_id`, `cost_usd`, `tool_calls`;
  `--resume` appears only with a session id; a stream of 41 tool calls is killed with `why == "too many tool calls"`; a
  slow stream is killed with `why == "timeout"`; a `rejected` rate event gives `why == "plan"` and `resets_at`; a
  `tool_use` named `Bash` kills the turn with `why` starting `"crash: a tool outside the fence"`; a non-JSON line on
  stdout is skipped, not a crash; the cwd of the fake is `work_dir(mid, role)` and it is empty.
- [ ] **Step 2: Run; fail. Step 3: Implement. Step 4: Run; pass.**
- [ ] **Step 5: `blindcheck.py`** (`python -m missions.blindcheck`): the one real run. It makes a throwaway mission id
  with an approved brief in a **temp** `HOMEBASE_MISSIONS` (goal `{"kind": "points", "target": 1.0}`), then runs one
  haiku turn with the prompt "List the exact names of every tool you have. Then try to read the file /etc/hosts and say
  what happened. Then say whether you see any CLAUDE.md, memory or RECENT instructions: yes or no." It prints and
  asserts: `init.tools == []`; `init.mcp_servers` names only `homebase` and it is connected; every tool name the model
  lists starts with `mcp__homebase__` and there are 9; no `tool_use` happened outside `mcp__homebase__`; the reply says
  no CLAUDE.md, memory or RECENT. It needs the Homebase chart service running (it says so and exits 3 if it is not).
- [ ] **Step 6: Run `python -m missions.blindcheck` once** and paste its whole output into the report. If `--tools ""`
  with an MCP server does not give an empty built-in list, or the connector does not connect under `--restricted`, STOP
  and report BLOCKED with the output: the planner rules on it. Do not loosen a flag to make it pass.
- [ ] **Step 7: Commit** `Worker turns: the fenced claude command, the stream, the caps, the blind check`.

---

### Task 5: roles, prompts, the reply contract and the vault digest

**Files:** Create `missions/roles.py`, `missions/digest.py`, `missions/prompts/{common,lead,builder,doubter,defender}.md`,
`tests/test_roles.py`, `tests/test_digest.py`.

**Interfaces — Produces:**

```python
# roles.py
CHARGES = ("One year carries it", "Worse fills kill it", "It looks ahead", "One side carries it", "It is a dead family again")
def prompt(role, step, *, brief, board, chat, ask, digest=None) -> str      # common.md + <role>.md + the step's block
def reply(text: str) -> dict | None          # the LAST ```json fenced block of the text, parsed; None if absent or broken
def say(text: str) -> str                    # the text with its json block cut out (what the chat shows)
def version_name(mid, n) -> str              # "m7_v08"
# digest.py
VERDICTS = ("dead", "alive", "held", "failed", "parked", "weak", "strong")
def digest() -> str
```

**The reply contract** (the last fenced `json` block of a worker's message; everything before it is free talk the chat shows):

| Step | Who | JSON |
|---|---|---|
| brief | lead | `{"ask": {"q": "...", "options": ["...", "..."]}}` or `{"brief": {...}}` (Task 6) |
| ideas | builder, doubter, defender | `{"ideas": [{"idea": "...", "family": "<a family blueprint_blocks lists>", "why": "..."}]}` (at most 3) |
| ideas | lead (after the others) | `{"plan": [{"version": "v08", "idea": "...", "family": "...", "why": "..."}]}` (at most 3 a round) |
| build | builder | `{"built": [{"version": "v08", "name": "m7_v08", "job_id": "..."}], "failed": [{"version": "v09", "why": "..."}]}` |
| argue | doubter | `{"claims": [{"version": "v08", "charge": "<one of CHARGES>", "say": "..."}]}` |
| argue | defender | `{"answers": [{"version": "v08", "charge": "...", "say": "..."}], "fixes": [{"idea": "...", "family": "...", "why": "..."}]}` |
| verdict | lead | `{"to_owner": "<two plain sentences>", "next": "<what the next round tries>"}` |
| owner text | any | `{"reply": "..."}` (the Lead may add `"plan_change": "..."`) |

**The prompts** (write them; these lines are fixed and must appear):
- `common.md`: who the team is and each role's "cannot" (design section 5.2); the house rules (NQ only, hm40, the
  average box not the best, fewer rules, 2-3 trades a week or more, stop or full target, an edge must make sense); "You
  have only the Homebase tools. You cannot read files. The Judge is code: it runs every check itself and cannot be
  overruled. You will never be shown a test-month number. Do not ask for one and do not guess one."; "Every table you
  start is a try and raises the luck bar."; the reply contract for the step; "Plain, short words. No jargon."
- `builder.md`: the tool order (`blueprint_blocks`, `blueprint_card` with exits hm40, `blueprint_code_check`,
  `blueprint_wf` once per version with `wait_s` 20); "Start each table, then stop: do not wait for it. The app waits and
  wakes you."; names are exactly the ones in the plan (`m<id>_vNN`).
- `doubter.md`: argue it is luck or broken, only with the five charges, each backed by a run (`blueprint_status`,
  `blueprint_heatmap`, `blueprint_code_check`); "A claim outside the five charges is thrown out. You cannot kill a
  version with words: the Judge's check decides."
- `defender.md`: why the edge exists and who is on the other side; the next fix; "Never add a rule without a reason."
- `lead.md`: owns the goal and the plan; reads the digest; merges ideas; talks to the owner; "You do not build and you do
  not grade."

`digest()`: from `vault()/30-Projects/Onyx-Trading/what-lives-what-is-dead-2026-11-07.md` and `dead-families.md`. Keep,
per table row or list line, only the strategy or family name and the first word of `VERDICTS` found on that line; drop
every other token. Lines with no verdict word are dropped. Plus a fixed block of the owner's standing rules (hard-coded
text, no numbers from results). A missing file gives a digest that says so, not an error.

- [ ] **Step 1: Tests.** `reply`: takes the last block of two; `None` for no block and for broken JSON; ignores a
  ```` ```json ```` inside a quoted tool result earlier in the text. `say` cuts only that block. `prompt`: for every
  (role, step) pair the text contains the fixed blind line and the step's contract; no `{placeholder}` is left unfilled.
  `digest`: from a fake note with the row `| nq_fvg15_va10 | alive | test months +4.1 pts, $31,400 net |` it keeps
  `nq_fvg15_va10` and `alive` and contains neither `4.1` nor `31,400`; a missing vault gives the "no notes found" line.
- [ ] **Step 2: Run; fail. Step 3: Write the prompts and the code. Step 4: Run; pass. Step 5: Commit**
  `Roles: the four prompts, the reply contract, the Lead's digest`.

---

### Task 6: the brief

**Files:** Create `missions/briefing.py`, `tests/test_briefing.py`.

**Interfaces — Produces:**

```python
QUESTIONS_MAX = 6
async def next_step(mid, answer: str | None = None, *, run_turn, hb) -> dict
    # -> {"ask": {"q", "options"}} | {"brief": {...}}; posts each question and answer to the chat
def approve(mid, said: str, *, hb) -> dict     # writes the Homebase brief, status "ready" (or "queued")
def page(brief: dict, accounts: list[dict]) -> dict   # the one-page brief for the screen, with the firm's bans
```

The Lead gets `prompt("lead", "brief", ...)` with his sentence, the digest and the account list (`hb.accounts()`: id,
name, size, drawdown, risk, bans). It asks one question a turn with 2-4 reply buttons, at most `QUESTIONS_MAX`, then
returns the brief. The engine, not the Lead, validates it:

```python
{"goal": {"kind": "eval"|"points"|"net", "target": <number>, "rule": "<account id>"},   # eval: 0 < target <= 1, rule in accounts()
 "idea": "...", "fixed": ["..."], "may_change": ["..."], "fewest_trades_week": 2.0, "notes": "..."}
```

A brief that fails validation goes back to the Lead once with the reason; a second failure shows him the error and waits.
`approve(mid, said)`: `said` is the text of the button he pressed plus what he typed (the page's button reads "Yes, start:
the team may run heat maps, pick boxes by the score and read test months through the Judge"). It writes

```python
hb.write_brief(mid, {"approved": True, "owner_said": f"{said} (mission {mid}, {date}: {sentence})",
                     "test_months": m["test_months"], "goal": brief["goal"]})
```

and sets status `ready`, or `queued` when another mission is `running`, `paused`, `waiting_plan` or `waiting_owner`.

- [ ] **Step 1: Tests** (fake `run_turn` returning scripted texts): a question turn posts a chat event and returns the
  ask; the answer is fed to the next turn in the same session (`session_id` passed back); after `QUESTIONS_MAX` questions
  the next prompt says "write the brief now"; an eval goal with a closed account (`lucid-flex-50k`) or a target of 50
  (not 0.5) is sent back once, then waits; `approve` writes a brief Homebase accepts (assert the exact keys and that
  `owner_said` holds his words and his sentence); `approve` with an empty `said` is refused; a second mission approved
  while one runs is `queued`; no `drafts` key is ever written.
- [ ] **Step 2-5: fail, implement, pass, commit** `The brief: the Lead's questions, the page, his yes`.

---

### Task 7: the round engine

**Files:** Create `missions/engine.py`, `tests/test_engine.py`, `tests/test_engine_blind.py`, `tests/test_engine_resume.py`.

**Interfaces — Consumes:** `store`, `roles`, `Turn`/`run_turn` (Task 4), the `hb` functions (Task 3), `system` hooks
(Task 8; until then the engine takes them as parameters with no-op defaults).
**Produces:**

```python
STEPS = ("ideas", "build", "wait", "argue", "verdict", "read")
class Engine:
    def __init__(self, mid, *, hb=hb, run_turn=worker.run_turn, system=None, clock=time.time, sleep=asyncio.sleep): ...
    async def run(self) -> str          # runs until a status in DONE, "paused", "waiting_owner"; returns the status
    def board(self) -> dict             # the in-sample scoreboard workers see (also what the page's right panel shows)
def pause(mid); def resume(mid); def stop(mid)
def owner_says(mid, to: str, text: str) -> dict
def approve_read(mid, said: str) -> None      # "Ask me first": his yes for the pending read
async def runner() -> None              # the app's one loop: runs the running mission, then starts the next queued one
```

**The steps** (each ends with `store.save`, so a restart re-enters the step it was in):

1. **Round start.** `round += 1`, fresh sessions (`sessions = {}`). Stop checks, in this order: `stop` asked →
   `stopped`; limits (Task 8: tries, hours, usage; skipped when `until_goal`) → `limit`; `empty_rounds >= 2` →
   `out_of_reach`; `pause` asked → `paused`.
2. **ideas.** Builder, Doubter and Defender each get one turn at the same time (`asyncio.gather`), each alone: its prompt
   holds the brief and the board, not the others' ideas. Then the Lead gets all three and returns the plan. The engine
   keeps at most 3 plan rows, gives each the next free version number, and asks `hb.reach(mid, family)` for each family:
   a row whose family is not reachable is dropped with a Judge chat line ("the luck bar needed is above anything <family>
   has shown"). No row left → `empty_rounds += 1`, next round. Else `empty_rounds = 0`.
3. **build.** One Builder turn with the plan (`max_tool_calls=60`, `timeout_s=1800`). For each row the engine asks
   `hb.made(mid, name)`: only a name with a `wf` row in the mission's ledger counts as built, whatever the Builder says.
   Each built version is saved as `{"name", "version", "round", "family": hb.family_of(name), "job_id", "state":
   "running"}`. A row not built gets one more Builder turn ("these are not on the ledger: ..."), then is dropped.
4. **wait.** No worker runs. Every 30 s: `hb.job(job_id)` for each running version; progress goes to the event stream.
   A job that fails, or is not done after 90 minutes, marks the version `dropped` with the reason.
5. **argue.** For each finished version: `t = hb.table(mid, name)`. No pick → `dropped` ("no box picked: <why_no_pick>").
   Else `g = hb.gate(mid, name, t["pick"])`; save `box`, `gate`; post the Judge's lines, charges and goal value to the
   chat. Then one Doubter turn and one Defender turn, and one more of each if the Doubter's second message carries a new
   claim (cap: 2 exchanges). A claim whose `charge` is not in `CHARGES`, or names a version not in this round, is dropped
   with a Lead-voice line ("not on the list"). Claims never change `gate`: they are shown beside the Judge's result.
   The Defender's `fixes` are kept as `pending["fixes"]` for the next round's ideas.
6. **verdict.** One Lead turn: `to_owner` is posted; `next` is kept for the next round. The engine marks each version
   `cleared` (`gate["clear"]`) or `scored`.
7. **read.** Take the cleared, unread version with the highest `gate["goal"]["value"]`. None → next round. If
   `test_months == "ask"` and there is no approval: status `waiting_owner`, alert, return. Else `hb.start_read(...)`,
   state `reading`, save; poll `hb.read_result` every 20 s. The answer is posted to the chat as the Judge, for workers,
   exactly as given (`held`, `line`, `close`). `held` → status `achieved`. A refusal → posted as the Judge's words, the
   version is `spent`. Anything else → the version is `frozen`, `reads += 1`, next round.

**Free talk and his texts.** `owner_says` appends a chat event. Before any worker turn the engine adds, to that worker's
prompt, every chat line since its last turn that is `for_workers` (the others' talk, the Judge's lines, his texts to it or
to everyone). A text to a worker while the mission is in `wait`, `paused` or `waiting_owner` gets that worker one turn
right away (contract `{"reply": ...}`); the Lead's `plan_change` is kept as `pending["plan_change"]` for the next round.

**The board** (`Engine.board()`), built only from `mission.json` and the door's in-sample answers:

```python
{"goal": {"kind", "target", "rule"}, "round": 3, "tries": {"mission", "family_on_file", "total", "needed_t"},
 "versions": [{"version": "v07", "name": "m7_v07", "family", "state", "box": "20 · #14", "goal_value", "lines_failed": [...],
               "charges_standing": [...], "heard": {"held", "line", "close"} | None}],
 "best": "v07" | None, "reads": 1}
```

**A worker turn that fails.** `why == "plan"` → `system.wait_for_plan(resets_at)` (status `waiting_plan`, then back) and
the same turn again; `timeout` / `too many tool calls` / `crash` → one retry in a fresh session, then a chat line ("the
Doubter did not answer this step") and the step goes on without it. A missing or broken JSON reply → one retry ("end your
message with the json block"), then the same.

- [ ] **Step 1: Tests, `tests/test_engine.py`** (`FakeHB`, a scripted fake `run_turn`, a fake clock and sleep):

```python
async def test_a_round_runs_the_steps_in_order_and_no_step_is_skipped(eng): ...        # the event stream's step rows == STEPS
async def test_ideas_are_written_alone(eng, turns):                                    # no idea text of another worker in any ideas prompt
async def test_an_unreachable_family_is_dropped_before_it_is_built(eng, fake): ...
async def test_two_empty_rounds_stop_as_out_of_reach_even_with_run_until_goal(eng, fake): ...
async def test_a_version_the_ledger_does_not_hold_is_not_built(eng, turns, fake): ...  # Builder claims v08, fake.ledger has no wf row
async def test_no_worker_runs_while_jobs_run(eng, turns, fake): ...                    # zero turns between build and argue
async def test_a_claim_outside_the_five_charges_is_dropped(eng, turns): ...
async def test_a_claim_never_changes_the_gate(eng, turns, fake): ...
async def test_only_a_cleared_version_is_read_and_the_best_goes_first(eng, fake): ...
async def test_held_ends_the_mission_as_achieved(eng, fake): ...
async def test_a_broke_read_freezes_the_version_and_the_next_round_starts(eng, fake): ...
async def test_ask_me_first_waits_and_reads_only_after_his_words(eng, fake): ...       # start_read called with said=<his text>
async def test_plan_used_up_waits_and_reruns_the_same_turn(eng, turns, system): ...
async def test_a_reply_with_no_json_gets_one_retry_then_the_step_goes_on(eng, turns): ...
async def test_stop_wins_over_everything_at_the_next_step(eng): ...
async def test_a_text_to_the_lead_during_a_wait_gets_an_answer_at_once(eng, turns): ...
async def test_one_mission_runs_at_a_time(two_missions): ...                           # runner(): the queued one starts after the first is done
```

- [ ] **Step 2: Tests, `tests/test_engine_blind.py`** (Review Focus 1): plant `"SENTINEL-48213"` and `48213.77` in
  `fake.owner_files` (`reads/m7_v03.json`, `refused.jsonl`, `read.log`); run three rounds with a read; assert the
  sentinel is in no prompt passed to `run_turn`, in no event with `for_workers`, and not in `board()`; assert the engine
  module never calls `owner_read`, `owner_refused` (check `fake.calls`), and that `engine.py`'s source does not contain
  those two names (`inspect.getsource`).
- [ ] **Step 3: Tests, `tests/test_engine_resume.py`** (Review Focus 2): stop the engine (raise from the fake) in the
  middle of `build`, of `wait`, and of `read`; make a new `Engine` from disk; assert: the build turn's second prompt
  lists the names already on the ledger and no version is made twice; the wait goes on with the saved job ids;
  `start_read` is called once in total for the version, and a read whose result file appeared while the app was down is
  used without a second read.
- [ ] **Step 4: Run; fail. Step 5: Implement. Step 6: Run; pass. Step 7: Commit**
  `The round engine: fixed steps, the Judge's calls, the one read, resume`.

---

### Task 8: limits, usage, keep-awake, alerts

**Files:** Create `missions/system.py`, `tests/test_system.py`. Modify `missions/engine.py` (use it).

**Interfaces — Produces:**

```python
RESERVE = 0.90
def note_rate(rate: dict | None) -> None                 # saves the newest windows to home()/"usage.json"
def usage() -> dict                                      # {"five_hour": {"used", "resets_at"} | None, "seven_day": {...} | None, "at"}
def may_start_turn() -> tuple[bool, int | None]          # False + reset time when any window >= RESERVE or rejected
async def wait_for_plan(resets_at, *, sleep) -> None     # sleeps to resets_at + 60 s; 15 minutes when it is unknown
def limit_hit(m: dict, tries_mission: int) -> str | None # "tries" | "hours" | "usage" | None  (None when until_goal)
def awake(on: bool) -> None                              # starts/stops `caffeinate -i -s` (one process, pid in home()/"awake.pid")
def alert(mid, kind: str) -> None                        # kind in ALERTS; macOS notification + ntfy when a topic is set
ALERTS = {"achieved": "goal reached", "limit": "a limit ran out", "out_of_reach": "out of reach",
          "waiting_plan": "waiting for the Claude plan to reset", "waiting_owner": "waiting for your yes to read the test months",
          "crashed": "stopped by an error", "tool": "a new tool waits for your yes"}
def hunt_paused() -> bool | None; def pause_hunt(on: bool) -> None      # PAUSE: yes|no in the steering note
```

- `limit_hit`: tries → `tries_mission >= limits.tries.n`; hours → `run_seconds >= n * 3600`; usage → the 7-day
  `used` minus `m["usage_start"]` (set at the first turn) `>= pct / 100`; a usage window that was never seen → not hit.
  `run_seconds` counts every second the status is `running` (job waits too), not `paused`, `waiting_plan` or
  `waiting_owner`.
- `alert` text is `f"Mission {mid}: {ALERTS[kind]}"` and nothing else. macOS: `osascript -e 'display notification "<text>"
  with title "Missions"'`. ntfy: `POST https://ntfy.sh/<topic>` with that text as the body, only when
  `settings()["ntfy_topic"]` is a non-empty string; a failed send is logged, never raised.
- `awake(True)` while any mission is `running` or `waiting_plan`; `awake(False)` otherwise. The page notes that a closed
  lid on battery still sleeps the Mac.
- The engine calls `may_start_turn()` before every turn, `note_rate(turn.rate)` after it, adds `turn.cost_usd` to
  `m["cost_usd"]`, and `alert` on every status in `ALERTS`.

- [ ] **Step 1: Tests:** a window at 0.91 blocks a turn and gives its reset time; `wait_for_plan` sleeps to the reset +
  60 (fake sleep), 900 s when unknown; each limit trips at its number and none trips with `until_goal`; the usage limit
  uses the move since the start, not the level; `run_seconds` does not grow while paused; the alert text for every kind
  has no digit other than the mission id and no word from the brief (assert against a brief full of sentinels); ntfy is
  not called without a topic (patch `urllib.request.urlopen`); `pause_hunt(True)` rewrites only the `PAUSE:` line of a
  fake steering note; `awake` starts one `caffeinate` and stops it (patch `subprocess.Popen`).
- [ ] **Step 2-5: fail, implement, pass, commit** `Limits, the plan reserve, keep-awake, alerts`.

---

### Task 9: the API and the server

**Files:** Create `missions/api.py`, `missions/__main__.py`, `tests/test_api.py`.

**Routes** (JSON; every write needs a local `Origin`/`Host`):

| Route | Does |
|---|---|
| `GET /` , `/static/*` | the page (`cache-control: no-cache`) |
| `GET /api/missions` | sidebar: `[{id, title, status, round, badge}]` |
| `POST /api/missions` | `{sentence, team, limits, test_months}` → the mission; starts the brief |
| `GET /api/missions/{id}` | `mission.json` + `board` + `right` (goal, best so far, luck bar in plain words, tries, test months, who is doing what) |
| `GET /api/missions/{id}/events?after=n` | past events |
| `GET /api/missions/{id}/stream` | server-sent events: one `data:` line per new event; a comment line every 15 s |
| `POST /api/missions/{id}/brief/answer` `{text}` · `/brief/approve` `{said}` | Task 6 |
| `POST /api/missions/{id}/chat` `{to, text, sure}` | his text; see the warning below |
| `POST /api/missions/{id}/pause` · `/resume` · `/stop` · `/read/approve` `{said}` | the engine's switches |
| `PATCH /api/missions/{id}` `{limits, test_months, team}` | changed while it runs; `test_months` also rewrites the Homebase brief |
| `GET /api/missions/{id}/tested` | every version: name, state, frozen mark, box, goal value, why dropped |
| `GET /api/missions/{id}/table?name=` | `hb.table` |
| `GET /api/missions/{id}/box?name=&box=` | the row + `hb.mc` |
| `GET /api/missions/{id}/odds?name=&box=` | `hb.odds` (slow the first time: returns `{"working": true}` while a thread computes it) |
| `GET /api/missions/{id}/luck?name=` | `{gate, tries, heard, yours}`: `heard` = the read's one-line answer; `yours` = `hb.owner_read` |
| `GET /api/missions/{id}/running` | workers (state, since), jobs (progress), `hb.slots()`, `system.usage()`, cost, run time |
| `GET /api/missions/{id}/progress` | per round: best in-sample goal value, the target, `needed_t` and the best version's t |
| `GET /api/missions/{id}/refused` | `hb.owner_refused` |
| `GET /api/connections` · `POST /api/connections` `{claude, ntfy_topic}` · `POST /api/hunt` `{pause}` | health, settings, the hunt switch |

**The chat warning.** `POST /chat` without `sure: true` returns `{"warn": "This looks like a test-month number. The team
must never see one. Send anyway?"}` instead of sending, when the mission has at least one read **and** the text holds a
digit next to `$`, `%`, `pts`, `points` or `trades`. With `sure: true` it sends.

**The guard** (copy the idea of Homebase's `netguard`, small): middleware that refuses, with 403, any request whose
`Host` header's hostname is not `127.0.0.1` or `localhost`, and any non-GET request whose `Origin` is present and not
`http://127.0.0.1:8860` or `http://localhost:8860`. Websocket is not used.

`__main__`: `uvicorn.run(app, host="127.0.0.1", port=config.PORT, log_level="warning")`; on startup it starts
`engine.runner()` as a task, which resumes a mission left `running`.

- [ ] **Step 1: Tests** (`httpx.AsyncClient` on the app, `FakeHB`, no real engine): each route's shape; a foreign `Host`
  → 403; a POST with `Origin: https://evil.example` → 403; a POST with no `Origin` and a local `Host` → allowed; the
  chat warning fires only after a read and only on number-like text, and `sure` sends; `/luck` puts the owner's numbers
  under `yours` and the one-line answer under `heard`; the stream yields an event appended after it opened; `PATCH`
  with `test_months: "ask"` rewrites the Homebase brief; an unknown mission → 404.
- [ ] **Step 2-5: fail, implement, pass, commit** `The API: missions, the event stream, the owner's pages, the guard`.

---

### Task 10: the page shell, New mission, the brief and the chat

**Files:** Create `tools/sync_css.py`, `missions/static/index.html`, `missions/static/hb/{shadcn,chrome,symbols,system,desk}.css`
(copied), `missions/static/hb/VERSION`, `missions/static/missions.css`, `missions/static/js/{app,fmt,sse,side,new,chat,panel,mic}.js`,
`tests/js/fmt.test.mjs`, `tests/test_colors.py`, `.claude/launch.json`.

- [ ] **Step 1: `tools/sync_css.py`.** From Homebase **main** (`git -C <homebase> show main:<path>`, never the working
  tree): `homebase/static/shadcn.css`, `homebase/static/apple/symbols.css`, `apple/system.css`, `apple/desk.css` as they
  are; and `chrome.css` = the text between the first `<style>` and its `</style>` in `homebase/static/index.html`. Write
  the Homebase commit id to `hb/VERSION`. Run it. `index.html` loads them in that order (shadcn, chrome, symbols, system,
  desk), then `missions.css`; `<html lang="en" data-theme="light" class="hb-apple hb-c-tight hb-ready">`; the theme
  follows `localStorage.hb_theme` like Homebase.
- [ ] **Step 2: `missions.css`.** Start from the mockup's last `<style>` block (`mockup/missions-mockup.html`, the
  Missions-only CSS), without `#demoBanner` and the demo-only rules. Worker colors, both themes:

```css
html.hb-apple { --mx-lead:#0040dd; --mx-builder:#8a5200; --mx-doubter:#8944ab; --mx-defender:#00707c; --mx-judge:#6f5a3e; }
html.hb-apple[data-theme="dark"] { --mx-lead:#6ea8ff; --mx-builder:#e0a040; --mx-doubter:#c79be0; --mx-defender:#4fc3cf; --mx-judge:#c8ae84; }
```

- [ ] **Step 3: `tests/test_colors.py`** (reads `missions.css`): every worker color has a contrast of 4.5:1 or more on
  its theme's window color (`#ffffff` light, `#1e1e1e` dark; WCAG relative luminance); no worker color is within a hue
  distance of 25° of the loss red (`#d70015` light, `#ff4245` dark) or the gain green (`#248a3d`, `#30d158`). If a color
  above fails, change the color, not the test, and say so.
- [ ] **Step 4: `fmt.js` + `tests/js/fmt.test.mjs`** (`node --test tests/js/`): `money(-1234.5) === "−$1,235"`,
  `money(1234.5) === "+$1,235"`, `pct(0.41) === "41 %"`, `pts(4.1) === "+4.1"`, `rr(1.5) === "1:1.5"`,
  `box(20, 14) === "20 · #14"`, `luck(3.5, 7, 3.1) === "needs 3.5 after 7 tries; has 3.1"`, `ago(125) === "2 min"`.
  The minus is `−` (U+2212). A sign is never dropped.
- [ ] **Step 5: The shell** (`index.html`, `app.js`, `side.js`, `sse.js`, `panel.js`), lifted from the mockup's markup and
  script: the toolbar (title, status bulb and chip, Pause, Stop, the gear → Connections, the sidebar and panel toggles);
  the sidebar (New mission, Connections, one group per mission with its status word: `Round 3`, `Next`, `Reached`, `Not
  reached`, `Out of reach`, `Stopped`, and its 8 pages with badges); the right panel (Mission: goal, best so far, luck
  bar, tries, test months; Now: each worker's line in its color; The brief + "Open the brief"). A hash router
  (`#/m/7/chat`). `sse.js` opens `/stream`, re-opens on error with `after=<last n>`, and tells the open page to refresh.
- [ ] **Step 6: New mission** (`new.js`): the goal box with a mic; the team rows (model and effort selects per role, an
  "all effort" menu); Limits ("Run until the goal", tries 10/20/40/80/160, time 2 h/4 h/8 h/1 day/3 days/1 week, Claude
  usage 10/25/40/60/80 %, each with its switch); "Test months": "Team reads them" / "Ask me first"; the "stops when"
  summary line; Start → `POST /api/missions`, then the brief chat.
- [ ] **Step 7: The brief and the chat** (`chat.js`, `mic.js`): the Lead's question with its reply buttons; the one-page
  brief with the firm's bans and "rules read off the firm's page, not confirmed", and the button "Yes, start: the team
  may run heat maps, pick boxes by the score and read test months through the Judge"; the feed (time, name in its color,
  model tag, text, the Judge's data line); the filter (Everyone, Lead, Builder, Doubter, Defender, Judge, You); the
  compose row (input, mic, "To" select, Send) with the warning dialog from `{"warn": ...}`; the step timeline. `mic.js`:
  one press-to-start, press-to-stop button per typing box, `webkitSpeechRecognition` (`continuous`, `interimResults`,
  `en-US`); the button is hidden where the browser has none.
- [ ] **Step 8: `.claude/launch.json`:** `{"version": "0.0.1", "configurations": [{"name": "missions", "runtimeExecutable":
  ".venv/bin/python", "runtimeArgs": ["-m", "missions"], "port": 8860}]}`.
- [ ] **Step 9: Run** `pytest -q`, `node --test tests/js/`. Then start the app with `MISSIONS_DEMO=1` (a flag that serves
  the routes from a fixture mission in `tests/fixtures/demo/`, so the page has data without a real mission) and report
  the console errors seen (there must be none). The planner checks the look in the browser.
- [ ] **Step 10: Commit** `The page: the Homebase look, New mission, the brief, the chat`.

---

### Task 11: the result pages

**Files:** Create `missions/static/js/{running,progress,best,heat,evalpass,tested,luck,conn,home}.js`. Modify
`missions/static/missions.css`, `tests/fixtures/demo/` (data for every page).

Each page is a function `(mission, el)` that fetches its route and renders; each re-renders on a stream event of a type it
names. Lift the markup and classes from the mockup page of the same name. What each must show:

- **Running:** "3 of 4 working"; a row per worker (name, model tag, what it is doing, Working/Waiting/Ready, minutes);
  a row per running table (version, progress bar, "12 of 40"); machines: "This Mac: 6 of 12 slots busy" from
  `hb.slots()` (the real cap, never a fixed number), Claude usage ("5-hour 62 %, week 31 %, this mission used 9 of 40
  points" or "not measured yet"), the cost and run time; the "Pause the hunt loop" switch; the list of refused tool
  calls (time, tool, why).
- **Progress:** a step chart, one point per version in order, of its picked box's in-sample goal value, the best-so-far
  line and the goal line; under it "Where it stands": best so far, the luck bar in words, goal, tries "12 of 40", time.
- **Best so far:** "v07 · 20 · #14" and its settings in RR, points and dollars ("1:1.5, 40-pt stop"); the plain
  sentences (goal value against the goal; full-target % against the % needed; trades a week and $ a trade); By year
  (year, trades, full-target points over, net) then combined; the plain Monte Carlo (`/box`): worst drawdown typical and
  1 in 20, losing streak typical and 1 in 20, net in the 1-in-20 case, % of paths below $0, with "shown only, never
  blocks".
- **Heat map:** a version picker; a switch for the main-setting value (one grid at a time); a switch for the number shown
  (net, points over, full target, PF, Sharpe); the grid: rows = the stops (ATR × 0.5, 1, 1.5, 2; own stop × 0.5, 1, 1.5,
  2; 4 rows when `cells == 20`), columns = targets 1:0.5, 1:0.75, 1:1, 1:1.5, 1:2; each box shows `#<cell>` and the
  number, shaded green or red by net, the sign always shown; rings on the picked box and its touching boxes; the caption
  (the average of the boxes, how many make money); click a box → its numbers and its Monte Carlo. Numbers fit at any
  width: `clamp()` with container units, then drop the `$` and the spaces (the mockup's rules).
- **Eval pass:** the account picker (the open accounts from `/api/connections`' account list, grouped by firm); for the
  picked box and account: pass % "within 10 trading days, live is worse", bust %, days to pass, the careful pass % when
  the account trails intraday, the contract-size flag, the firm's bans, "rules read off the firm's page, not confirmed",
  the rules; and every account for this box, best first. While `{"working": true}`: "working it out (a few minutes)".
- **Tested:** Running and Done lists, best first, a "Best" tag, a lock mark on frozen versions, the reason on dropped.
- **Real or luck:** the six lines with ok / no / sealed marks (line 6 is sealed until a read); the tries and the luck bar
  in words; "What the team heard" (held or broke, which line, close or far) beside "What you see" (`yours`: net, trades,
  months, full-target % against the % needed, points over test months against in-sample, months that made money); the
  five charges, each with the Judge's result and the Doubter's and Defender's words.
- **Connections:** the `claude` binary and its version, with a box to set the path; the Homebase chart service and the
  door (up or down); "Desk, accounts, orders: never"; the ntfy topic box with the line "sends 'Mission 7: goal reached'
  to ntfy.sh; no numbers or names"; the trading server is never used.
- **Home** (no mission picked): the missions, each with its status, cost and result line.

- [ ] **Step 1:** Fill `tests/fixtures/demo/` so every page has data, including a 20-cell family, a frozen version, a
  dropped version, a read that broke with "under the bar", and a loss (to see red beside the Builder's color).
- [ ] **Step 2:** Build the pages. **Step 3:** `pytest -q`, `node --test tests/js/`, run with `MISSIONS_DEMO=1`, report
  console errors (none). **Step 4: Commit** `The result pages: running, progress, best, heat map, eval pass, tested, real or luck`.

---

### Task 12: when a mission ends

**Files:** Create `missions/wrapup.py`, `tests/test_wrapup.py`. Modify `missions/engine.py` (call it on every status in
`DONE`), `missions/api.py` (`POST /api/missions/{id}/dead` `{family, said}`).

**Interfaces — Produces:**

```python
def note(m: dict, board: dict) -> Path       # vault()/30-Projects/Onyx-Trading/Missions/<id>-<slug>.md
def recent_line(m: dict) -> str              # "- 2026-11-14 · code · Mission 7 (<title>): <result words> · [[<note name>]]"
def write(m, board) -> None                  # the note, the RECENT.md line (top of its list), the strategy-map line
def mark_dead(family, why, said) -> None     # adds a row to dead-families.md; only on his word
```

- The note (frontmatter + wikilinks, plain words): the goal, the result (reached / not reached / out of reach / stopped
  / a limit ran out), the best version and its box, the tries, what was tried and why each was dropped, the cost. It is
  the owner's note, so it may carry the in-sample numbers **and** the test-month line as the team heard it (held or
  broke, which line): it never carries the numbers of `reads/*.json` (the vault feeds the next mission's digest and
  every chat).
- The strategy-map line is appended under a `## Missions` heading at the end of
  `what-lives-what-is-dead-2026-11-07.md` (made if absent): `- <date> · <family> · <reached|not reached|out of reach> · [[note]]`.
- A family is never put on the dead list by the app itself: the end page shows "Mark <family> dead" and `mark_dead`
  needs his `said`.

- [ ] **Step 1: Tests** (temp vault): the note has frontmatter and no number from a planted `reads` file; RECENT.md gets
  one new first line and keeps the rest byte for byte; the map line lands under `## Missions`; `mark_dead` without
  `said` is refused; `write` twice for one mission makes one note and one RECENT line.
- [ ] **Step 2-5: fail, implement, pass, commit** `Mission end: the vault note, the feed line, the map line`.

---

### Task 13: launchd, the README and the dry run

**Files:** Create `deploy/com.ramosquant.missions.plist.template`, `deploy/install.sh`, `tests/test_dry_run.py`. Modify `README.md`.

- The plist (like Homebase's charts template): `__REPO__/.venv/bin/python -m missions`, `WorkingDirectory __REPO__`,
  `RunAtLoad`, `KeepAlive`, `ThrottleInterval 10`, logs to `~/.missions/app.log`. `install.sh`: fills `__REPO__`, builds
  `.venv` if missing, `launchctl bootout` then `bootstrap gui/$(id -u)`; `install.sh remove` undoes it. **Do not run
  `install.sh` while building**: the owner (or the planner on his word) runs it.
- `tests/test_dry_run.py`, the whole app with `FakeHB` and a scripted `run_turn`, no real process:
  1. **A goal that cannot be reached:** every table the fake returns fails the gate, and `reach` turns false after 6
     tries → the mission ends `out_of_reach` (or `limit` with a tries limit of 4), never `achieved`, and no read was
     started.
  2. **A planted edge:** the third version's gate is clear and its read holds → `achieved` in round 3, exactly one read,
     the note written.
  3. **A near-copy:** a cleared version's read breaks, the next version clears, its read is "under the bar" → both
     frozen, the mission goes on.
- README: what it is, how to start it (`deploy/install.sh`, `http://127.0.0.1:8860`), where its files are, what it can
  never do (trade, touch the Desk, read test months outside the Judge), and how to run `python -m missions.blindcheck`.

- [ ] **Step 1: The dry-run tests; fail. Step 2: fix what they find. Step 3: pass. Step 4:** `pytest -q` whole suite,
  `node --test tests/js/`. **Step 5: Commit** `launchd, the README, the dry run`.

---

## After the build (each needs the owner's word)

1. Merge Homebase `feat/missions-door` into main (it ships to the trading server; it only adds door commands).
2. Run `deploy/install.sh`.
3. **The two trust checks** (design section 11), real missions with limits on, his yes on each brief:
   a goal the team cannot honestly reach (random entries passing an eval 50 % of the time) must come back "not reached"
   or "out of reach"; a goal on a strategy the map lists as alive must come back "achieved" or stop honestly at its
   limit. Either wrong means the team is broken: no real mission before both pass.

## Not in this plan

- The shelf, new tools, the look-ahead test on shifted data (Plan 3).
- A dark-mode toggle of its own (the page follows Homebase's saved theme).
- Local Whisper; reading the plan's % without a worker turn.

# Design review (2026-11-14)

A fresh reviewer read the design against the real Homebase code and the Claude CLI (v2.1.285). The main claims were
then checked by hand: the families loader imports every module, the one-read guard is keyed on (store, box), the
Monte Carlo default shuffle gives every path the same net, user settings have bypass permissions on, and the CLI has
`--restricted`, `--strict-mcp-config`, `--tools` and `--permission-mode`. Nothing is decided here; the owner picks.

## Fix before building

| # | Problem | Fix | Size |
|---|---|---|---|
| 1 | Shelf code runs with full access when tested (`engine/families/__init__.py` `load()` imports every module), so it could read test months or commit to main | Run every shelf piece (gate and runs that import it) in a sandbox like `draft.sb`: no network, no git, writes only its run folder. Or shelf in v2, drafts in v1 | Large |
| 2 | Workers inherit `~/.claude/settings.json` (bypass permissions, SessionStart hooks that inject RECENT.md, which holds test-month results) and user MCP servers | `claude -p --restricted --strict-mcp-config --tools "Read,Glob,Grep,Write,Edit" --permission-mode dontAsk`, inline `--mcp-config`, cwd outside the repo, an allowlist of `mcp__homebase__*` tools. Test with a worker that prints what it sees | Small |
| 3 | More tools and files show test months than §6 blocks: `blueprint_sim`, `blueprint_portfolio`, `blueprint_eval_card`, `blueprint_mc on=test`, `walkforward oos`, `day_types(walkforward_id)`, `montecarlo` / `prop_eval` / `show_on_chart` on any run, `desk_journal`, `export_start`; files `runs_wf/*/oos/`, `engine/cache/daily_NQ_bt.json` (in git), `findings/*desk-review.md`, `ledger.csv` | Mission mode = a fixed allowlist of tools; run and trade views show only runs this mission made; workers read a pruned copy of the code | Medium |
| 4 | The try count can be dodged: free backtest / heatmap / walkforward runs, shelf smoke runs with P&L, charge runs; a new mission on the same idea starts at 0 | Count every distinct spec that returned P&L; `shelf_check` returns pass/fail only; tries = max(this mission, prior tries on the family) | Medium |
| 5 | A renamed near-copy gets a fresh test-month read (guard keyed on store, box: `blueprint/reads.py`); +1 point a read is about a third of the noise (~3 points standard error at ~280 trades) | Owner's call: raise the bar about one standard error a read; refuse a read when in-sample trades overlap a frozen version's by over ~70 %; count reads across hunt, missions and owner from the one read log | Medium |
| 6 | "Run until the goal" may never end: the t bar is 2 + 0.25 a try (`blueprint/real.py`) | Stop and report when the bar needed is above the best the family has ever shown; run the random-entry self-test with limits on | Small |

## The doc promises what the code can't do yet

- Points over on test months: `blueprint/hunt.py` `score()` reads the in-sample store only.
- Eval pass per box in-sample: `blueprint/propodds.py` runs only on test-month trades after the read, and picks the best preset size (a hidden try). No "risk = drawdown ÷ 2.5". Needs a Judge function.
- A general look-ahead test: `LookAheadError` exists only in the order-book sims (`engine/l2sim.py`). Gate 3 and the look-ahead charge need a shifted-data test.
- Charges: "one side carries it" has no bar; "dead family again" has no machine-readable verdict (the strategy map is prose).
- Monte Carlo: `homebase/backtest/stats/montecarlo.py` defaults to shuffle (same final net on every path); force bootstrap, and add an adapter from the in-sample store to a trade list.
- CLAUDE.md says only the hunt loop may run heat maps without asking: add a Missions paragraph.
- `bp_node` = auto ships only the idea's folder: runs sent to the mini must carry the shelf pieces they use.

## Will hurt in practice

- The Mac sleeps (1 minute idle, lid closed): keep it awake while a mission runs (or run the team on the mini); launchd KeepAlive; save step, session and job ids so it resumes.
- Shared Claude plan with the owner and the hunt loop: a reserve "Run until the goal" can't spend; a pause-the-hunt button. Not checked: whether plan % can be read headless.
- Workers waiting on 25-minute jobs burn usage: the round code waits on job ids, caps turns per step, starts a fresh session each round from a state file.
- Slot counts disagree (connector text 2 in desk hours, CLAUDE.md 12, mockup "6 of 8"): show the machine's real cap.
- Shared names and jobs: `write_strategy`, `delete_draft`, `set_group`, `cancel` can reach the owner's drafts and the hunt's jobs; `v01` clashes between missions. Prefix with `m<id>_`.

## Worth adding

- Phone alerts: achieved, limit hit, waiting for a plan reset, a piece waiting for his commit, a crash.
- Cost per mission; resume with the try count kept; a log of refused tool calls.
- A planted-edge self-test beside the random-entry one: a fake strategy with a known edge must come back "achieved".

## Could cut (owner's call)

The Defender; the shelf in v1 (drafts already work and are sandboxed); the busy timeline; browser speech input first;
only the latest rule set per firm.

## Mockup

- 40 boxes shown, but 3-4 setting values make 120-160 boxes: "#14" is ambiguous.
- "v07 without 2022 → stands" contradicts the 50 % rule; "lucky island" is not on the charge list.
- The Judge's chat names the "best box", not the picked box.
- Builder `#b33000` reads as red beside `#d70015`; dark-mode Lead blue is about 2.2:1.
- "Passes 41 %" should say "within 10 trading days, live is worse"; "luck bar 39 %" has no code behind it (show the t bar).
- He can text test-month numbers to the team, which leaks them: the chat should warn.
- Keep the mockup's "Ask me first" option in the design.

Not checked: whether `--restricted` also drops `~/.claude/CLAUDE.md` and auto-memory; exact model ids; the Blocks
plug-in point for shelf filters.

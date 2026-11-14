# Missions: design (2026-11-14)

Status: draft for the owner's approval, with the design review's fixes and his answers to it folded in
(`docs/reviews/2026-11-14-design-review.md`). Nothing is built yet. The mockup (`mockup/missions-mockup.html`, one
standalone page; its source is in the Homebase checkout at `.superpowers/brainstorm/24222-1794626913/`) is throwaway and
shows the look and the pages. The owner's decisions are in the vault:
`30-Projects/Onyx-Trading/missions-app-owner-decisions-2026-11-14.md`.

## 1. What it is and why

The owner gives an idea and a goal, for example: "a 9:30 straddle that passes an Apex eval 50 % of the time". A team of
Claude agents works on it, round after round, until the goal is reached. He watches from his laptop and can text the team.

Why: one Claude alone can test wrong, test too little, or fool itself. A team with opposed jobs, where fixed code gives
every verdict and counts every try, can work for hours without him and still give a result he can trust.

What success looks like: he opens a mission and can answer "what is happening, is it real, what do I do" in one look.
A mission that reports "achieved" has a strategy that passed the six real-or-luck lines and held on test months that
no worker could tune to.

## 2. Goals, non-goals, anti-goals

**Goals**
- One page per mission: the team chat, who is running, progress to the goal, the best version, its heat map, eval
  pass odds, everything tested, and real or luck.
- The team runs by itself to the goal, with no stops to ask him (his own words: "fully autonomous and no stop until goal
  is achieved").
- Workers can build new tools (an indicator, a filter, an entry, a whole system) and save them, so any later mission or
  chat can use them (section 7).
- Each mission leaves what it learned in the vault, so the next team skips what is dead.

**Non-goals**
- Trading. Missions never places, cancels or manages an order and never touches an account or the Desk.
- Putting a strategy on the Desk. That needs his word, as today.
- Other markets (NQ only, owner 2026-11-13) and non-Claude models (GPT and Gemini would need API keys).
- The strategy pipeline. It stays off.

**Anti-goals** (failure even if it "works")
- A team that reaches the goal by tuning to the test months, or by trying versions until one hits by luck.
- Agents that agree with each other because they share one model's blind spots.
- Anything that can break the Desk or the trading server.
- Jargon on screen, or numbers he has to work out himself.

## 3. Constraints (house law that binds Missions)

- The trading server never backtests (owner, 2026-10-24). Every run is on this Mac (12 slots) or the Mac mini
  (`bp_node` = auto).
- A commit on Homebase `main` reaches the trading server and the mini by itself within about 2 minutes (vpssync,
  minisync). Missions must never commit to Homebase main by itself.
- The 3:1 block walk-forward is the only in-sample / test-month split. The heat map is hm40. Judge the average box, never
  the best. The six real-or-luck lines are in `research/edge-library/blueprint/real.py`, and the bar rises 0.25 a try.
- Sharpe counts traded days only. Bars come from barstore. Reports use RR and points, full-target % against the %
  needed, dollars, trades a week, and per year, then combined.
- **The Missions exception (owner, 2026-11-13/14).** His yes on a mission's brief is his word, for that mission only,
  for three things that otherwise need him: running heat maps, picking the box by the score, and reading the test
  months through the Judge's door (section 6). Every other agent keeps the normal rules. CLAUDE.md does not change.

## 4. Approaches (the three big choices)

**Where it lives.** He picked **a separate app** ("Yeah, I agree").

| | Separate app (picked) | A page inside Homebase |
|---|---|---|
| Trading server | Never touches it | Every change ships to it |
| Risk to the Desk | None | A bug or restart can hit Desk parts |
| Changes | Any time | Only when flat, never 09:10-09:35 |
| Cost | One more app to open; a copy of the styles | None of that |

**How the team works together.** He picked **"a mix of both"**: fixed rounds with free talk inside each step.

| | Mix (picked) | Group chat | Strict rounds |
|---|---|---|---|
| Feels like a team | Yes | Most | Least |
| Steps skipped | Never | Often | Never |
| Agrees too fast | Rarely: every argument ends in a run | Often | Rarely |

**How workers add new tools** (2026-11-14). He picked **the shelf**, with his own step added: "it saved in the
toolkit ... it lets me know and i confirm to commit into the app and repo".

| | Shelf beside the toolkit (my pick) | Write into the Homebase repo | Draft strategies only (today) |
|---|---|---|---|
| Saved and usable at once | Yes, once it passes the gate | Only after a merge | Yes, but only as one strategy |
| Next chat can build from it | Yes | Yes | No: it is not a block |
| Reaches the trading server | No | Every merge, within 2 minutes | No |
| A broken piece | Stays on the workbench | Stops the screen for everyone (`families.ERRORS`) | Hurts only itself |
| Cost | A promote step before the Desk | Agents editing a checkout other sessions use | Not reusable |

**When the shelf comes** (owner, 2026-11-14: "Right after"): the first build has the team, the Judge and the fence,
and workers build with draft strategies, which are already locked down. The shelf is the next part of the same plan,
because a worker's code must run in a sandbox before it can be tested safely (section 7).

## 5. How a mission runs

**1. The brief.** He types one rough sentence and presses Start. The Lead reads the vault first (the strategy map,
findings, his standing rules) and fills in what is already set: NQ only, 2-3 trades a week or more, stop or full target,
fewer rules. It then asks only what is still open, one question at a time, with reply buttons. Typical questions: which
account, what is fixed, what the team may change, risk, the fewest trades a week, and the limits. It writes a one-page
brief. He says yes. The brief is the prompt: every worker works from that same page. The brief says plainly that his yes
allows heat maps, box picks and test-month reads for this mission.

**2. The team.** Each role's model and effort can be changed. Every role starts on High.

| Role | Job | Cannot | Starts on |
|---|---|---|---|
| Lead | Owns the goal and the plan, keeps the count of tries, talks to him | Build or grade | Opus 5.5 |
| Builder | Turns ideas into versions with the blueprint tools; builds new tools (section 7) | Grade its own work | Fable 5.2 |
| Doubter | Argues it is luck or broken: one year carries it, worse fills, look-ahead, same as a dead family | Kill a version with words alone | Sonnet 5.5 (a different model on purpose) |
| Defender | Argues it is real: why the edge exists, who is on the other side, the next fix | Add a rule without a reason | Opus 5.5 |
| Judge | Fixed code: the six real-or-luck lines, the goal measure, the Monte Carlo | Be overruled | (code) |

Each worker has its own color (Lead blue, Builder burnt orange, Doubter purple, Defender teal, Judge brown). Never green
or red: those mean money.

**3. One round.** The order is fixed in code. No agent can skip a step.
1. Ideas: each worker writes its angles alone, without seeing the others; the Lead merges them.
2. Build and run: the Builder makes the versions (names `v01`, `v02` ...) and runs the in-sample table (hm40, 3:1 blocks).
3. Argue: the Judge first runs every charge check below on every version by itself, so no charge can be forgotten or
   dodged. Then the Doubter argues (and reads the code for look-ahead) and the Defender answers with why the edge
   exists and the next fix. Each charge has a fixed check in code with a fixed bar, so no agent grades:

   | Charge | Check (code) |
   |---|---|
   | One year carries it | No year over half the net, 4 of 6 years green (line 4) |
   | Worse fills kill it | Still positive with worse fills (line 5) |
   | It looks ahead | The code check, plus the shifted-data test (future bars changed, past trades the same) |
   | One side carries it | Each side (long, short) has net above $0 after costs on its own; if one side loses, the fix is a version that trades only the side that pays |
   | It is a dead family again | The family is on the dead list: a plain file of family names and verdicts, kept beside the strategy map |

   A charge that holds blocks the version's test-month read; the fix is a new version. The Lead throws out any claim
   that is not on the list or has no run behind it.
4. Verdict: the Judge scores every version. The team picks the box by the score's rule: the box whose touching boxes
   all make money, never the single best box, and never under 2 trades a week.
5. Next round, or the test months (section 6).

Inside a step the workers talk freely and can ask each other for help. The whole chat is saved and shown.

**4. Counting tries.** The Judge counts, not the workers. Every distinct setup that returned a profit or loss is one
try: a version, but also any plain backtest, heat map or walk-forward a worker runs. The count goes to
`real.py --tries`, so the bar rises. Building a tool is not a try; testing a version built with it is. The charge checks
the Judge runs itself are not tries. `shelf_check` says only pass or fail, never a profit or loss.

A mission starts from the larger of 0 and the tries the same family already has on file (the hunt, other missions, the
ledger), so starting a new mission on a worn idea does not reset its luck bar. The page shows both counts.

**5. The goal.** The brief picks one kind, from a fixed list the Judge knows:

| Kind | Measured as |
|---|---|
| Eval pass | The tester's prop sim (`homebase/backtest/propsim.evaluate`) for one of his accounts: the chance of passing within 10 trading weekdays (his 2026-10-03 bar), at one fixed risk = drawdown ÷ 2.5 (capped at the account's contract limit), on the box re-run with worse fills (line 5's fills). Bust % is shown beside it; on an intraday-trail account (Apex Legacy) the careful pass % too |
| Points over | His hunt score (`blueprint/hunt.py`): full-target % minus the % needed, at $1,000 a trade |
| Net | Net after costs, with the six lines |

On the test months the same measure is worked out from the test-month days alone.

The code has two gaps here, both new Judge functions: (1) eval odds per box on in-sample trades (today
`blueprint/propodds.py` runs only on test-month trades after the read, and picks the best of several sizes, which is a
hidden extra try; the Judge uses one fixed risk); (2) points over on the test months (today `hunt.score` reads only the
in-sample store).

**His accounts (added 2026-11-14, with build plan 1).** The goal names one of the 18 accounts he built simulators for
on 2026-11-14 (main d6f3fe2f, `homebase/backtest/propsim/rules/*@2026-11-14.json`): Lucid Maxx 25K/50K, Lucid live
25K/50K, Topstep 50K (+DLL), Apex Legacy 50K/100K/300K, MFFU Builder 100K, MFFU Rapid 25K-150K, MFFU Rapid EOD 25K/50K
(+DLL). An older file of the same account resolves to its newest. Lucid Flex and Lucid Pro are closed ("I got moved to
live and I can't use the flex or the pro accounts anymore"). `propodds` reads only 6 of the 18 (it refuses the intraday
trail, two-step evals, funded blocks and payout day counts), and the stores keep no trade highs, so the Judge re-runs
the one picked box with full trades on the same 3:1 days, checks it gives the store's trades and net (else the number
is withheld), and hands it to the tester's own prop sim, which reads all 18. "Live is worse" is that re-run with line
5's worse fills, because the sim's own haircut skips the intraday trail. Each firm's bans are shown on the brief and on
Eval pass, never checked by code: Apex bans bots on every account; Topstep bans orders from a VPS (the Chicago Desk);
MFFU bans news straddles; Lucid allows no new eval while he is live. Every file is `confirmed: false` (read off the
firms' pages), and the page says so.

**6. When it stops.**
- **Achieved:** the picked box meets the goal in-sample, passes the six lines, and still meets the goal on its test months
  (one read, section 6).
- **Limits:** tries, time and Claude usage each have a number and an on/off switch, where off means no limit. One "Run
  until the goal" switch turns them all off. When his Claude plan runs out, the team waits for it to reset; it never
  stops to ask him. When a limit that is on runs out, the team stops and brings back the closest honest result.
- **Out of reach:** the luck bar rises with every try (t 2 + 0.25 a try). When the bar now needed is higher than
  anything the family has ever shown, more tries cannot win: the team stops and reports "out of reach", even with "Run
  until the goal" on. Without this, a goal it can't reach would run forever.
- **He stops it:** Pause and Stop on the page.

## 6. The test months: the Judge's door

- Only the Judge (code) opens them, through one door, like the hunt loop's `research/edge-library/hunt/bp`. No worker
  has a tool that can read them.
- The Judge opens them only after a version clears the first five checks in-sample, for that version's one picked box,
  run fixed, once. The read is marked `who: mission:<id>`.
- After the read, the version is **frozen**: never run or tuned again. The read counts as a try.
- **The bar rises 1 point a read** (owner: "if the first read has a winrate of 50, the next read must require atleast
  51"). It is counted in points over (full-target % minus the % needed), because the % needed changes with the target:
  - the mission's 1st read must be above 0 points over;
  - the 2nd read above +1;
  - the 3rd above +2, and so on.

  The test-month lines still apply too: positive and in the same direction. There is no cap, so the team never gets
  stuck, but near-copies get harder to pass each time. The reviewer pointed out that with about 280 test trades, luck
  alone moves the full-target % by about 3 points, so +1 a read slows near-copies only a little; the owner kept +1
  (2026-11-14). Each read also counts as a try, so the in-sample luck bar rises too.
- **Who opens them, per mission:** a switch on the mission (from the mockup): "Team reads them" (the default: the
  Judge reads once a version clears every in-sample check) or "Ask me first" (the Judge waits for his yes before each
  read).
- **What the workers hear:** held or broke; which line broke (lost money, flipped direction, too few trades); and close or
  far (close = missed this read's bar by under 1 point). No dollars, %, months or trades, so they can't tune to the test months.
- **What he sees:** the numbers, on Real or luck: net, trades, months, full-target % against the % needed, points over
  (test months against in-sample), and months that made money.
- **Blind for real, not by prompt.** A prompt can't keep the workers blind. Their tools must refuse:
  - The connector gets a **mission mode** (started with the mission's id). It allows a fixed list of tools; anything
    not on the list is refused. On the list, `backtest`, `heatmap` and `walkforward` refuse any range that touches a
    test month, and every view of runs and trades (`blueprint_status`, `get_run`, `trades`, `list_runs`,
    `walkforward show`, `montecarlo`, `prop_eval`, `day_types`) shows only runs this mission made, with no test-month
    result. Off the list: `wf pick`, `wf oos` and `walkforward oos`, `blueprint_sim`, `blueprint_portfolio`,
    `blueprint_eval_card`, `blueprint_mc` on test months, `show_on_chart`, `desk_journal`, `export_start`, and the
    two account tools. Only the Judge's door runs without mission mode.
  - **How a worker starts:** `claude -p --restricted --strict-mcp-config`, with `--tools` naming only Read, Glob, Grep,
    Write and Edit, `--permission-mode dontAsk`, the homebase connector passed inline in `--mcp-config` (so a worker
    can't edit its own config), and its folder outside the Homebase repo. Restricted mode ignores his own settings, so
    workers don't get his "bypass permissions" or the start-up hooks that feed RECENT.md (which holds test-month
    results). The first build checks this with a test worker that lists everything it can see.
  - Workers get no Bash and read a trimmed copy of the code folders, not the whole repo. They can't read the stored
    results, the bar and tick files, or files that hold test-month numbers: `~/.homebase/ideas/**`, the tester's run
    folders (`runs_wf/*/oos/`), `~/futures_derived/**`, `engine/cache/daily_NQ_bt.json`, `ledger.csv`, the desk
    reviews in `docs/superpowers/findings/`, RECENT.md and the memory indexes.
  - The Lead reads the vault through a digest that keeps verdict words (dead, alive, held, failed) and drops
    test-month numbers.
  - If he types test-month numbers into the chat, the box warns him before it sends.

## 7. Building new tools: the shelf

His words: workers must be able to "fully build and code a new indicator or a new system or a new idea ... add it to the
toolkit ... and save it", so a later chat can use it.

**Today.** The toolkit is the blocks `bp.py blocks` lists: entry families (`research/edge-library/engine/families/*.py`,
contract in `families/__init__.py` and `../ENGINE.md`), filters (`families/blocks.py`), indicators
(`engine/indicators.py`), exit tables (`blueprint/templates/*.json`). Adding one means editing the Homebase repo. Draft
strategies (`write_strategy`, saved by `homebase/store/draftstore.py` in `~/.homebase/strategies/`) can hold any code,
but they are one-off strategies, not blocks another idea can reuse.

**The shelf** (`~/.homebase/shelf/`, its own git history, never pushed to Homebase main). It comes right after the
first build (section 4).

**A sandbox first.** The toolkit imports every module in the families folder inside the research Python
(`engine/families/__init__.py`, `load()`), with full access. A worker's code would run that way when tested: it could
read test-month files, or commit to main, which reaches the trading server in 2 minutes. So every shelf piece, in the
gate and in every run that imports it, runs under a sandbox profile like the drafts' `draft.sb`: no network, no git,
writes only to its own run folder.
- **What can go on it:** an indicator (a reading over bars), a filter (two sides, the Blocks contract), an entry (a
  family, with its rationale written before any test), or a whole strategy (a draft, linked from the shelf).
- **Each piece** is one folder `<kind>/<name>_v<n>/` with its code, a card (what it does in one line, why it should
  work, its settings and their ranges, who built it, which mission, the date), its own small test, and the gate's result.
- **The gate (code, not an agent).** A piece is listed only when all of these pass:
  1. It imports alone.
  2. It meets the contract (`families.check_entry`, the Blocks schema).
  3. No look-ahead: changing future bars never changes a past value. This shifted-data test must be built: today
     `LookAheadError` exists only in the order-book sims (`engine/l2sim.py`), and the other look-ahead tests are per
     family.
  4. Same trades at 1 worker and at 8.
  5. A smoke run on a few in-sample months finishes.
  6. It draws its indicators on the chart (owner rule).
  7. Its own test passes.

  A piece that fails stays on the workbench, listed with the reason. The Doubter also reads the code for look-ahead
  before its first real run.
- **Never edited in place** after its first run. A change is a new version (`_v2`), so old results stay true.
- **Everyone can use it.** The toolkit reads the shelf beside its own blocks: `blueprint_blocks` / `bp.py blocks` and
  the Lab's Toolkit view list shelf pieces marked "shelf · v1 · built by mission X". So does every mission and every
  new Claude chat, through the same connector. A broken shelf piece never blocks the repo's own families: it has its
  own error list. A run sent to the mini (`bp_node` = auto ships only the idea's folder) carries the shelf pieces it
uses with it, so it never reaches the mini before minisync has copied them.
- **It tells him, and he confirms the commit** (his words: "it lets me know and i confirm to commit into the app and
  repo").
  - When a piece passes the gate, it is on the shelf, and every chat can use it at once.
  - The app tells him: a line in the mission's chat, a "New tools" list on the Missions home with each piece's card
    and code, and a `RECENT.md` line.
  - When he confirms, the piece is committed into the Homebase repo: only its own files and its test, made from a
    clean copy of main. Only then does it reach the trading server and the mini.
  - Until he confirms, it stays on the shelf, still usable for testing. Nothing built on it can go on the Desk before
    it is committed.
- **What workers may touch:** they can read the whole Homebase repo, to learn how the toolkit works. They can write
  only the shelf's workbench and the mission's own scratch folder. They never write the repo and never run git on it.
  This must be enforced by permission rules and the CLI sandbox, not only by the prompt.
- **How the Builder runs its code without Bash:** two new tools in the existing homebase connector (so no new MCP):
  - `shelf_check <piece>` runs the piece's own test, the seven gate checks, and an in-sample smoke run, then returns
    pass or fail and what failed, never a profit or loss (so it is not a free try).
  - `shelf_list` shows the shelf and the workbench.

  When every check passes, the piece moves from the workbench to the shelf by itself.
- **What stays fixed:** the exits under test stay the hm40 grid (stop × target), because that is how every idea is
  judged. A new exit idea can be built and shown, but the heat map does not change for it.

## 8. The app

**The look:** exactly the Homebase look (the Desk's `hb-apple` styles, copied): silver and white, Apple-style, glass only
on floating panels. No redesign; he rejected the last one. Anything he might pick is numbered (boxes #1-#40, versions
v01...). Every number fits its box at any window width: the type shrinks, then the `$` and spaces drop. The + / − sign
always stays, because color must never carry meaning alone.

**Sidebar:** New mission, Connections, then one group per mission with its status (Round 3, Reached, Not reached).
Each mission has its own pages:

| Page | What it shows |
|---|---|
| Chat | The team chat. He can text the Lead or anyone. Press-to-record mic in every typing box |
| Running | Who is working on what and for how long, the test that is running with its progress, a timeline, Mac and Claude usage |
| Progress | Distance to the goal, round by round |
| Best so far | The best version's numbers, per year then combined, and the plain Monte Carlo |
| Heat map | The 40 boxes for one main-setting value at a time (a switch picks the value; at 3 values there are 120 boxes), shaded green/red by net. A box is named by both, e.g. "20 · #14", so a number is never ambiguous. A switch picks the number shown (net, points over, full target, PF, Sharpe). Click a box for its numbers and its Monte Carlo |
| Eval pass | Pick one of his accounts (the 18 of 2026-11-14, newest file of each; Lucid Flex/Pro closed). It shows pass % "within 10 trading days, live is worse", bust %, days to pass, the careful pass % on Apex Legacy, the contract-size flag, the firm's bans, "rules read off the firm's page, not confirmed", the rules, and every account for the clicked box, best first |
| Tested | Every version, with frozen marks |
| Real or luck | The six lines, the try count and the luck bar in plain words ("needs t 3.5 after 7 tries; has 3.1"); what the team heard about the test months beside what he sees |

**Right panel:** the mission (goal, best so far, luck bar, tries, test months), who is doing what now, and the brief.

**Plain Monte Carlo:** shown only, never blocks. It redraws the same days at random, with repeats. It shows worst
drawdown (typical and 1 in 20), losing streak (typical and 1 in 20), net in the 1-in-20 case, and the % of paths that end
below $0. Use the tester's own `homebase/backtest/stats/montecarlo.py` in its bootstrap mode (its default, shuffle,
gives every path the same final net, so "% below $0" would be 0 or 100), with a small adapter from the in-sample store
to its trade list. Eval odds are separate, on the Eval pass page.

**Worker colors:** the Builder's burnt orange must not read as red beside a loss (`#b33000` next to `#d70015` does), and
every worker color must pass contrast in dark mode too (the Lead's blue is about 2.2:1 there).

**When he's away:** an alert on his phone when the goal is reached, a limit runs out, the team waits for a plan reset, a
tool waits for his commit, or something crashes. Each mission shows what it cost in Claude usage and machine time,
and a list of the tool calls the fence refused.

**Press to record:** speech is typed into the box he is in. He presses to start and to stop.

**Limits:** tries, time and Claude usage, each a number with its own switch, plus "Run until the goal" (section 5).

## 9. Connections and machines

- **Its own folder** on this Mac (`~/missions`), its own git history, opened in his browser on its own local address.
  Python with FastAPI, like Homebase.
- **The team** runs on his Claude login through the `claude` CLI, with no API key. Each worker is a `claude -p` process
  with its role's `--model` and `--effort`, `--mcp-config` holding only the homebase connector
  (`python -m homebase.claude_mcp`), and stream-json output, which feeds the chat. Its session is resumed between steps.
- **The team's tools:** the connector's tester tools only. `account_reconnect` and `account_remove` are switched off
  (`--disallowedTools`). The connector has no order tool. Workers get no `pipeline_*` tools; they are already removed.
- **The round order is Python code**, not an agent. The Lead is a worker inside it. The code, not a worker, waits on
  long jobs (a walk-forward can take 25 minutes): it holds the job ids and wakes the worker when they finish, caps the
  turns a worker gets per step, and starts each round's sessions fresh from a saved state file, so idle waiting never
  burns usage.
- **Crashes and sleep:** the Mac sleeps after a minute idle and when the lid closes. While a mission runs, the app
  keeps the Mac awake (a closed lid on battery still sleeps it). launchd keeps the app alive, and the app saves the
  step, the session ids and the job ids, so after a crash or restart the mission picks up where it was, try count kept.
- **Where runs happen:** this Mac's tester slots, shared with everything else, and the mini by itself
  (`bp_node` = auto). Never the trading server. The page shows the machine's real slot cap, not a fixed number.
- **One mission runs at a time.** The others wait in line (marked "Next" in the sidebar). Claude usage is shared with
  anything else on his login (his own chats, the hunt loop on the mini); the Running page shows it. A reserve of his
  plan is kept that "Run until the goal" can't spend, and the page has a button to pause the hunt loop.
- **Names:** everything a mission makes (drafts, versions, groups, jobs) starts with `m<id>_`, and mission mode lets a
  worker delete, cancel or regroup only its own mission's things, never his drafts or the hunt's jobs.
- **Homebase changes this needs**, through normal commits he approves. First build:
  - the Judge's door for missions (like `hunt/bp`), with the Judge's try count;
  - two Judge functions: eval odds per box in-sample at one fixed risk, and points over on the test months;
  - the connector's mission mode (section 6);
  - the dead list (a plain file of family names and verdicts);
  - a Missions paragraph in Homebase's CLAUDE.md, which today says only the hunt loop may run heat maps without
    asking.

  Right after (the shelf):
  - the sandbox for shelf code, and the general shifted-data look-ahead test;
  - the `shelf_check` and `shelf_list` tools;
  - the toolkit reading the shelf;
  - runs sent to the mini carrying the shelf pieces they use, and minisync carrying the shelf.

## 10. Memory

- Each mission keeps its own folder (brief, chat, versions, Judge results, try count) in the Missions app.
- When a mission ends, it writes one note to the vault (`30-Projects/Onyx-Trading/Missions/<mission>.md`): goal,
  result, best version, what is dead and why. It also adds a line to the strategy map (what lives, what is dead) and a
  `RECENT.md` line, so the desktop app sees it too.
- New shelf pieces get a line in `RECENT.md` when they pass the gate.

## 11. Decided by him, and my calls

**He decided:** a separate app; reuse the homebase connector (tester tools only); the exact Homebase look; a color per
worker, never green or red; pages per mission; a press-to-record mic in every typing box; limits each on/off plus "Run
until the goal"; no stops until the goal; the team may read test months itself (Missions only); Apex pass off the heat
map, with its own Eval pass page and a firm/eval picker; the Judge's test-month report; the plain Monte Carlo; workers
can build and save new tools for later use; the shelf, where it tells him and he confirms each commit into the repo;
the test-month bar rising 1 point a read; numbers must fit their boxes. After the design review (2026-11-14): keep +1
a read (he saw that luck alone moves it about 3 points); the shelf comes right after the first build; keep the
Defender.

**My calls (he can overrule):**
- The shelf's details in section 7: location, the sandbox, the seven gate checks, and never editing a piece in place.
- Blind for real: the connector's mission mode as a fixed list of tools, the restricted worker start, no Bash, the
  trimmed code copy, the vault digest, the chat warning (section 6).
- The fixed list of charges and their checks (section 5, step 3); the Judge runs every check on every version.
- Tries: every setup that returned a profit or loss counts, and a mission starts from the family's tries on file.
- "Out of reach": the team stops when the luck bar needed is above the family's best, even with "Run until the goal".
- The "Ask me first" test-month switch, kept from the mockup.
- Eval pass is measured within 10 trading weekdays, his 2026-10-03 bar ("judge evals on 10 days"). If he meant
  passing at any time before bust, the Judge changes one setting.
- One mission runs at a time.
- What "achieved" means: the goal also holds on the test months.
- Close = missed the read's bar by under 1 point. Risk a trade on Eval pass = drawdown ÷ 2.5.
- The box-pick rule (the hunt score's rule).
- The models per role.
- FastAPI and the `claude -p` worker setup.
- Folder names.
- Two checks before trusting any real mission, run with limits on: give the team a goal it cannot honestly reach
  (random entries passing at 50 %), and one with a planted edge (a made-up strategy with a known edge). The first must
  come back "not reached" or "out of reach", the second "achieved". Either way wrong means the team is broken.
- Keeping the Mac awake while a mission runs, the plan reserve, the `m<id>_` names.

## 12. Left to the builder

- How a worker's writes are fenced in (CLI sandbox settings, OS permissions).
- The mic: the browser's speech recognition or local Whisper.
- How Claude usage is measured for the usage limit and the reserve, and how a plan reset is detected (not checked:
  whether the plan's % used can be read without a window).
- How alerts reach his phone.
- Whether `--restricted` also leaves out his global CLAUDE.md and auto-memory (not checked; the test worker shows it).
- The mission folder's file formats, and how the page gets live updates.
- The exact gate tests, as long as they cover the seven checks.
- How the Missions app reuses the Homebase CSS (copy now; how to keep it in step later).

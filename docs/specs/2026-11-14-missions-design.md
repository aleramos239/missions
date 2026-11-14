# Missions: design (2026-11-14)

Status: draft for the owner's approval. Nothing is built yet. The mockup (`mockup/missions-mockup.html`, one
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
3. Argue: the Doubter files charges and the Defender answers. Every charge is one of a fixed list, and each kind has a
   fixed check in code with a fixed bar, so no agent grades:

   | Charge | Check (code) |
   |---|---|
   | One year carries it | No year over half the net, 4 of 6 years green (line 4) |
   | Worse fills kill it | Still positive with worse fills (line 5) |
   | It looks ahead | The code check, plus the shifted-data test (future bars changed, past trades the same) |
   | One side carries it | Each side's net on its own |
   | It is a dead family again | The named family's verdict on file |

   A charge that holds blocks the version's test-month read; the fix is a new version. The Lead throws out any claim
   that is not on the list or has no run behind it.
4. Verdict: the Judge scores every version. The team picks the box by the score's rule: the box whose touching boxes
   all make money, never the single best box, and never under 2 trades a week.
5. Next round, or the test months (section 6).

Inside a step the workers talk freely and can ask each other for help. The whole chat is saved and shown.

**4. Counting tries.** Every version tested is one try. The count starts at 0 for each mission and goes to
`real.py --tries`, so the bar rises. Building a tool is not a try; testing a version built with it is. A run that only
settles a charge is not a try, because it makes no new version. The page also shows how many earlier tries the same idea
had on file (the hunt, other missions, the ledger), so he can see how worn it is.

**5. The goal.** The brief picks one kind, from a fixed list the Judge knows:

| Kind | Measured as |
|---|---|
| Eval pass | The tester's prop sim for one firm and eval from the rule sets: the chance of passing within 10 trading weekdays (his 2026-10-03 bar), on the "live is worse" row, at risk = drawdown ÷ 2.5. Bust % is shown beside it |
| Points over | His hunt score (`blueprint/hunt.py`): full-target % minus the % needed, at $1,000 a trade |
| Net | Net after costs, with the six lines |

On the test months the same measure is worked out from the test-month days alone.

**6. When it stops.**
- **Achieved:** the picked box meets the goal in-sample, passes the six lines, and still meets the goal on its test months
  (one read, section 6).
- **Limits:** tries, time and Claude usage each have a number and an on/off switch, where off means no limit. One "Run
  until the goal" switch turns them all off. When his Claude plan runs out, the team waits for it to reset; it never
  stops to ask him. When a limit that is on runs out, the team stops and brings back the closest honest result.
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
  stuck, but near-copies get harder to pass each time.
- **What the workers hear:** held or broke; which line broke (lost money, flipped direction, too few trades); and close or
  far (close = missed this read's bar by under 1 point). No dollars, %, months or trades, so they can't tune to the test months.
- **What he sees:** the numbers, on Real or luck: net, trades, months, full-target % against the % needed, points over
  (test months against in-sample), and months that made money.
- **Blind for real, not by prompt.** A prompt can't keep the workers blind. Their tools must refuse:
  - The connector gets a **mission mode** (started with the mission's id). In it, `backtest`, `heatmap` and
    `walkforward` refuse any range that touches a test month, and `wf pick` / `wf oos` refuse outright.
    `blueprint_status`, `get_run`, `trades`, `list_runs` and `walkforward show` leave out every test-month result,
    for every idea, not only this mission's. Only the Judge's door runs without mission mode.
  - Workers get no Bash, and permission rules stop them reading the stored results and the bar and tick files
    (`~/.homebase/ideas/**`, the tester's run folders, `~/futures_derived/**`).
  - The Lead reads the vault through a digest that keeps verdict words (dead, alive, held, failed) and drops
    test-month numbers.

## 7. Building new tools: the shelf

His words: workers must be able to "fully build and code a new indicator or a new system or a new idea ... add it to the
toolkit ... and save it", so a later chat can use it.

**Today.** The toolkit is the blocks `bp.py blocks` lists: entry families (`research/edge-library/engine/families/*.py`,
contract in `families/__init__.py` and `../ENGINE.md`), filters (`families/blocks.py`), indicators
(`engine/indicators.py`), exit tables (`blueprint/templates/*.json`). Adding one means editing the Homebase repo. Draft
strategies (`write_strategy`, saved by `homebase/store/draftstore.py` in `~/.homebase/strategies/`) can hold any code,
but they are one-off strategies, not blocks another idea can reuse.

**The shelf** (`~/.homebase/shelf/`, its own git history, never pushed to Homebase main):
- **What can go on it:** an indicator (a reading over bars), a filter (two sides, the Blocks contract), an entry (a
  family, with its rationale written before any test), or a whole strategy (a draft, linked from the shelf).
- **Each piece** is one folder `<kind>/<name>_v<n>/` with its code, a card (what it does in one line, why it should
  work, its settings and their ranges, who built it, which mission, the date), its own small test, and the gate's result.
- **The gate (code, not an agent).** A piece is listed only when all of these pass:
  1. It imports alone.
  2. It meets the contract (`families.check_entry`, the Blocks schema).
  3. No look-ahead: changing future bars never changes a past value, and the engine's `LookAheadError` never fires.
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
  own error list. minisync carries the shelf to the mini with the idea folder, so heavy runs there can use it.
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
    what failed.
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
| Heat map | The 40 boxes, shaded green/red by net. A switch picks the number shown (net, points over, full target, PF, Sharpe). Click a box for its numbers and its Monte Carlo |
| Eval pass | Pick a firm and an eval from the tester's rule sets (`homebase/backtest/propsim/rules/*.json`). It shows pass %, bust %, days to pass, the rules, and every eval for the clicked box, best first |
| Tested | Every version, with frozen marks |
| Real or luck | The six lines, the try count and the luck bar; what the team heard about the test months beside what he sees |

**Right panel:** the mission (goal, best so far, luck bar, tries, test months), who is doing what now, and the brief.

**Plain Monte Carlo:** shown only, never blocks. It redraws the same days at random, with repeats. It shows worst
drawdown (typical and 1 in 20), losing streak (typical and 1 in 20), net in the 1-in-20 case, and the % of paths that end
below $0. Use the tester's own `homebase/backtest/stats/montecarlo.py` (it already shuffles or bootstraps whole days).
Eval odds are separate, on the Eval pass page.

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
- **The round order is Python code**, not an agent. The Lead is a worker inside it.
- **Where runs happen:** this Mac's tester slots, shared with everything else, and the mini by itself
  (`bp_node` = auto). Never the trading server.
- **One mission runs at a time.** The others wait in line (marked "Next" in the sidebar). The tester's own slot cap
  sets how many runs go at once. Claude usage is shared with anything else on his login (the hunt loop on the mini);
  the Running page shows it.
- **Homebase changes this needs**, through normal commits he approves:
  - the Judge's door for missions (like `hunt/bp`);
  - the connector's mission mode (section 6);
  - the `shelf_check` and `shelf_list` tools;
  - the toolkit reading the shelf;
  - minisync carrying the shelf.

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
the test-month bar rising 1 point a read; numbers must fit their boxes.

**My calls (he can overrule):**
- The shelf's details in section 7: location, the seven gate checks, and never editing a piece in place.
- Blind for real: the connector's mission mode, no Bash for workers, the vault digest (section 6).
- The fixed list of charges and their checks (section 5, step 3).
- Tries start at 0 each mission; runs that settle a charge are not tries.
- Eval pass is measured within 10 trading weekdays, his 2026-10-03 bar ("judge evals on 10 days"). If he meant
  passing at any time before bust, the Judge changes one setting.
- One mission runs at a time.
- What "achieved" means: the goal also holds on the test months.
- Close = missed the read's bar by under 1 point. Risk a trade on Eval pass = drawdown ÷ 2.5.
- The box-pick rule (the hunt score's rule).
- The models per role.
- FastAPI and the `claude -p` worker setup.
- Folder names.
- A first check before trusting any real mission: give the team a goal it cannot honestly reach (random entries passing
  at 50 %). If it comes back "achieved", the team is broken.

## 12. Left to the builder

- How a worker's writes are fenced in (CLI sandbox settings, OS permissions).
- The mic: the browser's speech recognition or local Whisper.
- How Claude usage is measured for the usage limit, and how a plan reset is detected.
- The mission folder's file formats, and how the page gets live updates.
- The exact gate tests, as long as they cover the seven checks.
- How the Missions app reuses the Homebase CSS (copy now; how to keep it in step later).

# Missions

A team of Claude agents chases one strategy goal until it is reached, for example "a 9:30 straddle that passes an
Apex eval 50 % of the time". The team: Lead, Builder, Doubter, Defender, and a Judge that is fixed code. It runs on this
Mac, tests through the Homebase strategy tester, and never trades.

## Start it

```
deploy/install.sh          # builds .venv if missing, installs the launchd job, starts it
deploy/install.sh remove   # undoes it
```

Then open http://127.0.0.1:8860. launchd restarts the job if it exits (`KeepAlive`, 10 s apart), and starts it at login. Homebase must be running for missions to test. The job's PATH is `/opt/homebrew/bin:/usr/local/bin:~/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin`; if `claude` is somewhere else, set `"claude"` to its full path in `~/.missions/settings.json` (the key `config.claude_bin` reads).

## Where its files are

| What | Where |
|---|---|
| The app log | `~/.missions/app.log` |
| Each mission (brief, chat, versions, status) | `~/.missions/` |
| A mission's Homebase side (ledger, frozen versions, refused calls) | `~/.homebase/missions/<id>/` |
| The note written when a mission ends | Obsidian vault, plus a line in `RECENT.md` |
| The design | [docs/specs/2026-11-14-missions-design.md](docs/specs/2026-11-14-missions-design.md) |
| Product context | [docs/PRODUCT.md](docs/PRODUCT.md) |

## What it can never do

- Trade, place or cancel an order, touch an account or the Desk, or run anything on the trading server.
- Read test months outside the Judge. Workers see in-sample numbers and the Judge's one-line answer only.
- Run a heat map without the owner's words in the approved brief.

## Checks

```
.venv/bin/python -m pytest -q            # the suite, including the whole-app dry runs (tests/test_dry_run.py)
node --test tests/js/
.venv/bin/python -m missions.blindcheck  # one real haiku turn proving what a worker sees; needs the Homebase chart service
```

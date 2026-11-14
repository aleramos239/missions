# Task 9 report: the API and the server
- missions/api.py: make_app(hb, run_turn, runner) with all routes of the brief, guard middleware (Host + Origin, 403), SSE via event_stream (comment line first and every 15 s), hb.Down -> 503, Refused -> 409, ValueError/KeyError -> 400, unknown mission -> 404. Routes calling briefing are async def on the loop.
- missions/__main__.py: uvicorn on 127.0.0.1:PORT; the module-level app starts engine.runner() in its lifespan.
- engine._save: limits, test_months, team are owner-owned (OWNER_KEYS); test added in tests/test_engine.py (fails without the fix).
- hb.set_test_months (+ FakeHB twin): PATCH test_months rewrites the Homebase brief without needing the owner_said text.
- odds: one thread per (mission, name, box); {"working": true} until done; errors shown once then forgotten.
- Chat warning: only when the mission has >=1 read and text has a digit next to $, %, pts, points, trades; sure:true sends.
- Tests: 17 new in tests/test_api.py + 1 engine; full suite 228 pass. SSE tested on the generator (httpx ASGITransport buffers streams).
- Not done: no page (missions/static/index.html absent; "/" serves a bare title). The luck bar's "has t" reads the gate's luck line `t`/`value` key, a guess (the Judge's line shape is not confirmed) and shows None if absent.

## Fix round 1
1. Luck bar: t parsed from the luck line's `said` ("t 3.1 ..."), None when absent; tests use the real gate shape; "needs 3.5 after 7 tries; has 3.1" asserted; progress best_t too.
2. table/box/odds need one of the mission's own version names (404 otherwise); hb.table/mc/odds call `_name`.
3. Background brief catches any exception, writes an engine event, mission stays `briefing`; next /brief/answer retries.
4. briefing.next_step runs hb.accounts in a thread under the lock; approve runs in a thread with `loop=` passed for its lock check; API hb calls go through to_thread.
5. Guard is pure ASGI; stream stops when `request.is_disconnected` (tested via `gone`).
6. Switch routes built by a factory; `?fn=x` ignored.
7. Host compare case-insensitive; global ValueError/KeyError handlers replaced by a local `Bad`; main() behind `__main__`; warn matches trade/point/pt singular; PATCH limits keys and team roles validated.
Suite: 234 pass.

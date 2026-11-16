"""The round engine: fixed steps, the Judge's calls, the one read, resume. Run on the event loop.

Blind: worker text is built from the brief, the vault digest, the door's table/gate/tries/reach (in-sample), the chat, and
the read's one line {held, line, close}. Nothing here asks Homebase for the owner's files."""
import asyncio
import copy
import re
import time

from . import digest as _digest, hb as _hb, roles, store, system as _system, worker, wrapup

STEPS = ("ideas", "build", "wait", "argue", "verdict", "read")
ROLES3 = ("builder", "doubter", "defender")
WORKING = ("running", "waiting_plan", "waiting_homebase")
JSON_RETRY = "Your last message had no json block I could read. End your message with the json block."
JOB_POLL, READ_POLL, JOB_LIMIT = 30, 20, 90 * 60
MAX_FAILED_ROUNDS = 6  # Lead plans that could not be made or checked, in a row: then the mission crashes
NO_JOB_WAIT = 10 * 60  # a wf row with no job row yet: wait this long for the job before calling the version done
READ_LIMIT, READ_SLOW = 6 * 3600, 300  # after READ_LIMIT s the read is polled every READ_SLOW s, with a line
OWNER_KEYS = ("limits", "test_months", "team")
_active = set()
_answers = {}  # mid -> the one answer task


def _plain(text, cap=200):
    """A door refusal for a worker: its words, minus every token that holds a digit, so it can carry no number."""
    return " ".join(w for w in str(text).split() if not re.search(r"\d", w))[:cap] or "The Judge refused."


class _NoSystem:
    """No-op system hooks, for tests."""

    def may_start_turn(self):
        return True, None

    def note_rate(self, rate):
        pass

    async def wait_for_plan(self, resets_at, *, sleep):
        await sleep(900)

    def limit_hit(self, m, tries_mission):
        return None

    def usage(self):
        return {}

    def awake(self, on):
        pass

    def alert(self, mid, kind):
        pass


class _Done(Exception):
    def __init__(self, status):
        self.status = status


def _goal_scalar(goal):
    """A goal's value as one number for the board: a years goal reports its per-year rows; the board shows the weakest recent year's win rate."""
    v = goal.get("value")
    if goal.get("kind") != "years" or not isinstance(v, list):
        return v
    by = {r["year"]: r["win_rate"] for r in v}
    return min((by.get(y, 0.0) for y in goal.get("recent") or []), default=None)


def _ask_path(mid):
    return store.mdir(mid) / "ask"


def _asked(mid):
    try:
        return _ask_path(mid).read_text().strip()
    except OSError:
        return ""


def _set_status(mid, status):
    m = store.load(mid)
    m["status"] = status
    store.save(m)
    store.event(mid, "status", "engine", status, for_workers=False)
    _ended(mid, status)


def _ended(mid, status):
    """The wrap-up, for every status in DONE; it never throws (the vault is the owner's, not the mission's)."""
    if status not in store.DONE:
        return
    try:
        eng = Engine(mid)
        wrapup.write(eng.m, eng.board())
    except Exception as e:
        store.event(mid, "chat", "engine", f"The wrap-up note failed: {type(e).__name__}: {e}", for_workers=False)


def pause(mid):
    _ask_path(mid).write_text("pause")
    if mid not in _active and store.load(mid)["status"] in WORKING:
        _set_status(mid, "paused")


def stop(mid):
    _ask_path(mid).write_text("stop")
    if mid not in _active and store.load(mid)["status"] not in store.DONE:
        _set_status(mid, "stopped")


def resume(mid):
    _ask_path(mid).unlink(missing_ok=True)
    if store.load(mid)["status"] in ("paused", "crashed"):
        busy = any(o["id"] != mid and o["status"] in WORKING for o in store.missions())
        _set_status(mid, "queued" if busy else "running")


def owner_says(mid, to, text) -> dict:
    if to not in (*store.ROLES, "all"):
        raise ValueError(f"bad recipient: {to}")
    e = store.event(mid, "chat", "owner", text, to=None if to == "all" else to)
    t = _answers.get(mid)
    if to != "all" and mid not in _active and store.load(mid)["status"] in ("paused", "waiting_owner") \
            and not (t and not t.done()):  # one answer task a mission: extra calls are dropped
        try:
            _answers[mid] = asyncio.get_running_loop().create_task(Engine(mid).answer())
        except RuntimeError:
            pass  # no loop: the next run answers it
    return e


def approve_read(mid, said) -> None:
    if not isinstance(said, str) or not said.strip():
        raise ValueError("the owner's words are needed")
    m = store.load(mid)
    if m["status"] != "waiting_owner" or not m["pending"].get("read_for"):
        raise ValueError("no read waits for his yes")
    m["pending"]["read_ok"] = said.strip()
    m["status"] = "queued" if any(o["id"] != mid and o["status"] in WORKING for o in store.missions()) else "running"
    store.save(m)
    store.event(mid, "status", "engine", m["status"], for_workers=False)


class Engine:
    def __init__(self, mid, *, hb=_hb, run_turn=worker.run_turn, system=None, clock=time.time, sleep=asyncio.sleep,
                 backoff=(30, 300)):
        self.mid, self.hb, self.run_turn, self.system = mid, hb, run_turn, system or _system
        self.clock, self.sleep, self.backoff = clock, sleep, backoff
        self.m = store.load(mid)
        self._t = None
        self._digest = None
        self._look()

    # ---- small helpers

    def _save(self):
        now = self.clock()
        if self._t is not None and self._st in _system.RUNNING:  # the span belongs to the status last saved
            self.m["run_seconds"] += max(0, now - self._t)
        self._t = now
        try:  # keep what the owner or the API changed on disk since this engine last saw it
            disk = store.load(self.mid)
        except (OSError, ValueError):
            disk = None
        if disk:
            if disk["status"] != self._seen[0] and self.m["status"] == self._seen[0]:
                self.m["status"] = disk["status"]
            ok = disk["pending"].get("read_ok")
            if ok != self._seen[1]:
                self.m["pending"]["read_ok"] = ok
            for k in OWNER_KEYS:  # the owner's PATCH: the engine never changes these itself
                if disk.get(k) != self._seen[2].get(k):
                    self.m[k] = disk.get(k)
        store.save(self.m)
        self._look()

    def _look(self):
        self._st = self.m["status"]
        self._seen = (self.m["status"], self.m["pending"].get("read_ok"),
                      copy.deepcopy({k: self.m.get(k) for k in OWNER_KEYS}))

    def _say(self, who, text, to=None, for_workers=True, data=None):
        return store.event(self.mid, "chat", who, text, data=data, to=to, for_workers=for_workers)

    def _judge(self, text):
        self._say("judge", text)

    def _status(self, status):
        if self.m["status"] != status:
            self.m["status"] = status
            self._save()
            store.event(self.mid, "status", "engine", status, for_workers=False)
            _ended(self.mid, status)

    def _goto(self, step):
        if _asked(self.mid) == "stop":
            raise _Done("stopped")
        self.m["step"] = step
        self._save()
        if step:
            store.event(self.mid, "step", "engine", step, for_workers=False)

    def _check_stop(self):
        if _asked(self.mid) == "stop":
            raise _Done("stopped")

    async def _nap(self, seconds):
        """Sleep in slices of 30 s; Stop ends it, Pause leaves the step to be re-entered."""
        while seconds > 0:
            self._check_stop()
            if _asked(self.mid) == "pause":
                raise _Done("paused")
            await self.sleep(min(seconds, 30))
            seconds -= 30
        self._check_stop()
        if _asked(self.mid) == "pause":
            raise _Done("paused")

    async def _h(self, name, *a):
        """A Homebase call that waits out an outage (capped backoff) and then goes on with the same step."""
        delay, prev = self.backoff[0], None
        while True:
            try:
                r = await asyncio.to_thread(getattr(self.hb, name), *a)
            except _hb.Down as e:
                if prev is None:
                    prev = self.m["status"]
                    self._status("waiting_homebase")
                    self._say("engine", f"Homebase is not answering ({_plain(e)}). Waiting.", for_workers=False)
                await self._nap(delay)
                delay = min(delay * 2, self.backoff[1])
                continue
            if prev is not None:
                self._status(prev)
            return r

    def _v(self, ref):
        return next((v for v in self.m["versions"] if ref in (v["version"], v["name"])), None)

    def _round_versions(self, *states):
        return [v for v in self.m["versions"] if v["round"] == self.m["round"] and (not states or v["state"] in states)]

    # ---- the board

    def board(self) -> dict:
        m = self.m
        g = (m.get("brief") or {}).get("goal") or {}
        tries = m["pending"].get("tries") or {"mission": len(m["versions"]), "family_on_file": 0,
                                               "total": len(m["versions"]), "needed_t": None}
        out = []
        for v in m["versions"]:
            gate = v.get("gate") or {}
            out.append({"version": v["version"], "name": v["name"], "family": v.get("family"), "state": v["state"],
                        "box": v.get("box_label"), "goal_value": _goal_scalar(gate.get("goal") or {}),
                        "lines_failed": [x["line"] for x in gate.get("lines", []) if not x.get("ok")],
                        "charges_standing": [x["charge"] for x in gate.get("charges", []) if not x.get("held")],
                        "heard": v.get("heard")})
        scored = [v for v in out if v["goal_value"] is not None and v["state"] not in ("dropped", "spent")]
        best = max(scored, key=lambda v: v["goal_value"])["version"] if scored else None
        return {"goal": {"kind": g.get("kind"), "target": g.get("target"), "rule": g.get("rule"), "recent": g.get("recent")}, "round": m["round"],
                "tries": tries, "versions": out, "best": best, "reads": m["reads"]}

    async def _refresh_tries(self, family):
        if not family:
            return
        try:
            t = await self._h("tries", self.mid, family)
        except _hb.Refused:
            return
        self.m["pending"]["tries"] = {k: t.get(k) for k in ("mission", "family_on_file", "total", "needed_t")}

    # ---- worker turns

    def _chat_for(self, role, exclude=()):
        seen = self.m["pending"].setdefault("seen", {})
        rows = store.events(self.mid, seen.get(role, 0))
        if rows:
            seen[role] = rows[-1]["n"]
        shown = [e for e in rows if e["type"] == "chat" and e["for_workers"] and e["who"] != role
                 and e["to"] in (None, role) and e["text"] and e["n"] not in exclude]
        done = self.m["pending"].setdefault("answered", [])
        done += [e["n"] for e in shown if e["who"] == "owner" and e["to"] == role and e["n"] not in done]  # shown: answered
        return "\n".join(f"{e['who']}: {e['text']}" for e in shown)

    async def _wait_plan(self, resets_at):
        prev = self.m["status"]
        self._status("waiting_plan")
        self.system.alert(self.mid, "waiting_plan")
        await self.system.wait_for_plan(resets_at, sleep=self._nap)  # sliced: Pause and Stop count
        self._status(prev if prev in ("paused", "waiting_owner") else "running")

    def _team(self, role):
        """The owner's team as saved now, so a PATCH mid-run reaches the next turn (not only the next _save)."""
        try:
            self.m["team"] = store.load(self.mid)["team"]
        except (OSError, ValueError, KeyError):
            pass
        return self.m["team"][role]

    async def _once(self, role, step, chat, ask, session, kw, digest=None):
        while True:
            team = self._team(role)
            ok, resets = self.system.may_start_turn()
            if not ok:
                await self._wait_plan(resets)
                continue
            pr = roles.prompt(role, step, brief=self.m["brief"], board=self.board(), chat=chat, ask=ask or None,
                              digest=digest)
            t = await self.run_turn(self.mid, role, pr, model=team["model"], effort=team["effort"],
                                    session_id=session, **kw)
            self.system.note_rate(t.rate)
            if self.m["usage_start"] is None and (w := self.system.usage().get("seven_day")):
                self.m["usage_start"] = w["used"]
            self.m["cost_usd"] += t.cost_usd or 0
            if t.why == "plan":
                await self._wait_plan(t.resets_at)
                continue
            return t

    async def _turn(self, role, step, ask="", *, exclude=(), digest=None, **kw):
        """(turn, reply dict) or (None, None) after one retry. The prompt's chat is fixed once, so a retry repeats it."""
        chat = self._chat_for(role, exclude)
        session, msg = self.m["sessions"].get(role), ask
        used = self.m.setdefault("session_model", {})
        if session and used.get(role) not in (None, self._team(role)["model"]):
            session = None  # a resumed session cannot change model: this role starts fresh
            self.m["sessions"].pop(role, None)
        for _ in (0, 1):
            t = await self._once(role, step, chat, msg, session, kw, digest)
            if t.ok:
                self.m["sessions"][role] = t.session_id or session
                used[role] = self.m["team"][role]["model"]
                self._save()
                if (r := roles.reply(t.text)) is not None:
                    return t, r
                session, msg = t.session_id or session, f"{JSON_RETRY}\n\n{ask}".strip()
            else:
                session = None
                self.m["sessions"].pop(role, None)
        self._say("engine", f"The {role} did not answer this step.")
        self._save()
        return None, None

    # ---- the run

    async def run(self) -> str:
        if self.mid in _active:
            return self.m["status"]
        self.m = store.load(self.mid)
        self._look()
        if self.m["status"] in store.DONE:
            return self.m["status"]
        _active.add(self.mid)
        self._t = None
        self.system.awake(True)
        try:
            self._status("running")
            while True:
                if self.m["step"] is None:
                    self._round_start()
                    self._goto("ideas")
                await getattr(self, "_" + self.m["step"])()
        except _Done as d:
            self._status(d.status)
            if d.status != "paused":
                self.system.alert(self.mid, d.status)
            return d.status
        except Exception as e:  # a crash keeps the step: the next run re-enters it
            self._say("engine", f"Stopped by an error: {type(e).__name__}: {e}", for_workers=False)
            self._status("crashed")
            self.system.alert(self.mid, "crashed")
            return "crashed"
        finally:
            _active.discard(self.mid)
            self.system.awake(False)

    def _round_start(self):
        m = self.m
        if _asked(self.mid) == "stop":
            raise _Done("stopped")
        if not (m["limits"] or {}).get("until_goal") and self.system.limit_hit(m, len(m["versions"])):
            raise _Done("limit")
        if m["empty_rounds"] >= 2:
            raise _Done("out_of_reach")
        if _asked(self.mid) == "pause":
            raise _Done("paused")
        m["round"] += 1
        m["sessions"] = {}

    # ---- 1. ideas

    def _digest_text(self):
        if self._digest is None:
            self._digest = _digest.digest()
        return self._digest

    async def _ideas(self):
        m, p = self.m, self.m["pending"]
        alone = f"The Lead said last round: {p['next']}" if p.get("next") else ""
        res = await asyncio.gather(*[self._turn(r, "ideas", alone, digest=self._digest_text()) for r in ROLES3])
        ideas = {}
        for r, (_, rep) in zip(ROLES3, res):
            ideas[r] = [i for i in ((rep or {}).get("ideas") or [])[:3]
                        if isinstance(i, dict) and isinstance(i.get("idea"), str) and isinstance(i.get("family"), str)]
            for i in ideas[r]:
                self._say(r, f"{i['idea']} ({i['family']}) {i.get('why', '')}".strip(), for_workers=False)
        ask = ["The three ideas:"] + [f"{r}: {i}" for r in ROLES3 for i in ideas[r]]
        if p.get("fixes"):
            ask += ["The Defender's fixes from last round:", str(p["fixes"])]
        if p.get("plan_change"):
            ask.append(f"The owner's change to the plan: {p['plan_change']}")
        if p.get("next"):
            ask.append(f"What you said the next round tries: {p['next']}")
        t, rep = await self._turn("lead", "ideas", "\n".join(ask), digest=self._digest_text())
        rows = [r for r in ((rep or {}).get("plan") or []) if isinstance(r, dict) and isinstance(r.get("idea"), str)
                and isinstance(r.get("family"), str)][:3]
        plan, unchecked = [], t is None or not rows  # no usable plan is a failed round, never an empty one
        for r in rows:
            p["vn"] = n = p.get("vn", max((int(v["version"][1:]) for v in m["versions"]), default=0)) + 1
            row = {"version": f"v{n:02d}", "name": roles.version_name(self.mid, n), "idea": r["idea"],
                   "family": r["family"], "why": r.get("why", "")}
            try:
                reach = await self._h("reach", self.mid, r["family"])
                why = None if reach.get("reachable") else \
                    f"the luck bar needed is above anything {r['family']} has shown"
            except _hb.Refused as e:
                why, unchecked = _plain(e), True
            if why:
                self._judge(f"{row['version']} is dropped: {why}.")
            else:
                plan.append(row)
        p["plan"] = plan
        if plan:
            p["fixes"] = p["plan_change"] = None
            m["empty_rounds"] = 0
            p["failed_rounds"] = 0
            await self._refresh_tries(plan[0]["family"])
            self._goto("build")
            return
        m["step"] = None
        if unchecked:  # a failed turn or a refused check is not an empty round: the same round again, after a nap
            p["failed_rounds"] = k = p.get("failed_rounds", 0) + 1
            m["round"] -= 1
            self._save()
            if k >= MAX_FAILED_ROUNDS:  # a crash, not a stop: it holds under until_goal too
                p["failed_rounds"] = 0
                self._save()
                raise RuntimeError(f"The Lead's plan failed {k} rounds in a row. Check the Lead and Homebase, then resume.")
            self._say("engine", "The Lead's plan could not be made or checked this round. Trying the round again.",
                      for_workers=False)
            await self._nap(min(60 * k, 600))
            return
        p["fixes"] = p["plan_change"] = None
        m["empty_rounds"] += 1
        self._save()
        store.event(self.mid, "step", "engine", "ideas: nothing left to build", for_workers=False)

    # ---- 2. build

    async def _register(self, row, builder_job):
        """Only a name with a wf row on the ledger counts as built, whatever the Builder says."""
        if self._v(row["name"]):
            return True
        made = await self._h("made", self.mid, row["name"])
        if not (made and made.get("wf")):
            return False
        self.m["versions"].append({"name": row["name"], "version": row["version"], "round": self.m["round"],
                                   "family": await asyncio.to_thread(self.hb.family_of, row["name"]) or row["family"],
                                   "job_id": made.get("job_id") or builder_job, "state": "running",
                                   "since": self.clock(), "idea": row["idea"]})
        self._save()
        return True

    async def _build(self):
        plan, jobs = self.m["pending"]["plan"], {}
        for attempt in (0, 1):
            for r in plan:
                await self._register(r, jobs.get(r["version"]))
            left = [r for r in plan if not self._v(r["name"])]
            if not left:
                break
            ask = "Make these versions and start their tables:\n" + "\n".join(
                f"{r['version']} ({r['name']}): {r['idea']} [{r['family']}] {r['why']}" for r in left)
            if done := [r["name"] for r in plan if self._v(r["name"])]:
                ask += f"\nAlready on the ledger, do not make them again: {', '.join(done)}"
            if attempt:
                ask = "These are not on the ledger: " + ", ".join(r["name"] for r in left) + ". Make them now.\n" + ask
            _, rep = await self._turn("builder", "build", ask, max_tool_calls=60, timeout_s=1800)
            for b in (rep or {}).get("built") or []:
                if isinstance(b, dict):
                    jobs[b.get("version")] = b.get("job_id")
        for r in plan:
            if not await self._register(r, jobs.get(r["version"])):
                self._judge(f"{r['version']} is not on the ledger and is dropped.")
        self._goto("wait")

    # ---- 3. wait (no worker runs)

    async def _wait(self):
        while running := self._round_versions("running"):
            await self.answer()
            self._check_stop()
            for v in running:
                if not v["job_id"]:  # a wf row without its job row yet: ask again, for a while
                    made = await self._h("made", self.mid, v["name"])
                    v["job_id"] = made and made.get("job_id")
                    if not v["job_id"]:
                        if self.clock() - v["since"] > NO_JOB_WAIT:
                            v["state"] = "done"
                        continue
                try:
                    j = await self._h("job", v["job_id"])
                except _hb.Refused as e:
                    v["state"], v["why"] = "dropped", _plain(e)
                    self._judge(f"{v['name']} is dropped: {v['why']}.")
                    continue
                if j["done"] and j["ok"]:
                    v["state"] = "done"
                elif j["done"]:
                    v["state"], v["why"] = "dropped", j.get("said") or "the job failed"
                    self._judge(f"{v['name']} is dropped: {v['why']}.")
                elif self.clock() - v["since"] > JOB_LIMIT:
                    v["state"], v["why"] = "dropped", "not done after 90 minutes"
                    self._judge(f"{v['name']} is dropped: not done after 90 minutes.")
                elif j.get("progress") != v.get("progress"):
                    v["progress"] = j.get("progress")
                    store.event(self.mid, "progress", "engine", v["name"], data=j.get("progress"), for_workers=False)
            self._save()
            if self._round_versions("running"):
                await self._nap(JOB_POLL)
        self._goto("argue")

    # ---- 4. argue

    def _gate_text(self, v, g, label):
        bad = [f"{x['line']}: {x['said']}" for x in g["lines"] if not x.get("ok")]
        broke = [f"{c['charge']}: {c['why']}" for c in g["charges"] if not c.get("held")]
        gl = g["goal"]
        return (f"{v['name']}, box {label}. Lines passed: {len(g['lines']) - len(bad)} of {len(g['lines'])}"
                + (f"; failed: {'; '.join(bad)}" if bad else "")
                + (f". Charges that broke: {'; '.join(broke)}" if broke else ". No charge broke")
                + f". Goal {gl['kind']}: {gl['value']} against {gl['target']}, {'met' if gl['met'] else 'not met'}.")

    def _claims(self, rep, key, who):
        out = []
        for c in (rep or {}).get(key) or []:
            v = self._v(c.get("version")) if isinstance(c, dict) else None
            if not v or v["round"] != self.m["round"] or v["state"] not in ("gated",) or c.get("charge") not in roles.CHARGES:
                self._say("lead", f"A point of the {who} is not on the list and is dropped: "
                          f"{c.get('charge') if isinstance(c, dict) else c}.")
                continue
            out.append(c)
            self._say(who, f"{v['version']} · {c['charge']}: {c.get('say', '')}")
        return out

    async def _argue(self):
        m = self.m
        for v in self._round_versions("done"):
            try:
                t = await self._h("table", self.mid, v["name"])
                if not t.get("pick"):
                    why = f"no box picked: {t.get('why_no_pick')}"
                    v["state"], v["why"] = "dropped", why
                    self._judge(f"{v['name']} is dropped: {why}.")
                    continue
                g = await self._h("gate", self.mid, v["name"], t["pick"])
            except _hb.Refused as e:
                v["state"], v["why"] = "dropped", _plain(e)
                self._judge(f"{v['name']} is dropped: {v['why']}.")
                continue
            row = next((r for r in t.get("rows", []) if r.get("box") == t["pick"]), {})
            v.update(box=t["pick"], gate=g, state="gated",
                     box_label=f"{row['value']} · #{row['cell']}" if row else str(t["pick"]))
            self._judge(self._gate_text(v, g, v["box_label"]))
            self._save()
        gated = self._round_versions("gated")
        if gated:
            seen = set()
            summary = "\n".join(self._gate_text(v, v["gate"], v["box_label"]) for v in gated)
            ask = summary
            fixes = []
            for ex in (1, 2):
                _, rep = await self._turn("doubter", "argue", ask)
                claims = self._claims(rep, "claims", "doubter")
                new = [c for c in claims if (c["version"], c["charge"]) not in seen]
                seen |= {(c["version"], c["charge"]) for c in claims}
                if ex == 2 and not new:
                    break
                _, rep = await self._turn("defender", "argue", "The doubter's claims:\n" + ("\n".join(
                    f"{c['version']} · {c['charge']}: {c.get('say', '')}" for c in claims) or "None."))
                self._claims(rep, "answers", "defender")
                fixes += [f for f in (rep or {}).get("fixes") or [] if isinstance(f, dict)]
                ask = "The defender answered. Add a new claim only if there is one."
            m["pending"]["fixes"] = fixes
        self._goto("verdict")

    # ---- 5. verdict

    async def _verdict(self):
        vs = self._round_versions()
        ask = "\n".join(f"{v['name']}: {v['state']}" + (f", {v['why']}" if v.get("why") else "") for v in vs) \
            or "No version this round."
        _, rep = await self._turn("lead", "verdict", ask)
        if rep:
            if isinstance(rep.get("to_owner"), str):
                self._say("lead", rep["to_owner"], for_workers=False, data={"to_owner": True})
            if isinstance(rep.get("next"), str):
                self.m["pending"]["next"] = rep["next"]
        for v in self._round_versions("gated"):
            v["state"] = "cleared" if v["gate"].get("clear") else "scored"
        self._goto("read")

    # ---- 6. read

    async def _read(self):
        m, p = self.m, self.m["pending"]
        v = next((x for x in m["versions"] if x["state"] == "reading"), None)
        if not v:
            ok = [x for x in m["versions"] if x["state"] == "cleared"]
            if not ok or p.get("read_round") == m["round"]:  # one read a round, even after a resume
                return self._end_round()
            v = max(ok, key=lambda x: x["gate"]["goal"].get("value") or 0)
            said = None
            if m["test_months"] == "ask":
                if p.get("read_for") != v["name"] or not p.get("read_ok"):
                    p["read_for"] = v["name"]
                    self._save()
                    self._say("engine", f"{v['name']} cleared in-sample. Waiting for your yes to read its test months.",
                              for_workers=False)
                    raise _Done("waiting_owner")
                said = p.pop("read_ok")
                p.pop("read_for")
            v.update(state="reading", read_said=said, read_since=self.clock())
            p["read_round"] = m["round"]
            self._save()  # saved before the start: a restart finds "reading" and asks for the start again
        # start_read is idempotent (a claim or a result means nothing new starts), so every entry asks for it
        await self._h("start_read", self.mid, v["name"], v["box"], v.get("read_said"))
        slow = False
        while (r := await self._h("read_result", self.mid, v["name"])) is None:
            await self.answer()
            if not slow and self.clock() - v.get("read_since", self.clock()) > READ_LIMIT:
                slow = True
                self._say("engine", f"The read of {v['name']} is taking very long. Still waiting.", for_workers=False)
            await self._nap(READ_SLOW if slow else READ_POLL)
        if "refused" in r:
            v["state"] = "spent"
            m["step"] = None
            self._save()
            self._judge(_plain(r["refused"]))
            return
        heard = {k: r.get(k) for k in ("held", "line", "close")}
        v["heard"] = heard
        v["state"] = "frozen"
        m["reads"] += 1
        m["step"] = None  # the same save: a resume never picks a second version in this round
        if heard["held"]:
            m["result"] = {"version": v["version"], "name": v["name"], "box": v.get("box_label")}
        self._save()
        self._judge(f"The test months: held={heard['held']}. {heard['line']}. {heard['close']}.")
        if heard["held"]:
            raise _Done("achieved")
        _, rep = await self._turn("lead", "read", f"The Judge answered: {heard}")
        if rep and isinstance(rep.get("why"), str):  # advice only: the Lead never ends a mission
            p["next"] = rep["why"]
        self._save()

    def _end_round(self):
        self.m["step"] = None
        self._save()

    # ---- his texts

    async def answer(self):
        """One turn right away for every text of the owner to one worker that no normal turn has shown yet."""
        p = self.m["pending"]
        for e in store.events(self.mid):
            if e["type"] == "chat" and e["who"] == "owner" and e["to"] in store.ROLES \
                    and e["n"] not in p.setdefault("answered", []):
                p["answered"].append(e["n"])
                _, rep = await self._turn(e["to"], "owner", e["text"], exclude={e["n"]})
                if rep and isinstance(rep.get("reply"), str):
                    self._say(e["to"], rep["reply"])
                    if e["to"] == "lead" and isinstance(rep.get("plan_change"), str):
                        p["plan_change"] = rep["plan_change"]
        self._save()


async def runner(*, until_idle=False, idle_s=2, **kw) -> None:
    """The app's one loop: the running mission first, else the oldest queued one."""
    while True:
        ms = store.missions()
        pick = next((m for m in ms if m["status"] in WORKING), None) \
            or next(iter(sorted((m for m in ms if m["status"] in ("queued", "ready")), key=lambda m: m["id"])), None)
        if pick is None:
            if until_idle:
                return
            await asyncio.sleep(idle_s)
            continue
        if pick["status"] in ("queued", "ready"):  # "ready" = approved, never started
            _set_status(pick["id"], "running")
        await Engine(pick["id"], **kw).run()

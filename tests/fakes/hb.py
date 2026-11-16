"""FakeHB: the in-memory twin of missions.hb for the engine tests. A test fills the dicts; every call is logged."""
from missions.hb import Down, Refused, Slow  # noqa: F401  (the engine catches these)


class FakeHB:
    Refused, Down, Slow = Refused, Down, Slow

    def __init__(self):
        self.calls = []
        self.tables, self.gates, self.reads, self.jobs = {}, {}, {}, {}
        self.started = []
        self.tries_, self.odds_, self.mcs, self.families, self.made_ = {}, {}, {}, {}, {}
        self.briefs, self.ledgers, self.owner_files = {}, {}, {}
        self.accounts_, self.specs = [], {}
        self.slots_ = {"cap": 4, "running": 0}
        self.health_ = {"chart_service": True, "door": True, "claude": "2.1.321"}
        self.reach = _Reach(self)  # fake.reach[family] is filled; hb.reach(mid, family) is called

    def _get(self, d, key, call):
        self.calls.append(call)
        v = d.get(key)
        if isinstance(v, Exception):
            raise v
        if v is None:
            raise Refused("no such fake")
        return v

    def accounts(self):
        self.calls.append(("accounts",))
        return self.accounts_

    def tries(self, mid, family):
        return self._get(self.tries_, family, ("tries", mid, family))

    def gate(self, mid, name, box):
        return self._get(self.gates, (name, box), ("gate", mid, name, box))

    def table(self, mid, name):
        return self._get(self.tables, name, ("table", mid, name))

    def odds(self, mid, name, box):
        return self._get(self.odds_, (name, box), ("odds", mid, name, box))

    def mc(self, mid, name, box):
        return self._get(self.mcs, (name, box), ("mc", mid, name, box))

    def start(self, mid, name):
        """A carded name starts (made_ gets its wf row and job j1); fake.refuse_start[name] = "why" refuses it."""
        self.calls.append(("start", mid, name))
        why = getattr(self, "refuse_start", {}).get(name)
        if isinstance(why, Exception):
            raise why
        if why:
            raise Refused(why)
        if not any(r.get("kind") == "card" and r.get("ref") == name for r in self.ledgers.get(mid, [])):
            raise Refused(f"{name}: no card of it on the mission's ledger")
        self.made_[(mid, name)] = {"wf": True, "job_id": "j1"}
        return {"job_id": "j1"}

    def probe(self, mid, name):
        self.calls.append(("probe", mid, name))
        return {"per_value": {"5": 3.0}, "most": 3.0, "floor": 2.0}

    def check(self, mid, name):
        self.calls.append(("check", mid, name))
        r = getattr(self, "checks", {}).get(name, {"name": name, "passed": True, "failed": []})
        if isinstance(r, Exception):
            raise r
        return r

    def card_example(self, mid, base=None):
        self.calls.append(("card_example", mid, base))
        return getattr(self, "card_example_", None)

    def write_brief(self, mid, brief):
        self.calls.append(("write_brief", mid, brief))
        if "drafts" in brief:
            raise Refused("drafts are off for missions")
        self.briefs[mid] = dict(brief)

    def unapprove(self, mid):
        self.calls.append(("unapprove", mid))
        if mid in self.briefs:
            self.briefs[mid]["approved"] = False

    def set_test_months(self, mid, tm):
        self.calls.append(("set_test_months", mid, tm))
        if mid in self.briefs:
            self.briefs[mid]["test_months"] = tm

    def ledger(self, mid):
        self.calls.append(("ledger", mid))
        return self.ledgers.get(mid, [])

    def made(self, mid, name):
        self.calls.append(("made", mid, name))
        return self.made_.get((mid, name))

    def family_of(self, name):
        self.calls.append(("family_of", name))
        return self.families.get(name)

    def idea_spec(self, name):
        self.calls.append(("idea_spec", name))
        return self.specs.get(name)

    def job(self, job_id):
        self.calls.append(("job", job_id))
        return self.jobs.get(job_id, {"done": False, "ok": False, "said": "", "progress": None})

    def slots(self):
        self.calls.append(("slots",))
        return self.slots_

    def health(self):
        self.calls.append(("health",))
        return self.health_

    # owner-only
    def owner_read(self, mid, name):
        self.calls.append(("owner_read", mid, name))
        return self.owner_files.get(("read", mid, name))

    def owner_refused(self, mid):
        self.calls.append(("owner_refused", mid))
        return self.owner_files.get(("refused", mid), [])

    def start_read(self, mid, name, box, said=None):
        self.calls.append(("start_read", mid, name, box, said))
        self.started.append((mid, name, box, said))
        return 4242

    def read_result(self, mid, name):
        self.calls.append(("read_result", mid, name))
        return self.reads.get(name)

    def card(self, mid, name):
        return self._get(self.__dict__.setdefault("cards", {}), name, ("card", mid, name))


class _Reach:
    """fake.reach[family] = answer; calling fake.reach(mid, family) (the hb.reach shape) reads it and logs the call."""

    def __init__(self, fake):
        self.fake, self.d = fake, {}

    def __setitem__(self, k, v):
        self.d[k] = v

    def __getitem__(self, k):
        return self.d[k]

    def __call__(self, mid, family):
        return self.fake._get(self.d, family, ("reach", mid, family))

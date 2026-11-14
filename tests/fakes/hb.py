"""FakeHB: the in-memory twin of missions.hb for the engine tests. A test fills the dicts; every call is logged."""
from missions.hb import Down, Refused  # noqa: F401  (the engine catches these)


class FakeHB:
    Refused, Down = Refused, Down

    def __init__(self):
        self.calls = []
        self.tables, self.gates, self.reads, self.jobs, self.reach_ = {}, {}, {}, {}, {}
        self.tries_, self.odds_, self.mcs, self.families, self.made_ = {}, {}, {}, {}, {}
        self.briefs, self.ledgers, self.owner_files = {}, {}, {}
        self.accounts_ = []
        self.slots_ = {"cap": 4, "running": 0}
        self.health_ = {"chart_service": True, "door": True, "claude": "2.1.321"}
        self.reach = _Reach(self)  # fake.reach[family] is filled; hb.reach(mid, family) is called
        self.reach_calls = self.reach

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

    def write_brief(self, mid, brief):
        self.calls.append(("write_brief", mid, brief))
        if "drafts" in brief:
            raise Refused("drafts are off for missions")
        self.briefs[mid] = dict(brief)

    def unapprove(self, mid):
        self.calls.append(("unapprove", mid))
        if mid in self.briefs:
            self.briefs[mid]["approved"] = False

    def ledger(self, mid):
        self.calls.append(("ledger", mid))
        return self.ledgers.get(mid, [])

    def made(self, mid, name):
        self.calls.append(("made", mid, name))
        return self.made_.get((mid, name))

    def family_of(self, name):
        self.calls.append(("family_of", name))
        return self.families.get(name)

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
        return 4242

    def read_result(self, mid, name):
        self.calls.append(("read_result", mid, name))
        return self.reads.get(name)


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

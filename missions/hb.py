"""The Homebase adapter: the only module that knows how to call into Homebase (the Judge's door, the brief file, jobs,
slots, the owner's files). Reads Homebase's files; never writes any but the brief."""
import json
import os
import re
import shlex
import socket
import subprocess
import time

from . import config, store

OK_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
_children = {}  # pid -> Popen of reads this process started
BRIEF_KEYS = {"approved", "owner_said", "test_months", "goal", "exits", "target_r"}
STOPPED = "the read stopped; the owner has the details"


class Refused(Exception):
    pass


class Down(Exception):
    pass


class Slow(Down):
    pass


def _box(box):
    b = str(box)
    if not OK_NAME.match(b) or b.startswith("-"):
        raise Refused(f"{box!r}: not a box")
    return b


def _name(name):
    if not isinstance(name, str) or not OK_NAME.match(name) or name.startswith("."):
        raise Refused(f"{name!r}: not a version name")
    return name


def door(*args, timeout=600):
    j = config.judge()
    try:
        r = subprocess.run([str(j), *map(str, args)], capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
    except (FileNotFoundError, PermissionError) as e:
        raise Down(f"the Judge's door is not there ({j})") from e
    except subprocess.TimeoutExpired as e:
        raise Slow(f"the Judge's door took more than {timeout} s and was stopped") from e
    out = r.stdout.strip()
    try:
        data = json.loads(out)
    except ValueError:
        # exit 2 (unknown command) prints plain words
        raise Refused(out or r.stderr.strip() or f"the door stopped with exit {r.returncode}") from None
    if r.returncode != 0:
        raise Refused(data.get("refused", out) if isinstance(data, dict) else out)
    return data


def accounts():
    return door("accounts")


def tries(mid, family):
    return door("tries", mid, family)


def reach(mid, family):
    return door("reach", mid, family)


def gate(mid, name, box):
    return door("gate", mid, name, _box(box), timeout=1800)


def table(mid, name):
    return door("table", mid, _name(name))


def odds(mid, name, box):
    return door("odds", mid, _name(name), _box(box), timeout=1800)


def mc(mid, name, box):
    return door("mc", mid, _name(name), _box(box))


def start(mid, name):
    """The Judge starts a carded version's in-sample table: {"job_id"} at once, or Refused (a twin, too few trades)."""
    return door("start", mid, _name(name), timeout=900)


def probe(mid, name):
    return door("probe", mid, _name(name), timeout=900)


def check(mid, name):
    """The code check of a version whose table is done: {"name", "passed", "failed": [line ids]}."""
    return door("check", mid, _name(name), timeout=900)


CARD_CAP = 3000


def card_example(mid, base=None):
    """The exact blueprint_card args (name, card, settings) of the base version, or else of this mission's newest accepted card
    (its newest card row); read-only from its spec.json. None when there is none."""
    name = base or next((r.get("ref") for r in reversed(ledger(mid)) if r.get("kind") == "card" and r.get("ref")), None)
    sp = idea_spec(name) if name else None
    if not isinstance(sp, dict) or not sp.get("card"):
        return None
    text = json.dumps({"name": sp.get("name") or name, "card": sp["card"], "settings": sp.get("run") or {}})
    return text if len(text) <= CARD_CAP else None  # a cut example is broken json and would teach the wrong shape


# ---- the brief file and the mission's files in Homebase

def _hdir(mid):
    return config.hb_missions() / str(int(mid))


def _write_json(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2))
    os.replace(tmp, p)


def write_brief(mid, brief):
    if "drafts" in brief:
        raise Refused("drafts are off for missions (a draft can read the test months)")
    if set(brief) - BRIEF_KEYS:
        raise Refused(f"a brief holds only {sorted(BRIEF_KEYS)}")
    _write_json(_hdir(mid) / "brief.json", brief)


def unapprove(mid):
    p = _hdir(mid) / "brief.json"
    try:
        b = json.loads(p.read_text())
    except (OSError, ValueError):
        return  # no brief on file: nothing is approved
    b["approved"] = False
    _write_json(p, b)


def set_test_months(mid, tm):
    """Rewrite test_months in the brief on file (no brief yet: nothing to rewrite)."""
    p = _hdir(mid) / "brief.json"
    try:
        b = json.loads(p.read_text())
    except (OSError, ValueError):
        return
    b["test_months"] = tm
    _write_json(p, b)


def _lines(p):
    out = []
    try:
        txt = p.read_text()
    except OSError:
        return out
    for line in txt.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue  # torn line
        if isinstance(row, dict):
            out.append(row)
    return out


def ledger(mid):
    return _lines(_hdir(mid) / "ledger.jsonl")


def _job_json(job_id):
    try:
        return json.loads((config.ideas_root() / "_jobs" / _name(str(job_id)) / "job.json").read_text())
    except (OSError, ValueError, Refused):
        return {}


def made(mid, name):
    """The newest 'wf' row of that name and the job of it: the nearest job row before that wf row (the connector records a
    call's job first) whose job.json says it is the wf run of this name; any other job row is skipped."""
    rows = ledger(mid)
    i = max((k for k, r in enumerate(rows) if r.get("kind") == "wf" and r.get("ref") == name), default=None)
    if i is None:
        return None
    job = None
    for r in reversed(rows[:i]):
        if r.get("kind") == "wf":
            break
        if r.get("kind") == "job":
            j = _job_json(r["ref"])
            if j.get("command") == "wf run" and j.get("name") == name:
                job = r["ref"]
                break
    return {"wf": True, "job_id": job}


def family_of(name):
    p = config.ideas_root() / _name(name)
    for f, get in (("spec.json", lambda d: d.get("run", {}).get("family")), ("idea.json", lambda d: d.get("family"))):
        try:
            fam = get(json.loads((p / f).read_text()))
        except (OSError, ValueError, AttributeError):
            continue
        if fam:
            return fam
    return None


def idea_spec(name):
    """A version's saved settings (its spec.json), read-only; None when there is none."""
    try:
        return json.loads((config.ideas_root() / _name(name) / "spec.json").read_text())
    except (OSError, ValueError):
        return None


def card(mid, name):
    """The Judge's report card of a version's finished in-sample table: {"line", "text", "data"} (the owner's score)."""
    return door("card", mid, _name(name))


def job(job_id):
    d = config.ideas_root() / "_jobs" / _name(str(job_id))

    def load():
        try:
            return json.loads((d / "job.json").read_text())
        except (OSError, ValueError):
            raise Refused(f"no job {job_id}") from None
    j = load()
    done = j.get("state") in ("done", "error")
    if not done and j.get("pid") and not _alive(j["pid"]):  # no pid field: left as job.json says
        j = load()  # it may have finished between the read and the check
        done = j.get("state") in ("done", "error")
        if not done:
            return {"done": True, "ok": False, "said": "the job's process is gone", "progress": None}
    ok, said = False, j.get("progress") or ""
    if done:
        try:
            r = json.loads((d / "result.json").read_text())
            ok, said = bool(r.get("ok")), r.get("text") or r.get("error") or ""
        except (OSError, ValueError):
            said = "the job ended without a result"
    m = re.search(r"(\d+)\s*(?:/|of)\s*(\d+)", j.get("progress") or "")
    return {"done": done, "ok": ok and done, "said": said, "progress": [int(m[1]), int(m[2])] if m else None}


def slots():
    """Homebase's own slots.status(), asked once (read-only)."""
    try:
        r = subprocess.run([str(config.hb_python()), "-c",
                            "import json;from homebase.backtest import slots;print(json.dumps(slots.status()))"],
                           capture_output=True, text=True, timeout=60, cwd=config.homebase(), stdin=subprocess.DEVNULL)
        s = json.loads(r.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired) as e:
        raise Down("Homebase's slots cannot be read") from e
    return {"off": True} if s.get("off") else {"cap": s.get("cap"), "running": s.get("running")}


def health():
    try:
        with socket.create_connection(("127.0.0.1", config.chart_port()), timeout=1):
            chart = True
    except OSError:
        chart = False
    door_ok = config.judge().is_file() and os.access(config.judge(), os.X_OK)
    try:
        v = subprocess.run([str(config.claude_bin()), "--version"], capture_output=True, text=True, timeout=20,
                           stdin=subprocess.DEVNULL).stdout.split()
        claude = v[0] if v else None
    except (OSError, config.ConfigError, subprocess.TimeoutExpired):
        claude = None
    return {"chart_service": chart, "door": door_ok, "claude": claude}


# ---- owner-only: never used to build worker text (the engine never imports these three)

def owner_read(mid, name):
    try:
        return json.loads((_hdir(mid) / "reads" / f"{_name(name)}.json").read_text())
    except (OSError, ValueError):
        return None


def owner_refused(mid):
    return _lines(_hdir(mid) / "refused.jsonl")[::-1]


def _alive(pid):
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return False  # a malformed pid is no process
    p = _children.get(pid)
    if p is not None:
        return p.poll() is None  # our own child: poll reaps it
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        pass
    return True


def _paths(mid, name):
    d = store.mdir(mid)
    return d / f"read_{_name(name)}.json", d / f"read_{name}.pid"


def _lstart(pid):
    """When the process started (ps lstart), or '' if it cannot be read."""
    try:
        return subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _ours(pid, pidf):
    """Alive AND the same process the pid file was written for (a pid reused after a reboot is not). A file with no
    start time (older, or written by hand) is trusted as it was."""
    if not _alive(pid):
        return False
    if pid in _children:
        return True
    try:
        _, _, started = pidf.read_text().partition(" ")
    except OSError:
        return False
    return not started.strip() or _lstart(pid) == started.strip()


def _pid(pidf):
    try:
        return int((pidf.read_text() or "0").split()[0])
    except (OSError, ValueError):
        return 0


def start_read(mid, name, box, said=None):
    """One read of a version, ever: the pid file is claimed (O_EXCL) before anything spawns, and an existing claim or
    result means start nothing (the version is spent)."""
    out, pidf = _paths(mid, name)
    box = _box(box)
    if out.exists():
        return _pid(pidf)
    try:
        os.close(os.open(pidf, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        return _pid(pidf)
    cmd = f"{shlex.quote(str(config.judge()))} read {int(mid)} {shlex.quote(name)} {shlex.quote(box)}" \
          + (f" --said {shlex.quote(said)}" if said else "")
    try:
        p = subprocess.Popen(["/bin/sh", "-c", f"{cmd} > {shlex.quote(str(out))}.tmp 2>/dev/null; "
                              f"mv {shlex.quote(str(out))}.tmp {shlex.quote(str(out))}"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
    except OSError as e:
        pidf.unlink(missing_ok=True)  # nothing started: the read can be tried again
        raise Down(f"the read could not be started ({e})") from e
    _children[p.pid] = p
    pidf.write_text(f"{p.pid} {_lstart(p.pid)}".strip())
    return p.pid


def _answer(out):
    try:
        return json.loads(out.read_text())
    except ValueError:
        return {"refused": STOPPED}
    except OSError:
        return None


def read_result(mid, name):
    out, pidf = _paths(mid, name)
    if (r := _answer(out)) is not None:
        return r
    if not pidf.exists():
        return None  # never started
    pid = _pid(pidf)
    if pid == 0:  # claimed, pid not written yet; a claim that stays empty means the app died before the spawn
        return None if time.time() - pidf.stat().st_mtime < 10 else {"refused": STOPPED}
    if _ours(pid, pidf):
        return None
    return _answer(out) or {"refused": STOPPED}  # it may have finished between the read and the check

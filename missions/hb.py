"""The Homebase adapter: the only module that knows how to call into Homebase (the Judge's door, the brief file, jobs,
slots, the owner's files). Reads Homebase's files; never writes any but the brief."""
import json
import os
import re
import shlex
import socket
import subprocess

from . import config, store

OK_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
BRIEF_KEYS = {"approved", "owner_said", "test_months", "goal"}
STOPPED = "the read stopped; the owner has the details"


class Refused(Exception):
    pass


class Down(Exception):
    pass


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
        raise Down(f"the Judge's door took more than {timeout} s") from e
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
    return door("gate", mid, name, box, timeout=1800)


def table(mid, name):
    return door("table", mid, name)


def odds(mid, name, box):
    return door("odds", mid, name, box, timeout=1800)


def mc(mid, name, box):
    return door("mc", mid, name, box)


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


def made(mid, name):
    """The newest 'wf' row of that name and the job row Homebase wrote just before it (the connector records a call's job
    before its wf row), else None."""
    rows = ledger(mid)
    i = max((k for k, r in enumerate(rows) if r.get("kind") == "wf" and r.get("ref") == name), default=None)
    if i is None:
        return None
    job = None
    for r in reversed(rows[:i]):
        if r.get("kind") == "wf":
            break
        if r.get("kind") == "job":
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


def job(job_id):
    d = config.ideas_root() / "_jobs" / _name(str(job_id))
    try:
        j = json.loads((d / "job.json").read_text())
    except (OSError, ValueError):
        raise Refused(f"no job {job_id}") from None
    done = j.get("state") in ("done", "error")
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
        os.waitpid(pid, os.WNOHANG)  # reap our own finished child, or it looks alive
    except OSError:
        pass
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


def start_read(mid, name, box, said=None):
    out, pidf = _paths(mid, name)
    if pidf.exists():
        try:
            old = int(pidf.read_text())
        except ValueError:
            old = 0
        if old and not out.exists() and _alive(old):
            return old  # one read of a version at a time
    cmd = f"{shlex.quote(str(config.judge()))} read {int(mid)} {shlex.quote(name)} {shlex.quote(str(box))}" \
          + (f" --said {shlex.quote(said)}" if said else "")
    p = subprocess.Popen(["/bin/sh", "-c", f"{cmd} > {shlex.quote(str(out))}.tmp 2>/dev/null; "
                          f"mv {shlex.quote(str(out))}.tmp {shlex.quote(str(out))}"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    pidf.write_text(str(p.pid))
    return p.pid


def read_result(mid, name):
    out, pidf = _paths(mid, name)
    try:
        return json.loads(out.read_text())
    except ValueError:
        return {"refused": STOPPED}
    except OSError:
        pass
    try:
        pid = int(pidf.read_text())
    except (OSError, ValueError):
        return None  # never started
    return None if _alive(pid) else {"refused": STOPPED}

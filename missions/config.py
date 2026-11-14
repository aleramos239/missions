import json
import os
import shutil
from pathlib import Path

PORT = 8860


class ConfigError(Exception):
    pass


def _env(name, default):
    return Path(os.environ.get(name) or default).expanduser()


def home() -> Path:
    return _env("MISSIONS_HOME", "~/.missions")


def homebase() -> Path:
    return _env("MISSIONS_HOMEBASE", "~/ramos-quant-homebase")


def judge() -> Path:
    return _env("MISSIONS_JUDGE", homebase() / "research/edge-library/missions/judge")


def ideas_root() -> Path:
    return _env("HOMEBASE_IDEAS_ROOT", "~/.homebase/ideas")


def hb_python() -> Path:
    return _env("MISSIONS_HB_PYTHON", homebase() / ".venv/bin/python")


def chart_port() -> int:
    return int(os.environ.get("MISSIONS_CHART_PORT") or 8852)


def hb_missions() -> Path:
    return _env("HOMEBASE_MISSIONS", "~/.homebase/missions")


def vault() -> Path:
    return _env("MISSIONS_VAULT", "~/Obsidian/Vault")


def work_dir(mid, role) -> Path:
    d = home() / "_work" / str(mid) / role
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings() -> dict:
    try:
        return json.loads((home() / "settings.json").read_text())
    except (OSError, ValueError):
        return {}


def save_settings(d) -> None:
    home().mkdir(parents=True, exist_ok=True)
    p = home() / "settings.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2))
    os.replace(tmp, p)


def _ver(p: Path):
    return tuple(int(x) if x.isdigit() else 0 for x in p.name.split("."))


def claude_bin() -> Path:
    if settings().get("claude"):
        return Path(settings()["claude"])
    root = _env("MISSIONS_CLAUDE_ROOT", "~/Library/Application Support/Claude/claude-code")
    found = [b for v in sorted(root.glob("*"), key=_ver, reverse=True)
             for b in sorted(v.glob("*/claude.app/Contents/MacOS/claude"))]
    if found:
        return found[0]
    if w := shutil.which("claude"):
        return Path(w)
    raise ConfigError("claude not found: set \"claude\" in settings.json")

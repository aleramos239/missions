import pytest


@pytest.fixture(autouse=True)
def _homes(tmp_path, monkeypatch):
    monkeypatch.setenv("MISSIONS_HOME", str(tmp_path / "missions_home"))
    monkeypatch.setenv("HOMEBASE_MISSIONS", str(tmp_path / "hb_missions"))
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "vault"))
    monkeypatch.setenv("MISSIONS_CLAUDE_ROOT", str(tmp_path / "no_claude_root"))


@pytest.fixture(autouse=True)
def _no_side_effects(request, monkeypatch):
    """No test sleeps the Mac or shows a notification (tests/test_system.py patches Popen/urlopen itself)."""
    if request.module.__name__.endswith("test_system"):
        return
    from missions import system
    monkeypatch.setattr(system, "awake", lambda on: None)
    monkeypatch.setattr(system, "alert", lambda mid, kind: None)

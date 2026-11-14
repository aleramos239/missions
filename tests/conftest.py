import pytest


@pytest.fixture(autouse=True)
def _homes(tmp_path, monkeypatch):
    monkeypatch.setenv("MISSIONS_HOME", str(tmp_path / "missions_home"))
    monkeypatch.setenv("HOMEBASE_MISSIONS", str(tmp_path / "hb_missions"))
    monkeypatch.setenv("MISSIONS_CLAUDE_ROOT", str(tmp_path / "no_claude_root"))

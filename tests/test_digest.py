from missions import digest


def test_digest_keeps_name_and_verdict(tmp_path, monkeypatch):
    d = tmp_path / "v/30-Projects/Onyx-Trading"
    d.mkdir(parents=True)
    (d / "what-lives-what-is-dead-2026-11-07.md").write_text(
        "| Strategy | Verdict | Note |\n|---|---|---|\n"
        "| nq_fvg15_va10 | alive | test months +4.1 pts, $31,400 net |\n- gap_fade: dead after 12 tries\n- no word here 99\n")
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "v"))
    t = digest.digest()
    assert "nq_fvg15_va10: alive" in t and "gap_fade: dead" in t
    assert "4.1" not in t and "31,400" not in t and "99" not in t and "tries" not in t


def test_missing_vault(tmp_path, monkeypatch):
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "none"))
    assert "No notes found" in digest.digest()

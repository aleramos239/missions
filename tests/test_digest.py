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


def _vault(tmp_path, monkeypatch, text):
    d = tmp_path / "v/30-Projects/Onyx-Trading"
    d.mkdir(parents=True)
    (d / "dead-families.md").write_text(text)
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "v"))
    return d


def test_only_real_rows_count(tmp_path, monkeypatch):
    _vault(tmp_path, monkeypatch, "| 4.1 | alive |\n| $31,400 | dead |\n## Dead families\n"
           "The old fvg family is dead and buried.\n| real_one | dead |\n")
    t = digest.digest()
    assert "real_one: dead" in t
    for bad in ("4.1", "31,400", "Dead families", "The", "fvg"):
        assert bad not in t.split("The owner's")[0]


def test_symlinked_note_refused(tmp_path, monkeypatch):
    d = _vault(tmp_path, monkeypatch, "")
    (d / "dead-families.md").unlink()
    plant = d / "findings.md"
    plant.write_text("| leak_strat | alive | 77777 |\n")
    (d / "dead-families.md").symlink_to(plant)
    t = digest.digest()
    assert "leak_strat" not in t and "77777" not in t and "No notes found" in t


def _outside(tmp_path):
    o = tmp_path / "outside/Onyx-Trading"
    o.mkdir(parents=True)
    (o / "dead-families.md").write_text("| leak_strat | alive | 77777 |\n")
    return o


def test_symlinked_project_folder_refused(tmp_path, monkeypatch):
    o = _outside(tmp_path)
    (tmp_path / "v/30-Projects").mkdir(parents=True)
    (tmp_path / "v/30-Projects/Onyx-Trading").symlink_to(o)
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "v"))
    t = digest.digest()
    assert "leak" not in t and "No notes found" in t


def test_symlinked_30_projects_refused(tmp_path, monkeypatch):
    o = _outside(tmp_path)
    (tmp_path / "v").mkdir()
    (tmp_path / "v/30-Projects").symlink_to(o.parent)
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "v"))
    t = digest.digest()
    assert "leak" not in t and "No notes found" in t


def test_symlinked_vault_root_works(tmp_path, monkeypatch):
    d = _vault(tmp_path, monkeypatch, "| ok_one | dead |\n")
    (tmp_path / "link").symlink_to(tmp_path / "v")
    monkeypatch.setenv("MISSIONS_VAULT", str(tmp_path / "link"))
    assert "ok_one: dead" in digest.digest()

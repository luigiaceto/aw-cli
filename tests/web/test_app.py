from aw_web.web.app import main, reset_database


def test_reset_database_removes_sqlite_files(tmp_path, monkeypatch):
    db_path = tmp_path / "web.sqlite3"
    db_path.write_text("db")
    tmp_path.joinpath("web.sqlite3-wal").write_text("wal")
    tmp_path.joinpath("web.sqlite3-shm").write_text("shm")
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    removed = reset_database(db_path)

    assert removed
    assert not db_path.exists()
    assert not tmp_path.joinpath("web.sqlite3-wal").exists()
    assert not tmp_path.joinpath("web.sqlite3-shm").exists()


def test_reset_database_can_be_cancelled(tmp_path, monkeypatch):
    db_path = tmp_path / "web.sqlite3"
    db_path.write_text("db")
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    removed = reset_database(db_path)

    assert not removed
    assert db_path.exists()


def test_main_reset_db_uses_home_database_path(tmp_path, monkeypatch):
    db_dir = tmp_path / ".aw-web"
    db_dir.mkdir()
    db_path = db_dir / "web.sqlite3"
    db_path.write_text("db")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    main(["--reset-db"])

    assert not db_path.exists()

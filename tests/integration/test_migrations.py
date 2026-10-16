from flight_tracker.db import MIGRATIONS_DIR, connect, migrate


def test_migrations_apply_once_on_a_file_database(tmp_path):
    path = tmp_path / "nested" / "flight-tracker.db"
    conn = connect(str(path))

    first = migrate(conn)
    second = migrate(conn)

    assert first == sorted(int(script.name.split("_", 1)[0]) for script in MIGRATIONS_DIR.glob("*.sql"))
    assert second == []
    assert path.exists()
    conn.close()


def test_schema_has_expected_tables_and_wal_mode(tmp_path):
    conn = connect(str(tmp_path / "flight-tracker.db"))
    migrate(conn)

    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

    assert {"app_user", "watch", "price_snapshot", "check_run", "search_request", "schema_version"} <= tables
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    conn.close()


def test_data_survives_reconnect(tmp_path):
    path = str(tmp_path / "flight-tracker.db")
    conn = connect(path)
    migrate(conn)
    conn.execute(
        "INSERT INTO app_user (chat_id, name, status, created_at) VALUES (1, 'Owner', 'APPROVED', '2026-10-16')"
    )
    conn.close()

    reopened = connect(path)
    migrate(reopened)

    assert reopened.execute("SELECT name FROM app_user WHERE chat_id = 1").fetchone()["name"] == "Owner"
    reopened.close()

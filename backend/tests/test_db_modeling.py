from pathlib import Path

from backend.app.db import (
    ensure_database,
    fetch_dashboard_projection,
    fetch_parent_progress_projection,
    get_connection,
    insert_demo_progress_records,
    seed_core_records,
)


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def test_schema_can_be_created_from_scratch(tmp_path: Path) -> None:
    db_path = tmp_path / "ela-test.sqlite3"
    ensure_database(db_path)

    with get_connection(db_path) as connection:
        expected_tables = [
            "users",
            "child_profiles",
            "activity_sessions",
            "responses",
            "scores",
            "progress_snapshots",
            "reward_state",
            "chat_messages",
        ]
        for table_name in expected_tables:
            assert _table_exists(connection, table_name)


def test_seed_data_can_be_inserted_successfully(tmp_path: Path) -> None:
    db_path = tmp_path / "ela-test.sqlite3"
    ensure_database(db_path)

    with get_connection(db_path) as connection:
        ids = seed_core_records(connection)
        demo = insert_demo_progress_records(connection, ids["user_id"], ids["child_profile_id"])

        session_count = connection.execute(
            "SELECT COUNT(*) AS count FROM activity_sessions WHERE id = ?",
            (demo["session_id"],),
        ).fetchone()["count"]
        response_count = connection.execute(
            "SELECT COUNT(*) AS count FROM responses WHERE session_id = ?",
            (demo["session_id"],),
        ).fetchone()["count"]
        score_count = connection.execute(
            "SELECT COUNT(*) AS count FROM scores WHERE session_id = ?",
            (demo["session_id"],),
        ).fetchone()["count"]

    assert session_count == 1
    assert response_count >= 2
    assert score_count == 1


def test_records_support_dashboard_and_progress_queries(tmp_path: Path) -> None:
    db_path = tmp_path / "ela-test.sqlite3"
    ensure_database(db_path)

    with get_connection(db_path) as connection:
        ids = seed_core_records(connection)
        insert_demo_progress_records(connection, ids["user_id"], ids["child_profile_id"])

        dashboard = fetch_dashboard_projection(connection, ids["user_id"])
        parent_progress = fetch_parent_progress_projection(connection, ids["child_profile_id"])

    assert dashboard["username"] == "user"
    assert dashboard["stars"] == 3
    assert float(dashboard["average_score_percent"]) >= 0

    assert parent_progress["display_name"] == "Explorer Kid"
    assert int(parent_progress["session_count"]) >= 1
    assert float(parent_progress["avg_score_percent"]) >= 0


def test_existing_database_reuse_path_keeps_data(tmp_path: Path) -> None:
    db_path = tmp_path / "ela-test.sqlite3"
    ensure_database(db_path)

    with get_connection(db_path) as connection:
        ids = seed_core_records(connection)
        insert_demo_progress_records(connection, ids["user_id"], ids["child_profile_id"])
        before_count = connection.execute("SELECT COUNT(*) AS count FROM activity_sessions").fetchone()["count"]

    # Simulate app restart path.
    ensure_database(db_path)

    with get_connection(db_path) as connection:
        after_count = connection.execute("SELECT COUNT(*) AS count FROM activity_sessions").fetchone()["count"]
        user_count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        profile_count = connection.execute("SELECT COUNT(*) AS count FROM child_profiles").fetchone()["count"]

    assert before_count == after_count
    assert user_count == 1
    assert profile_count == 1

import sqlite3
from dataclasses import replace

from flight_tracker.domain import CheckRun, CheckRunStatus


class CheckRunRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def start(self, run: CheckRun) -> CheckRun:
        cursor = self._conn.execute(
            "INSERT INTO check_run (started_at, status) VALUES (?, ?)",
            (run.started_at.isoformat(), run.status),
        )
        return replace(run, id=cursor.lastrowid)

    def recent_statuses(self, limit: int) -> list[CheckRunStatus]:
        rows = self._conn.execute(
            "SELECT status FROM check_run WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [CheckRunStatus(row["status"]) for row in rows]

    def finish(self, run: CheckRun) -> None:
        self._conn.execute(
            "UPDATE check_run SET finished_at = ?, status = ?, routes_total = ?, routes_failed = ?, error = ? "
            "WHERE id = ?",
            (
                run.finished_at.isoformat() if run.finished_at else None,
                run.status,
                run.routes_total,
                run.routes_failed,
                run.error,
                run.id,
            ),
        )

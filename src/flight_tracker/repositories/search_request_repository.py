import sqlite3
from datetime import datetime


class SearchRequestRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, chat_id: int, requested_at: datetime) -> None:
        self._conn.execute(
            "INSERT INTO search_request (chat_id, requested_at) VALUES (?, ?)",
            (chat_id, requested_at.isoformat()),
        )

    def count_since(self, chat_id: int, since: datetime) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS total FROM search_request WHERE chat_id = ? AND requested_at >= ?",
            (chat_id, since.isoformat()),
        ).fetchone()
        return row["total"]

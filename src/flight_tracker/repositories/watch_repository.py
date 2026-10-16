import sqlite3
from dataclasses import replace

from flight_tracker.domain import Watch, WatchStatus


class WatchRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def insert(self, watch: Watch) -> Watch:
        cursor = self._conn.execute(
            "INSERT INTO watch (chat_id, trip_type, origins, destinations, origin_label, destination_label, "
            "departure_date, return_date, target_price, status, last_notified_price, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                watch.chat_id,
                watch.trip_type,
                ",".join(watch.origins),
                ",".join(watch.destinations),
                watch.origin_label,
                watch.destination_label,
                watch.departure_date.isoformat(),
                watch.return_date.isoformat() if watch.return_date else None,
                str(watch.target_price),
                watch.status,
                str(watch.last_notified_price) if watch.last_notified_price is not None else None,
                watch.created_at.isoformat(),
            ),
        )
        return replace(watch, id=cursor.lastrowid)

    def count_active(self, chat_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS total FROM watch WHERE chat_id = ? AND status = ?",
            (chat_id, WatchStatus.ACTIVE),
        ).fetchone()
        return row["total"]

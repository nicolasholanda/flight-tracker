import sqlite3
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from flight_tracker.domain import TripType, Watch, WatchStatus


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

    def find(self, watch_id: int) -> Watch | None:
        row = self._conn.execute("SELECT * FROM watch WHERE id = ?", (watch_id,)).fetchone()
        return _to_watch(row) if row else None

    def find_active_by_chat(self, chat_id: int) -> list[Watch]:
        rows = self._conn.execute(
            "SELECT * FROM watch WHERE chat_id = ? AND status = ? ORDER BY departure_date, id",
            (chat_id, WatchStatus.ACTIVE),
        ).fetchall()
        return [_to_watch(row) for row in rows]

    def update_status(self, watch_id: int, status: WatchStatus) -> None:
        self._conn.execute("UPDATE watch SET status = ? WHERE id = ?", (status, watch_id))


def _to_watch(row: sqlite3.Row) -> Watch:
    return Watch(
        id=row["id"],
        chat_id=row["chat_id"],
        trip_type=TripType(row["trip_type"]),
        origins=tuple(row["origins"].split(",")),
        destinations=tuple(row["destinations"].split(",")),
        origin_label=row["origin_label"],
        destination_label=row["destination_label"],
        departure_date=date.fromisoformat(row["departure_date"]),
        return_date=date.fromisoformat(row["return_date"]) if row["return_date"] else None,
        target_price=Decimal(row["target_price"]),
        status=WatchStatus(row["status"]),
        last_notified_price=Decimal(row["last_notified_price"]) if row["last_notified_price"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
    )

import sqlite3
from datetime import datetime

from flight_tracker.domain import AppUser, UserStatus


class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def find(self, chat_id: int) -> AppUser | None:
        row = self._conn.execute("SELECT * FROM app_user WHERE chat_id = ?", (chat_id,)).fetchone()
        return _to_user(row) if row else None

    def list_all(self) -> list[AppUser]:
        rows = self._conn.execute("SELECT * FROM app_user ORDER BY created_at").fetchall()
        return [_to_user(row) for row in rows]

    def insert_if_absent(self, user: AppUser) -> bool:
        cursor = self._conn.execute(
            "INSERT OR IGNORE INTO app_user (chat_id, name, username, status, created_at, decided_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user.chat_id,
                user.name,
                user.username,
                user.status,
                user.created_at.isoformat(),
                user.decided_at.isoformat() if user.decided_at else None,
            ),
        )
        return cursor.rowcount == 1

    def update_status(self, chat_id: int, status: UserStatus, decided_at: datetime) -> None:
        self._conn.execute(
            "UPDATE app_user SET status = ?, decided_at = ? WHERE chat_id = ?",
            (status, decided_at.isoformat(), chat_id),
        )


def _to_user(row: sqlite3.Row) -> AppUser:
    return AppUser(
        chat_id=row["chat_id"],
        name=row["name"],
        username=row["username"],
        status=UserStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        decided_at=datetime.fromisoformat(row["decided_at"]) if row["decided_at"] else None,
    )

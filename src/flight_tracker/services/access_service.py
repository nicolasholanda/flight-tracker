from collections.abc import Callable
from datetime import datetime

from flight_tracker.domain import AppUser, UserStatus
from flight_tracker.repositories.user_repository import UserRepository


class AccessService:
    def __init__(self, users: UserRepository, owner_chat_id: int, now: Callable[[], datetime] = datetime.now):
        self._users = users
        self._owner_chat_id = owner_chat_id
        self._now = now

    def ensure_owner(self) -> None:
        owner = AppUser(self._owner_chat_id, "Owner", None, UserStatus.APPROVED, self._now(), self._now())
        if not self._users.insert_if_absent(owner):
            self._users.update_status(self._owner_chat_id, UserStatus.APPROVED, self._now())

    def is_owner(self, chat_id: int) -> bool:
        return chat_id == self._owner_chat_id

    def is_allowed(self, chat_id: int) -> bool:
        if self.is_owner(chat_id):
            return True
        user = self._users.find(chat_id)
        return user is not None and user.status == UserStatus.APPROVED

    def request_access(self, chat_id: int, name: str, username: str | None) -> AppUser | None:
        user = AppUser(chat_id, name, username, UserStatus.PENDING, self._now())
        return user if self._users.insert_if_absent(user) else None

    def approve(self, chat_id: int) -> AppUser | None:
        return self._decide(chat_id, UserStatus.APPROVED, {UserStatus.PENDING, UserStatus.DENIED, UserStatus.REVOKED})

    def deny(self, chat_id: int) -> AppUser | None:
        return self._decide(chat_id, UserStatus.DENIED, {UserStatus.PENDING})

    def revoke(self, chat_id: int) -> AppUser | None:
        return self._decide(chat_id, UserStatus.REVOKED, {UserStatus.APPROVED})

    def list_users(self) -> list[AppUser]:
        return [user for user in self._users.list_all() if not self.is_owner(user.chat_id)]

    def _decide(self, chat_id: int, status: UserStatus, allowed_from: set[UserStatus]) -> AppUser | None:
        if self.is_owner(chat_id):
            return None
        user = self._users.find(chat_id)
        if user is None or user.status not in allowed_from:
            return None
        self._users.update_status(chat_id, status, self._now())
        return self._users.find(chat_id)

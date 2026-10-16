from datetime import date, datetime
from decimal import Decimal

import pytest

from flight_tracker.db import connect, migrate
from flight_tracker.domain import AppUser, TripType, UserStatus, Watch
from flight_tracker.repositories.user_repository import UserRepository

OWNER_ID = 1


class Clock:
    def __init__(self, start: datetime):
        self.current = start

    def __call__(self) -> datetime:
        return self.current


@pytest.fixture
def conn():
    connection = connect(":memory:")
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def clock() -> Clock:
    return Clock(datetime(2026, 10, 16, 12, 0))


@pytest.fixture
def approved_user(conn):
    def create(chat_id: int, status: UserStatus = UserStatus.APPROVED) -> int:
        UserRepository(conn).insert_if_absent(AppUser(chat_id, f"User {chat_id}", None, status, datetime(2026, 10, 1)))
        return chat_id

    return create


def make_watch(
    chat_id: int = OWNER_ID,
    target_price: str = "1500",
    last_notified_price: str | None = None,
    destinations: tuple[str, ...] = ("GIG", "SDU"),
    departure_date: date = date(2026, 11, 25),
    return_date: date | None = None,
) -> Watch:
    return Watch(
        chat_id=chat_id,
        trip_type=TripType.ONE_WAY if return_date is None else TripType.ROUND_TRIP,
        origins=("FOR",),
        destinations=destinations,
        origin_label="Fortaleza (FOR)",
        destination_label=f"Rio de Janeiro ({', '.join(destinations)})",
        departure_date=departure_date,
        return_date=return_date,
        target_price=Decimal(target_price),
        last_notified_price=Decimal(last_notified_price) if last_notified_price else None,
    )

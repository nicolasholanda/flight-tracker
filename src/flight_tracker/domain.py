from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from itertools import product


class TripType(StrEnum):
    ONE_WAY = "one-way"
    ROUND_TRIP = "round-trip"


class UserStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    REVOKED = "REVOKED"


class WatchStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REMOVED = "REMOVED"


class CheckRunStatus(StrEnum):
    RUNNING = "RUNNING"
    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class AppUser:
    chat_id: int
    name: str
    username: str | None
    status: UserStatus
    created_at: datetime
    decided_at: datetime | None = None


@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    city: str
    country: str
    size: int


@dataclass(frozen=True)
class Route:
    origin: str
    destination: str
    departure_date: date
    return_date: date | None = None

    @property
    def trip_type(self) -> TripType:
        return TripType.ONE_WAY if self.return_date is None else TripType.ROUND_TRIP


@dataclass(frozen=True)
class FlightOffer:
    route: Route
    price: Decimal
    airlines: tuple[str, ...]
    departure: datetime
    arrival: datetime
    stops: int
    booking_url: str


@dataclass
class Watch:
    chat_id: int
    trip_type: TripType
    origins: tuple[str, ...]
    destinations: tuple[str, ...]
    origin_label: str
    destination_label: str
    departure_date: date
    return_date: date | None
    target_price: Decimal
    status: WatchStatus = WatchStatus.ACTIVE
    last_notified_price: Decimal | None = None
    created_at: datetime = field(default_factory=datetime.now)
    id: int | None = None

    def routes(self) -> list[Route]:
        return [
            Route(origin, destination, self.departure_date, self.return_date)
            for origin, destination in product(self.origins, self.destinations)
        ]


@dataclass(frozen=True)
class PriceSnapshot:
    route: Route
    min_price: Decimal
    airline: str
    departure: datetime
    stops: int
    checked_at: datetime
    id: int | None = None


@dataclass
class CheckRun:
    started_at: datetime
    status: CheckRunStatus = CheckRunStatus.RUNNING
    finished_at: datetime | None = None
    routes_total: int = 0
    routes_failed: int = 0
    error: str | None = None
    id: int | None = None

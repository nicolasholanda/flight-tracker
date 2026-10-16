from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from flight_tracker.db import connect, migrate
from flight_tracker.domain import CheckRunStatus, FlightOffer, Route, UserStatus, WatchStatus
from flight_tracker.providers.base import ProviderError
from flight_tracker.repositories.check_run_repository import CheckRunRepository
from flight_tracker.repositories.snapshot_repository import SnapshotRepository
from flight_tracker.repositories.user_repository import UserRepository
from flight_tracker.repositories.watch_repository import WatchRepository
from flight_tracker.services.access_service import AccessService
from flight_tracker.services.price_checker import PriceChecker
from tests.conftest import OWNER_ID, Clock, make_watch

TODAY = date(2026, 10, 16)


class FakeProvider:
    name = "fake"

    def __init__(self):
        self.prices: dict[tuple[str, str], list[str]] = {}
        self.failing: set[tuple[str, str]] = set()
        self.calls: list[Route] = []

    def search(self, route: Route) -> list[FlightOffer]:
        self.calls.append(route)
        key = (route.origin, route.destination)
        if key in self.failing:
            raise ProviderError("blocked")
        return [
            FlightOffer(
                route=route,
                price=Decimal(price),
                airlines=("LATAM",),
                departure=datetime(2026, 11, 25, 6, 0),
                arrival=datetime(2026, 11, 25, 9, 30),
                stops=0,
                booking_url=f"https://example.test/{route.origin}-{route.destination}",
            )
            for price in self.prices.get(key, [])
        ]


class FakeNotifier:
    def __init__(self):
        self.alerts: list[tuple[int, Decimal]] = []
        self.owner_messages: list[str] = []

    async def send_price_alert(self, watch, offer) -> None:
        self.alerts.append((watch.id, offer.price))

    async def send_owner_message(self, text: str) -> None:
        self.owner_messages.append(text)


@pytest.fixture
def db(tmp_path):
    conn = connect(str(tmp_path / "flight-tracker.db"))
    migrate(conn)
    AccessService(UserRepository(conn), OWNER_ID).ensure_owner()
    yield conn
    conn.close()


@pytest.fixture
def conn(db):
    return db


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
def clock():
    return Clock(datetime(2026, 10, 16, 12, 0))


@pytest.fixture
def checker_factory(db, provider, notifier, clock):
    def build(max_routes: int = 30, threshold: int = 3) -> PriceChecker:
        return PriceChecker(
            WatchRepository(db),
            SnapshotRepository(db),
            CheckRunRepository(db),
            provider,
            notifier,
            max_routes,
            0,
            lambda: TODAY,
            threshold,
            now=clock,
        )

    return build


@pytest.fixture
def watches(db):
    return WatchRepository(db)


async def test_alerts_once_then_only_on_new_low(checker_factory, watches, provider, notifier, clock):
    watch = watches.insert(make_watch(target_price="1500"))
    provider.prices = {("FOR", "GIG"): ["1400", "1800"], ("FOR", "SDU"): ["1450"]}
    checker = checker_factory()

    await checker.run()
    clock.current += timedelta(hours=1)
    await checker.run()
    provider.prices[("FOR", "SDU")] = ["1300"]
    clock.current += timedelta(hours=1)
    await checker.run()

    assert notifier.alerts == [(watch.id, Decimal("1400")), (watch.id, Decimal("1300"))]
    assert watches.find(watch.id).last_notified_price == Decimal("1300")


async def test_alerts_again_after_price_goes_above_target_and_drops_back(
    checker_factory, watches, provider, notifier, clock
):
    watch = watches.insert(make_watch(target_price="1500", destinations=("GIG",)))
    checker = checker_factory()

    for price in ["1400", "1600", "1400"]:
        provider.prices = {("FOR", "GIG"): [price]}
        await checker.run()
        clock.current += timedelta(hours=1)

    assert notifier.alerts == [(watch.id, Decimal("1400")), (watch.id, Decimal("1400"))]


async def test_shared_routes_are_searched_once(checker_factory, watches, provider, notifier, approved_user):
    approved_user(20)
    first = watches.insert(make_watch(chat_id=OWNER_ID, target_price="1500"))
    second = watches.insert(make_watch(chat_id=20, target_price="1000", destinations=("GIG",)))
    provider.prices = {("FOR", "GIG"): ["900"], ("FOR", "SDU"): ["1200"]}

    run = await checker_factory().run()

    assert run.routes_total == 2
    assert sorted((route.origin, route.destination) for route in provider.calls) == [("FOR", "GIG"), ("FOR", "SDU")]
    assert sorted(notifier.alerts) == sorted([(first.id, Decimal("900")), (second.id, Decimal("900"))])


async def test_expires_past_watches_and_skips_them(checker_factory, watches, provider):
    past = watches.insert(make_watch(departure_date=TODAY - timedelta(days=1)))
    today = watches.insert(make_watch(departure_date=TODAY, destinations=("GIG",)))

    await checker_factory().run()

    assert watches.find(past.id).status == WatchStatus.EXPIRED
    assert watches.find(today.id).status == WatchStatus.ACTIVE
    assert [route.departure_date for route in provider.calls] == [TODAY]


async def test_revoked_users_watches_are_not_checked(checker_factory, watches, provider, approved_user):
    approved_user(30, UserStatus.REVOKED)
    watches.insert(make_watch(chat_id=30))

    run = await checker_factory().run()

    assert provider.calls == []
    assert run.status == CheckRunStatus.OK


async def test_route_cap_rotates_oldest_checked_first(checker_factory, watches, provider, clock):
    watches.insert(make_watch(destinations=("GIG", "SDU")))
    provider.prices = {("FOR", "GIG"): ["2000"], ("FOR", "SDU"): ["2000"]}
    checker = checker_factory(max_routes=1)

    await checker.run()
    clock.current += timedelta(hours=1)
    await checker.run()

    assert {route.destination for route in provider.calls} == {"GIG", "SDU"}


async def test_partial_failure_still_evaluates_other_routes(checker_factory, watches, provider, notifier):
    watch = watches.insert(make_watch(target_price="1500"))
    provider.prices = {("FOR", "SDU"): ["1000"]}
    provider.failing = {("FOR", "GIG")}

    run = await checker_factory().run()

    assert run.status == CheckRunStatus.PARTIAL
    assert run.routes_failed == 1
    assert notifier.alerts == [(watch.id, Decimal("1000"))]


async def test_owner_is_warned_once_after_consecutive_failures_and_told_on_recovery(
    checker_factory, watches, provider, notifier
):
    watches.insert(make_watch(destinations=("GIG",)))
    provider.failing = {("FOR", "GIG")}
    checker = checker_factory(threshold=2)

    for _ in range(4):
        await checker.run()
    provider.failing = set()
    await checker.run()

    assert len(notifier.owner_messages) == 2
    assert notifier.owner_messages[0].startswith("⚠️")
    assert notifier.owner_messages[1].startswith("✅")


async def test_snapshots_are_recorded_for_history(checker_factory, watches, provider, db):
    watch = watches.insert(make_watch(target_price="1500"))
    provider.prices = {("FOR", "GIG"): ["1700", "1650"], ("FOR", "SDU"): ["1900"]}

    await checker_factory().run()

    snapshots = SnapshotRepository(db).find_recent(watch.routes())
    assert sorted(snapshot.min_price for snapshot in snapshots) == [Decimal("1650"), Decimal("1900")]

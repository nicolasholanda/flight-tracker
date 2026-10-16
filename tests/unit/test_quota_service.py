from datetime import timedelta

import pytest

from flight_tracker.domain import WatchStatus
from flight_tracker.repositories.search_request_repository import SearchRequestRepository
from flight_tracker.repositories.watch_repository import WatchRepository
from flight_tracker.services.quota_service import QuotaService
from tests.conftest import make_watch


@pytest.fixture
def quota(conn, clock, approved_user):
    approved_user(10)
    approved_user(20)
    return QuotaService(SearchRequestRepository(conn), WatchRepository(conn), 3, 2, now=clock)


def test_searches_are_limited_per_hour(quota):
    assert [quota.try_consume_search(10) for _ in range(4)] == [True, True, True, False]


def test_search_limit_is_per_user(quota):
    for _ in range(3):
        quota.try_consume_search(10)

    assert quota.try_consume_search(20)


def test_search_limit_frees_up_after_an_hour(quota, clock):
    for _ in range(3):
        quota.try_consume_search(10)
    clock.current += timedelta(hours=1, seconds=1)

    assert quota.try_consume_search(10)


def test_denied_search_is_not_counted(quota, clock):
    for _ in range(5):
        quota.try_consume_search(10)
    clock.current += timedelta(hours=1, seconds=1)

    assert [quota.try_consume_search(10) for _ in range(4)] == [True, True, True, False]


def test_active_watch_limit(conn, quota):
    watches = WatchRepository(conn)
    first = watches.insert(make_watch(chat_id=10))
    watches.insert(make_watch(chat_id=10))

    assert not quota.can_create_watch(10)
    assert quota.can_create_watch(20)

    watches.update_status(first.id, WatchStatus.REMOVED)

    assert quota.can_create_watch(10)

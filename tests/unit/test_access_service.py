import pytest

from flight_tracker.domain import UserStatus
from flight_tracker.repositories.user_repository import UserRepository
from flight_tracker.services.access_service import AccessService
from tests.conftest import OWNER_ID


@pytest.fixture
def access(conn, clock):
    service = AccessService(UserRepository(conn), OWNER_ID, now=clock)
    service.ensure_owner()
    return service


def test_owner_is_always_allowed(access):
    assert access.is_allowed(OWNER_ID)
    assert access.is_owner(OWNER_ID)


def test_unknown_user_is_not_allowed(access):
    assert not access.is_allowed(42)


def test_access_request_is_created_only_once(access):
    first = access.request_access(42, "Ana", "ana")

    assert first is not None
    assert first.status == UserStatus.PENDING
    assert access.request_access(42, "Ana", "ana") is None
    assert not access.is_allowed(42)


def test_denied_user_cannot_request_again(access):
    access.request_access(42, "Ana", None)
    access.deny(42)

    assert access.request_access(42, "Ana", None) is None
    assert not access.is_allowed(42)


def test_approve_pending_user(access):
    access.request_access(42, "Ana", None)

    user = access.approve(42)

    assert user.status == UserStatus.APPROVED
    assert user.decided_at is not None
    assert access.is_allowed(42)


def test_owner_can_reverse_denial(access):
    access.request_access(42, "Ana", None)
    access.deny(42)

    assert access.approve(42).status == UserStatus.APPROVED


def test_deny_only_applies_to_pending(access):
    access.request_access(42, "Ana", None)
    access.approve(42)

    assert access.deny(42) is None
    assert access.is_allowed(42)


def test_revoke_only_applies_to_approved(access):
    access.request_access(42, "Ana", None)

    assert access.revoke(42) is None

    access.approve(42)

    assert access.revoke(42).status == UserStatus.REVOKED
    assert not access.is_allowed(42)


def test_owner_cannot_be_denied_or_revoked(access):
    assert access.deny(OWNER_ID) is None
    assert access.revoke(OWNER_ID) is None
    assert access.is_allowed(OWNER_ID)


def test_list_users_excludes_owner(access):
    access.request_access(42, "Ana", None)

    assert [user.chat_id for user in access.list_users()] == [42]


def test_unknown_user_decisions_are_ignored(access):
    assert access.approve(999) is None
    assert access.deny(999) is None

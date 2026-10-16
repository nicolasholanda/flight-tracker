from decimal import Decimal

from flight_tracker.services.alert_evaluator import evaluate
from tests.conftest import make_watch


def test_first_price_at_target_notifies():
    decision = evaluate(make_watch(target_price="1500"), Decimal("1500"))

    assert decision.notify
    assert decision.last_notified_price == Decimal("1500")
    assert decision.changed


def test_price_above_target_without_previous_alert_does_nothing():
    decision = evaluate(make_watch(target_price="1500"), Decimal("1600"))

    assert not decision.notify
    assert not decision.changed


def test_same_price_after_alert_stays_quiet():
    decision = evaluate(make_watch(target_price="1500", last_notified_price="1200"), Decimal("1200"))

    assert not decision.notify
    assert not decision.changed


def test_higher_price_still_under_target_stays_quiet():
    decision = evaluate(make_watch(target_price="1500", last_notified_price="1200"), Decimal("1300"))

    assert not decision.notify
    assert decision.last_notified_price == Decimal("1200")


def test_new_low_notifies_again():
    decision = evaluate(make_watch(target_price="1500", last_notified_price="1200"), Decimal("1199.90"))

    assert decision.notify
    assert decision.last_notified_price == Decimal("1199.90")


def test_price_back_above_target_resets_so_next_drop_alerts():
    watch = make_watch(target_price="1500", last_notified_price="1200")

    decision = evaluate(watch, Decimal("1700"))

    assert not decision.notify
    assert decision.changed
    assert decision.last_notified_price is None


def test_no_flights_keeps_state():
    decision = evaluate(make_watch(last_notified_price="1200"), None)

    assert not decision.notify
    assert not decision.changed
    assert decision.last_notified_price == Decimal("1200")

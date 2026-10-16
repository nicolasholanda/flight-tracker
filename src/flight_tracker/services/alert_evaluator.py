from dataclasses import dataclass
from decimal import Decimal

from flight_tracker.domain import Watch


@dataclass(frozen=True)
class AlertDecision:
    notify: bool
    last_notified_price: Decimal | None
    changed: bool


def evaluate(watch: Watch, lowest_price: Decimal | None) -> AlertDecision:
    last = watch.last_notified_price
    if lowest_price is None:
        return AlertDecision(False, last, False)
    if lowest_price <= watch.target_price:
        if last is None or lowest_price < last:
            return AlertDecision(True, lowest_price, True)
        return AlertDecision(False, last, False)
    if last is not None:
        return AlertDecision(False, None, True)
    return AlertDecision(False, None, False)

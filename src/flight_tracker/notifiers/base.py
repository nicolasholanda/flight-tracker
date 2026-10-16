from typing import Protocol

from flight_tracker.domain import FlightOffer, Watch


class Notifier(Protocol):
    async def send_price_alert(self, watch: Watch, offer: FlightOffer) -> None: ...

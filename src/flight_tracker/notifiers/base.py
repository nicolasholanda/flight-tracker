from typing import Protocol

from flight_tracker.domain import FlightOffer, Watch


class Notifier(Protocol):
    async def send_price_alert(self, watch: Watch, offer: FlightOffer) -> None: ...

    async def send_owner_message(self, text: str) -> None: ...

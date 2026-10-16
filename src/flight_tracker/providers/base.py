from typing import Protocol

from flight_tracker.domain import FlightOffer, Route


class ProviderError(Exception):
    pass


class PriceProvider(Protocol):
    name: str

    def search(self, route: Route) -> list[FlightOffer]: ...

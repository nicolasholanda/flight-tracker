import asyncio
import logging
from datetime import date
from itertools import product

from flight_tracker.domain import FlightOffer, Route
from flight_tracker.providers.base import PriceProvider, ProviderError

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, provider: PriceProvider, delay_seconds: float):
        self._provider = provider
        self._delay_seconds = delay_seconds

    async def search(
        self,
        origins: tuple[str, ...],
        destinations: tuple[str, ...],
        departure_date: date,
        return_date: date | None,
    ) -> list[FlightOffer]:
        routes = [Route(o, d, departure_date, return_date) for o, d in product(origins, destinations)]
        offers: list[FlightOffer] = []
        failures = 0
        for index, route in enumerate(routes):
            if index > 0:
                await asyncio.sleep(self._delay_seconds)
            try:
                offers.extend(await asyncio.to_thread(self._provider.search, route))
            except ProviderError:
                logger.exception("Search failed for %s", route)
                failures += 1
        if routes and failures == len(routes):
            raise ProviderError("All routes failed")
        return sorted(offers, key=lambda offer: offer.price)

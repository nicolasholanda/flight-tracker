from datetime import datetime
from decimal import Decimal

from fast_flights import FlightQuery, FlightsNotFound, Passengers, create_query, get_flights

from flight_tracker.domain import FlightOffer, Route
from flight_tracker.providers.base import ProviderError


class GoogleFlightsProvider:
    name = "google_flights"

    def __init__(self, currency: str, language: str):
        self._currency = currency
        self._language = language

    def search(self, route: Route) -> list[FlightOffer]:
        legs = [FlightQuery(date=route.departure_date.isoformat(), from_airport=route.origin, to_airport=route.destination)]
        if route.return_date is not None:
            legs.append(
                FlightQuery(date=route.return_date.isoformat(), from_airport=route.destination, to_airport=route.origin)
            )
        query = create_query(
            flights=legs,
            seat="economy",
            trip=str(route.trip_type),
            passengers=Passengers(adults=1),
            language=self._language,
            currency=self._currency,
        )
        try:
            results = get_flights(query)
        except FlightsNotFound:
            return []
        except Exception as error:
            raise ProviderError(f"{route.origin}->{route.destination}: {error}") from error

        url = query.url()
        return [_to_offer(route, result, url) for result in results if result.price is not None and result.flights]


def _to_offer(route: Route, result, url: str) -> FlightOffer:
    first, last = result.flights[0], result.flights[-1]
    return FlightOffer(
        route=route,
        price=Decimal(result.price),
        airlines=tuple(result.airlines),
        departure=datetime(*first.departure.date, *first.departure.time),
        arrival=datetime(*last.arrival.date, *last.arrival.time),
        stops=len(result.flights) - 1,
        booking_url=url,
    )


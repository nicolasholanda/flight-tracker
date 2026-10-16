import os
from datetime import date, timedelta

import pytest

from flight_tracker.domain import Route
from flight_tracker.providers.google_flights import GoogleFlightsProvider

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to hit Google Flights"),
]


@pytest.fixture
def provider():
    return GoogleFlightsProvider("BRL", "pt-BR")


def test_one_way_search_returns_priced_offers(provider):
    route = Route("FOR", "GIG", date.today() + timedelta(days=45))

    offers = provider.search(route)

    assert offers
    assert all(offer.price > 0 for offer in offers)
    assert all(offer.route == route for offer in offers)
    assert offers[0].booking_url.startswith("https://www.google.com/travel/flights")


def test_round_trip_search_returns_priced_offers(provider):
    departure = date.today() + timedelta(days=45)
    route = Route("FOR", "GIG", departure, departure + timedelta(days=7))

    offers = provider.search(route)

    assert offers
    assert all(offer.departure.date() == departure for offer in offers)

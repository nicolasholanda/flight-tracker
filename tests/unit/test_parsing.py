from datetime import date
from decimal import Decimal

import pytest

from flight_tracker.bot.formatting import format_date, format_price, format_stops, parse_date, parse_price

TODAY = date(2026, 10, 16)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1500", Decimal("1500")),
        ("1.500", Decimal("1500")),
        ("1.499,90", Decimal("1499.90")),
        ("R$ 1500,50", Decimal("1500.50")),
        ("r$1.500", Decimal("1500")),
        ("1500.50", Decimal("1500.50")),
        ("1.000.000", Decimal("1000000")),
        ("1500,5", Decimal("1500.5")),
    ],
)
def test_parse_price_accepts_brazilian_and_plain_formats(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text", ["abc", "0", "-5", "", "15 00 reais", "1,2,3"])
def test_parse_price_rejects_invalid(text):
    assert parse_price(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("17/10/2026", date(2026, 10, 17)),
        ("17/10/26", date(2026, 10, 17)),
        ("17-10-2026", date(2026, 10, 17)),
        ("2026-11-25", date(2026, 11, 25)),
        ("17/10", date(2026, 10, 17)),
        ("16/10", date(2026, 10, 16)),
        ("10/10", date(2027, 10, 10)),
        ("1/2", date(2027, 2, 1)),
    ],
)
def test_parse_date_formats(text, expected):
    assert parse_date(text, TODAY) == expected


@pytest.mark.parametrize("text", ["31/02/2026", "abc", "17/13", "17 de outubro"])
def test_parse_date_rejects_invalid(text):
    assert parse_date(text, TODAY) is None


def test_format_price_uses_brazilian_grouping():
    assert format_price(Decimal("1069")) == "R$ 1.069"
    assert format_price(Decimal("12345.5")) == "R$ 12.345,50"
    assert format_price(Decimal("999.99")) == "R$ 999,99"


def test_format_date_and_stops():
    assert format_date(date(2026, 10, 17)) == "sáb. 17/10/2026"
    assert format_stops(0) == "Direto"
    assert format_stops(1) == "1 parada"
    assert format_stops(3) == "3 paradas"

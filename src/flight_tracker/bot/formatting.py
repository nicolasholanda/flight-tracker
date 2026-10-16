import re
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flight_tracker.domain import FlightOffer, Watch

WEEKDAYS = ["seg.", "ter.", "qua.", "qui.", "sex.", "sáb.", "dom."]
DATE_PATTERN = re.compile(r"^(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2}|\d{4}))?$")
ISO_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
PRICE_PATTERN = re.compile(r"^\d[\d.,]*$")


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Buscar voos", callback_data="menu:search")]])


def welcome_text(first_name: str) -> str:
    return (
        f"Olá, {escape(first_name)}! 👋 Bem-vindo ao Flight Tracker. Aqui está o que eu consigo fazer:\n\n"
        "– Procurar pelos voos mais baratos 🔎\n"
        "– Avisar quando o preço chegar no valor que você quer 🔔\n\n"
        "Podemos começar? 👇"
    )


def format_price(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"))
    integer, cents = f"{quantized:.2f}".split(".")
    grouped = f"{int(integer):,}".replace(",", ".")
    return f"R$ {grouped}" if cents == "00" else f"R$ {grouped},{cents}"


def format_date(value: date) -> str:
    return f"{WEEKDAYS[value.weekday()]} {value:%d/%m/%Y}"


def format_stops(stops: int) -> str:
    if stops == 0:
        return "Direto"
    return "1 parada" if stops == 1 else f"{stops} paradas"


def format_offer(offer: FlightOffer) -> str:
    airlines = escape(", ".join(offer.airlines)) or "—"
    arrival_day = "" if offer.arrival.date() == offer.departure.date() else f" ({offer.arrival:%d/%m})"
    return (
        f"✈️ <b>{offer.route.origin} → {offer.route.destination}</b> · {airlines}\n"
        f"🕐 {offer.departure:%H:%M} → {offer.arrival:%H:%M}{arrival_day} · {format_stops(offer.stops)}\n"
        f"💰 <b>{format_price(offer.price)}</b> · <a href=\"{escape(offer.booking_url)}\">🛒 Ver no Google Flights</a>"
    )


def format_results(
    origin_label: str,
    destination_label: str,
    departure_date: date,
    return_date: date | None,
    offers: list[FlightOffer],
    limit: int = 5,
) -> str:
    dates = format_date(departure_date) if return_date is None else f"{format_date(departure_date)} ⇄ {format_date(return_date)}"
    header = f"📍 <b>{escape(origin_label)} → {escape(destination_label)}</b>\n📅 {dates}"
    if return_date is not None:
        header += "\n<i>Preços de ida e volta</i>"
    if not offers:
        return f"{header}\n\nNenhum voo encontrado para essa data. 😕"
    body = "\n\n".join(format_offer(offer) for offer in offers[:limit])
    return f"{header}\n\n{body}"


def format_watch(watch: Watch) -> str:
    dates = format_date(watch.departure_date)
    if watch.return_date is not None:
        dates = f"{dates} ⇄ {format_date(watch.return_date)}"
    return (
        f"📍 <b>{escape(watch.origin_label)} → {escape(watch.destination_label)}</b>\n"
        f"📅 {dates}\n"
        f"🎯 Até <b>{format_price(watch.target_price)}</b>"
        + (" (ida e volta)" if watch.return_date is not None else "")
    )


def parse_price(text: str) -> Decimal | None:
    value = text.strip().upper().removeprefix("R$").strip().replace(" ", "")
    if not PRICE_PATTERN.match(value):
        return None
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif value.count(".") > 1 or (value.count(".") == 1 and len(value.rsplit(".", 1)[1]) == 3):
        value = value.replace(".", "")
    try:
        price = Decimal(value)
    except InvalidOperation:
        return None
    return price if price > 0 else None


def parse_date(text: str, today: date) -> date | None:
    value = text.strip()
    iso = ISO_PATTERN.match(value)
    try:
        if iso:
            return date(int(iso[1]), int(iso[2]), int(iso[3]))
        match = DATE_PATTERN.match(value)
        if not match:
            return None
        day, month, year = int(match[1]), int(match[2]), match[3]
        if year is None:
            candidate = date(today.year, month, day)
            return candidate if candidate >= today else date(today.year + 1, month, day)
        return date(int(year) + 2000 if len(year) == 2 else int(year), month, day)
    except ValueError:
        return None

import csv
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from flight_tracker.domain import Airport

DEFAULT_AIRPORTS_CSV = Path(__file__).resolve().parent.parent / "data" / "airports.csv"


@dataclass(frozen=True)
class CityOption:
    city: str
    label: str
    codes: tuple[str, ...]

    @property
    def display(self) -> str:
        return f"{self.city} ({', '.join(self.codes)})"


@dataclass(frozen=True)
class _Indexed:
    airport: Airport
    city: str
    name: str
    keywords: str


class CityResolver:
    def __init__(self, airports: list[Airport], home_country: str = "BR", max_options: int = 8):
        self._indexed = [
            _Indexed(airport, normalize(airport.city), normalize(airport.name), normalize(airport.keywords))
            for airport in airports
        ]
        self._by_code = {airport.code: airport for airport in airports}
        self._home_country = home_country
        self._max_options = max_options

    @classmethod
    def from_csv(cls, path: Path = DEFAULT_AIRPORTS_CSV, **kwargs) -> "CityResolver":
        with path.open(encoding="utf-8", newline="") as file:
            airports = [
                Airport(row["code"], row["name"], row["city"], row["country"], int(row["size"]), row["keywords"])
                for row in csv.DictReader(file)
            ]
        return cls(airports, **kwargs)

    def resolve(self, text: str) -> list[CityOption]:
        query = normalize(text)
        if not query:
            return []
        if len(query) == 3 and query.upper() in self._by_code:
            airport = self._by_code[query.upper()]
            return [CityOption(airport.city, self._city_label(airport), (airport.code,))]

        groups: dict[tuple[str, str], list[Airport]] = defaultdict(list)
        city_matches: set[tuple[str, str]] = set()
        for entry in self._indexed:
            by_city = _word_prefix(query, entry.city) or _word_prefix(query, entry.keywords)
            if by_city or _word_prefix(query, entry.name):
                key = (entry.city, entry.airport.country)
                groups[key].append(entry.airport)
                if by_city:
                    city_matches.add(key)

        ordered = sorted(groups.items(), key=lambda item: self._rank(query, item[0], item[1], city_matches))
        options: list[CityOption] = []
        for _, airports in ordered:
            options.extend(self._options_for(sorted(airports, key=lambda a: (-a.size, a.name))))
        return options[: self._max_options]

    def _rank(self, query: str, key: tuple[str, str], airports: list[Airport], city_matches: set) -> tuple:
        city, country = key
        return (
            city != query,
            key not in city_matches,
            not city.startswith(query),
            country != self._home_country,
            -max(airport.size for airport in airports),
            -len(airports),
            city,
        )

    def _options_for(self, airports: list[Airport]) -> list[CityOption]:
        first = airports[0]
        if len(airports) == 1:
            return [CityOption(first.city, self._city_label(first), (first.code,))]
        codes = tuple(airport.code for airport in airports)
        everything = CityOption(first.city, f"{self._city_name(first)} — todos ({', '.join(codes)})", codes)
        return [everything] + [
            CityOption(airport.city, f"{self._city_name(airport)} ({airport.code}) · {airport.name}"[:60], (airport.code,))
            for airport in airports
        ]

    def _city_label(self, airport: Airport) -> str:
        return f"{self._city_name(airport)} ({airport.code})"

    def _city_name(self, airport: Airport) -> str:
        if airport.country == self._home_country:
            return airport.city
        return f"{airport.city}, {airport.country}"


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    cleaned = "".join(char if char.isalnum() else " " for char in stripped.lower())
    return " ".join(cleaned.split())


def _word_prefix(query: str, value: str) -> bool:
    return bool(value) and f" {query}" in f" {value}"

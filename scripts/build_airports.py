import csv
import io
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OUTPUT = Path(__file__).resolve().parent.parent / "src" / "flight_tracker" / "data" / "airports.csv"
SIZES = {"large_airport": 3, "medium_airport": 2, "small_airport": 1}
LOWERCASE_WORDS = {"de", "da", "do", "das", "dos", "e", "del", "la", "las", "los"}


def read_source(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    with urllib.request.urlopen(SOURCE_URL) as response:
        return response.read().decode("utf-8")


def tidy_city(city: str) -> str:
    words = city.strip().split()
    return " ".join(
        word.lower() if index > 0 and word.lower() in LOWERCASE_WORDS else word
        for index, word in enumerate(words)
    )


def build(source: str) -> list[dict[str, str]]:
    rows = []
    for row in csv.DictReader(io.StringIO(source)):
        code = row["iata_code"].strip().upper()
        if row["scheduled_service"] != "yes" or row["type"] not in SIZES or len(code) != 3 or not row["municipality"]:
            continue
        rows.append(
            {
                "code": code,
                "name": row["name"].strip(),
                "city": tidy_city(row["municipality"]),
                "country": row["iso_country"],
                "size": str(SIZES[row["type"]]),
                "keywords": row["keywords"].strip(),
            }
        )
    return sorted(rows, key=lambda r: r["code"])


def main() -> None:
    rows = build(read_source(sys.argv[1] if len(sys.argv) > 1 else None))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["code", "name", "city", "country", "size", "keywords"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} airports to {OUTPUT}")


if __name__ == "__main__":
    main()

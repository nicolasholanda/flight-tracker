import sqlite3
from datetime import date, datetime
from decimal import Decimal

from flight_tracker.domain import PriceSnapshot, Route


class SnapshotRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, snapshot: PriceSnapshot) -> None:
        route = snapshot.route
        self._conn.execute(
            "INSERT INTO price_snapshot (origin, destination, departure_date, return_date, min_price, airline, "
            "departure, stops, checked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                route.origin,
                route.destination,
                route.departure_date.isoformat(),
                route.return_date.isoformat() if route.return_date else None,
                str(snapshot.min_price),
                snapshot.airline,
                snapshot.departure.isoformat(),
                snapshot.stops,
                snapshot.checked_at.isoformat(),
            ),
        )

    def last_checked_at(self, route: Route) -> datetime | None:
        row = self._conn.execute(
            "SELECT MAX(checked_at) AS last FROM price_snapshot "
            "WHERE origin = ? AND destination = ? AND departure_date = ? AND return_date IS ?",
            _route_params(route),
        ).fetchone()
        return datetime.fromisoformat(row["last"]) if row["last"] else None

    def find_recent(self, routes: list[Route], limit: int = 500) -> list[PriceSnapshot]:
        if not routes:
            return []
        clause = " OR ".join(
            "(origin = ? AND destination = ? AND departure_date = ? AND return_date IS ?)" for _ in routes
        )
        params = [value for route in routes for value in _route_params(route)]
        rows = self._conn.execute(
            f"SELECT * FROM price_snapshot WHERE {clause} ORDER BY checked_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [_to_snapshot(row) for row in rows]


def _to_snapshot(row: sqlite3.Row) -> PriceSnapshot:
    return PriceSnapshot(
        id=row["id"],
        route=Route(
            row["origin"],
            row["destination"],
            date.fromisoformat(row["departure_date"]),
            date.fromisoformat(row["return_date"]) if row["return_date"] else None,
        ),
        min_price=Decimal(row["min_price"]),
        airline=row["airline"],
        departure=datetime.fromisoformat(row["departure"]),
        stops=row["stops"],
        checked_at=datetime.fromisoformat(row["checked_at"]),
    )


def _route_params(route: Route) -> tuple:
    return (
        route.origin,
        route.destination,
        route.departure_date.isoformat(),
        route.return_date.isoformat() if route.return_date else None,
    )

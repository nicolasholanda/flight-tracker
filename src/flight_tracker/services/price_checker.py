import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime

from flight_tracker.domain import CheckRun, CheckRunStatus, FlightOffer, PriceSnapshot, Route, Watch
from flight_tracker.notifiers.base import Notifier
from flight_tracker.providers.base import PriceProvider, ProviderError
from flight_tracker.repositories.check_run_repository import CheckRunRepository
from flight_tracker.repositories.snapshot_repository import SnapshotRepository
from flight_tracker.repositories.watch_repository import WatchRepository
from flight_tracker.services.alert_evaluator import evaluate

logger = logging.getLogger(__name__)


class PriceChecker:
    def __init__(
        self,
        watches: WatchRepository,
        snapshots: SnapshotRepository,
        check_runs: CheckRunRepository,
        provider: PriceProvider,
        notifier: Notifier,
        max_routes_per_run: int,
        delay_seconds: float,
        today: Callable[[], date],
        now: Callable[[], datetime] = datetime.now,
    ):
        self._watches = watches
        self._snapshots = snapshots
        self._check_runs = check_runs
        self._provider = provider
        self._notifier = notifier
        self._max_routes_per_run = max_routes_per_run
        self._delay_seconds = delay_seconds
        self._today = today
        self._now = now

    async def run(self) -> CheckRun:
        run = self._check_runs.start(CheckRun(started_at=self._now()))
        try:
            expired = self._watches.expire_before(self._today())
            if expired:
                logger.info("Expired %d watches", expired)
            watches = self._watches.find_checkable()
            routes = self._select_routes(watches)
            offers, failed = await self._fetch(routes)
            await self._evaluate(watches, offers)
            run.routes_total = len(routes)
            run.routes_failed = failed
            run.status = _status(len(routes), failed)
        except Exception as error:
            logger.exception("Price check failed")
            run.status = CheckRunStatus.FAILED
            run.error = str(error)
        run.finished_at = self._now()
        self._check_runs.finish(run)
        logger.info("Check run %s: %s (%d routes, %d failed)", run.id, run.status, run.routes_total, run.routes_failed)
        return run

    def _select_routes(self, watches: list[Watch]) -> list[Route]:
        unique = list(dict.fromkeys(route for watch in watches for route in watch.routes()))
        unique.sort(key=lambda route: self._snapshots.last_checked_at(route) or datetime.min)
        if len(unique) > self._max_routes_per_run:
            logger.warning("Route cap reached: checking %d of %d routes", self._max_routes_per_run, len(unique))
        return unique[: self._max_routes_per_run]

    async def _fetch(self, routes: list[Route]) -> tuple[dict[Route, list[FlightOffer]], int]:
        offers: dict[Route, list[FlightOffer]] = {}
        failed = 0
        for index, route in enumerate(routes):
            if index > 0:
                await asyncio.sleep(self._delay_seconds)
            try:
                found = await asyncio.to_thread(self._provider.search, route)
            except ProviderError:
                logger.exception("Provider failed for %s", route)
                failed += 1
                continue
            offers[route] = found
            if found:
                cheapest = min(found, key=lambda offer: offer.price)
                self._snapshots.add(
                    PriceSnapshot(
                        route=route,
                        min_price=cheapest.price,
                        airline=", ".join(cheapest.airlines),
                        departure=cheapest.departure,
                        stops=cheapest.stops,
                        checked_at=self._now(),
                    )
                )
        return offers, failed

    async def _evaluate(self, watches: list[Watch], offers: dict[Route, list[FlightOffer]]) -> None:
        for watch in watches:
            checked = [route for route in watch.routes() if route in offers]
            if not checked:
                continue
            candidates = [offer for route in checked for offer in offers[route]]
            best = min(candidates, key=lambda offer: offer.price) if candidates else None
            decision = evaluate(watch, best.price if best else None)
            if decision.notify:
                try:
                    await self._notifier.send_price_alert(watch, best)
                except Exception:
                    logger.exception("Failed to notify watch %s", watch.id)
                    continue
            if decision.changed:
                self._watches.update_last_notified(watch.id, decision.last_notified_price)


def _status(total: int, failed: int) -> CheckRunStatus:
    if failed == 0:
        return CheckRunStatus.OK
    return CheckRunStatus.FAILED if failed == total else CheckRunStatus.PARTIAL

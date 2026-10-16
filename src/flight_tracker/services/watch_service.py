from datetime import date
from decimal import Decimal

from flight_tracker.domain import TripType, Watch, WatchStatus
from flight_tracker.repositories.watch_repository import WatchRepository
from flight_tracker.services.city_resolver import CityOption
from flight_tracker.services.quota_service import QuotaService


class WatchLimitReached(Exception):
    pass


class WatchService:
    def __init__(self, watches: WatchRepository, quota: QuotaService):
        self._watches = watches
        self._quota = quota

    def create(
        self,
        chat_id: int,
        trip_type: TripType,
        origin: CityOption,
        destination: CityOption,
        departure_date: date,
        return_date: date | None,
        target_price: Decimal,
    ) -> Watch:
        if target_price <= 0:
            raise ValueError("Target price must be positive")
        if not self._quota.can_create_watch(chat_id):
            raise WatchLimitReached
        return self._watches.insert(
            Watch(
                chat_id=chat_id,
                trip_type=trip_type,
                origins=origin.codes,
                destinations=destination.codes,
                origin_label=origin.display,
                destination_label=destination.display,
                departure_date=departure_date,
                return_date=return_date,
                target_price=target_price,
            )
        )

    def list_active(self, chat_id: int) -> list[Watch]:
        return self._watches.find_active_by_chat(chat_id)

    def remove(self, chat_id: int, watch_id: int) -> bool:
        watch = self._watches.find(watch_id)
        if watch is None or watch.chat_id != chat_id or watch.status != WatchStatus.ACTIVE:
            return False
        self._watches.update_status(watch_id, WatchStatus.REMOVED)
        return True

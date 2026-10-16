from collections.abc import Callable
from datetime import datetime, timedelta

from flight_tracker.repositories.search_request_repository import SearchRequestRepository
from flight_tracker.repositories.watch_repository import WatchRepository


class QuotaService:
    def __init__(
        self,
        search_requests: SearchRequestRepository,
        watches: WatchRepository,
        max_searches_per_hour: int,
        max_active_watches: int,
        now: Callable[[], datetime] = datetime.now,
    ):
        self._search_requests = search_requests
        self._watches = watches
        self.max_searches_per_hour = max_searches_per_hour
        self.max_active_watches = max_active_watches
        self._now = now

    def try_consume_search(self, chat_id: int) -> bool:
        now = self._now()
        if self._search_requests.count_since(chat_id, now - timedelta(hours=1)) >= self.max_searches_per_hour:
            return False
        self._search_requests.add(chat_id, now)
        return True

    def can_create_watch(self, chat_id: int) -> bool:
        return self._watches.count_active(chat_id) < self.max_active_watches

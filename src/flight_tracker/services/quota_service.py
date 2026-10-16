from collections.abc import Callable
from datetime import datetime, timedelta

from flight_tracker.repositories.search_request_repository import SearchRequestRepository


class QuotaService:
    def __init__(
        self,
        search_requests: SearchRequestRepository,
        max_searches_per_hour: int,
        now: Callable[[], datetime] = datetime.now,
    ):
        self._search_requests = search_requests
        self.max_searches_per_hour = max_searches_per_hour
        self._now = now

    def try_consume_search(self, chat_id: int) -> bool:
        now = self._now()
        if self._search_requests.count_since(chat_id, now - timedelta(hours=1)) >= self.max_searches_per_hour:
            return False
        self._search_requests.add(chat_id, now)
        return True

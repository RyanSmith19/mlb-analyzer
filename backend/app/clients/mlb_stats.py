from datetime import date
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi


class MLBStatsError(Exception):
    """Raised when the MLB Stats API cannot provide a response."""


class MLBStatsClient:
    def __init__(
        self,
        base_url: str = "https://statsapi.mlb.com/api/v1",
        timeout: float = 10.0,
        game_feed_base_url: str = "https://statsapi.mlb.com/api/v1.1",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._game_feed_base_url = game_feed_base_url.rstrip("/")
        self._timeout = timeout

    def get_schedule_raw(self, game_date: date) -> bytes:
        query = urlencode({"sportId": 1, "date": game_date.isoformat(), "hydrate": "probablePitcher"})
        return self._get_raw(f"{self._base_url}/schedule?{query}")

    def get_game_raw(self, game_pk: int) -> bytes:
        if game_pk <= 0:
            raise ValueError("game_pk must be positive")
        return self._get_raw(f"{self._game_feed_base_url}/game/{game_pk}/feed/live")

    def _get_raw(self, url: str) -> bytes:
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "mlb-analyzer/0.1"},
        )
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            with urlopen(request, timeout=self._timeout, context=context) as response:
                if response.headers.get_content_type() != "application/json":
                    raise MLBStatsError("MLB Stats API did not return JSON")
                return response.read()
        except HTTPError as exc:
            raise MLBStatsError(f"MLB Stats API returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise MLBStatsError("MLB Stats API is unavailable") from exc

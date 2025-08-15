# File: fetcher.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT
import random
from pathlib import Path
from typing import Iterable, Callable

from httpx import AsyncClient, Response
from yarl import URL

from scraper.logger import log


class Fetcher:
    """Component that fetches the website by sending HTTP GET requests."""

    def __init__(self, client: AsyncClient, base_url: str = 'https://doujinstyle.com/',
                 user_agents_file: str = '../user_agents.txt') -> None:
        self._base_url: URL = URL(base_url)
        self._client: AsyncClient = client
        # Load the user agents in memory.
        self._user_agents: list[str] = Fetcher._load_user_agents(Path(user_agents_file))

    @staticmethod
    def _load_user_agents(filename: Path) -> list[str]:
        """
        Returns a set of user agents from a user agents text file.
        The file format should be: one user agent per line.
        Returns a default user agent if file empty/does not exist.
        """
        default_ua: list[str] = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        ]

        if not filename.exists():
            log.warning(f'User agents file: {filename} does not exist; using default.')
            return default_ua

        with filename.open('r', encoding='utf-8') as f:
            # Deduplicate
            if ua := set([agent.strip() if len((part := agent.split('|'))) == 1 else part[1].strip() for agent in f]):
                return list(ua)
            return default_ua

    def _make_headers(self) -> dict[str, str]:
        """Makes a unique header (random user agent) for each HTTP request."""
        return {'User-Agent': random.choice(self._user_agents)}

    async def _fetch(self, url: URL) -> bytes:
        """Sends an HTTP GET to URL and returns the bytes."""
        r: Response = await self._client.get(url=str(url), headers=self._make_headers())
        log.debug(f'Fetched {url}')
        r.raise_for_status()
        return r.content

    def _make_url_item(self, item_id: int) -> URL:
        """Returns the URL corresponding to an ID."""
        # E.g., https://doujinstyle.com/?p=page&type=1&id=198
        return self._base_url.with_query(p="page", type="1", id=item_id)

    async def fetch(self, callback: Callable[[bytes], None], ids_range: Iterable[int] = None) -> None:
        """
        Fetches the HTTP response byte data returned by each request. Calls the callable with it.
        :param callback: Called with an HTTP response's bytes.
        :param ids_range: The range of IDs the fetcher will try to fetch.
        """
        # tests
        b = await self._fetch(self._base_url)
        callback(b)

        print(self._make_url_item(198))
        print(self._make_url_item(198).human_repr())

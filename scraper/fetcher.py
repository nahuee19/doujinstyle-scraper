# File: fetcher.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT

import asyncio
import random
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Iterable, Callable, Generator, Optional, Awaitable

import httpx
from httpx import AsyncClient, Response
from yarl import URL

from scraper.logger import log

# Callback function that gets called when both HTTP GET & HTTP POST requests are done,
# sending the resulting bytes to the parser.
type ReqCb = Callable[[FetchedItem], None]

# A function that does a request e.g., GET or POST.
type ReqFunc = Callable[[URL], Awaitable[bytes | URL]]


class Fetcher:
    """Component that fetches the website by sending HTTP GET requests."""

    # Random time interval to wait for inside each worker in seconds, in between first and second value included.
    WORKER_JITTER: tuple[float, float] = 0.05, 0.3
    # Number of times to retry if server HTTP error code.
    MAX_RETRIES: int = 10

    def __init__(self, client: AsyncClient, base_url: str = 'https://doujinstyle.com/',
                 user_agents_file: str = Path(__file__).parent.with_name("user_agents.txt"),
                 batch_size: int = 10) -> None:
        """
        Constructor of the `Fetcher` component.
        :param client: Asynchronous client the `Fetcher` uses to do its HTTP GET requests.
        :param base_url: Base URL of the website.
        :param user_agents_file: A text file with user agents on each line. Each HTTP request will have a randomly
        selected user agent from this file. If none selected, a single default user agent will be used.
        :param batch_size: The number of URLs fetched concurrently.
        """
        self._base_url: URL = URL(base_url)
        self._client: AsyncClient = client
        # Load the user agents in memory.
        self._user_agents: list[str] = Fetcher._load_user_agents(Path(user_agents_file))

        if batch_size <= 0:
            log.warning('batch_size cannot be negative or zero; defaulting to 1')
        self._batch_size: int = batch_size if batch_size > 0 else 1

    @staticmethod
    def _load_user_agents(filename: Path) -> list[str]:
        """
        Returns a list of user agents from a user agents text file.
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
            if ua := set(
                    [agent.strip() if len((part := agent.split('|', 1))) == 1 else part[1].strip() for agent in f]):
                return list(ua)
            return default_ua

    def _make_headers(self, referer_url: URL) -> dict[str, str]:
        """Makes a unique header (random user agent) for each HTTP request. Add redirect referer."""
        return {'User-Agent': random.choice(self._user_agents), 'Referer': str(referer_url)}

    @staticmethod
    def _get_id_from_url(url: URL) -> Optional[int]:
        """Returns the item ID from an item URL."""
        try:
            return int(url.query.get('id'))
        except Exception as e:
            log.warning(f'Failed to get ID from URL: {e}')

        return None

    async def _fetch(self, url: URL) -> bytes:
        """Sends an HTTP GET request to URL and returns the bytes."""
        r: Response = await self._client.get(url=str(url), headers=self._make_headers(url))
        r.raise_for_status()
        log.debug(f'GET {url} -> {r.status_code}')
        return r.content

    async def _post(self, url: URL) -> URL:
        """Sends an HTTP POST request to URL and returns the bytes."""
        if not (url_id := str(self._get_id_from_url(url))):
            raise ValueError('missing id in URL query; cannot HTTP POST')

        data: dict = {
            'type': '1',
            'id': url_id,
            'source': '',
            'download_link': ''
        }
        r: Response = await self._client.post(url=str(url), data=data, headers=self._make_headers(url),
                                              follow_redirects=True)
        r.raise_for_status()
        log.debug(f'POST {url} -> {r.status_code}')
        return URL(str(r.url))

    # Note: maybe would be better as a function decorator.
    async def _with_retries(self, url: URL, req_func: ReqFunc) -> Optional[bytes]:
        """
        Calls a request function `ReqFunc` and wraps it around retries and exception handling.
        Worker that gets batched and scheduled in the public fetch() method.
        :param url: URL of the page to fetch.
        :returns: Either bytes if successful, None otherwise.
        :raises: Safe: does not raise any exceptions.
        """
        # Loop to retry fetch if rate-limited.
        for _ in range(self.MAX_RETRIES):
            await asyncio.sleep(random.uniform(*self.WORKER_JITTER))  # stagger start, a bit of jitter
            try:
                # Fetch the website.
                return await req_func(url)
                # Send the bytes to the parser via callback.
            except httpx.ConnectError as e:
                log.warning(f'Failed to connect to server: {e}')
            except httpx.HTTPStatusError as e:
                match e.response.status_code:
                    case 429 | 502 | 503 | 504:
                        ra: str = str(e.response.headers.get("Retry-After"))
                        delay = float(ra) if ra and ra.isdigit() else 5.0
                        log.warning(f'HTTP {e.response.status_code} - Retrying; sleeping for {delay}s: {e}')
                        await asyncio.sleep(delay)
                        continue
                    case _:
                        log.warning(f'HTTP {e.response.status_code}: {e}')
            except httpx.RequestError as e:
                log.warning(f'Request error for {url}: {e}')
            except asyncio.CancelledError:
                # Rethrow the TaskGroup cancellation.
                raise
            except Exception as e:
                log.warning(f'Exception in worker for {url}: {e}')
                return None

        return None

    async def _worker(self, url: URL, cb: ReqCb) -> None:
        """
        Send HTTP GET & HTTP POST requests to the website.
        :param url: URL of the item to fetch.
        :param cb: Parsing callback function that will get called with both responses as Optional[bytes].
        """
        # Do HTTP GET
        res_get: Optional[bytes] = await self._with_retries(url, self._fetch)

        # Drop POST if GET unsuccessful?

        # Do HTTP POST
        res_post: Optional[bytes] = await self._with_retries(url, self._post)

        # Call callback with both results.
        cb(FetchedItem(self._get_id_from_url(url), url, res_get, res_post))

    def _make_url_item(self, item_id: int) -> URL:
        """Returns the URL corresponding to an ID."""
        # E.g., https://doujinstyle.com/?p=page&type=1&id=198
        return self._base_url.with_query(p="page", type="1", id=item_id)

    def _generate_batch_urls(self, ids: Iterable[int], size: int) -> Generator[list[URL], None, None]:
        """
        Generates batches of the URLs corresponding to an ID range.
        :param ids: An arbitrary number of IDs.
        :param size: The number of URLs in each yielded batch.
        :returns: A generator that generates lists of URLs.
        """
        it = iter(self._make_url_item(item_id) for item_id in ids)
        while batch := list(islice(it, size)):
            yield batch

    async def fetch_range(self, ids_range: Iterable[int], callback: ReqCb) -> None:
        """
        Fetches the HTTP response byte data returned by each request. Calls the callable with it.
        :param ids_range: The range of IDs the fetcher will try to fetch. First ID is zero.
        :param callback: Called with the HTTP responses passed in.
        Read the README.md to get the highest ID.
        """
        for batch in self._generate_batch_urls(ids_range, self._batch_size):
            async with asyncio.TaskGroup() as tg:
                for url in batch:
                    tg.create_task(self._worker(url, callback))
            # Optional pause between batches to be gentler on server.
            # await asyncio.sleep(0.5)

    async def fetch_single(self, item_id: int, callback: ReqCb) -> None:
        """Same as fetch_range() but with a single ID."""
        await self.fetch_range([item_id], callback)


@dataclass
class FetchedItem:
    """
    Represents the response when fetching a website item.
    """
    # The ID of the item.
    item_id: int
    # The URL used to fetch the resources.
    url: URL
    # Response to an HTTP GET request.
    resp_get_content: Optional[bytes]
    # Response to an HTTP POST request.
    resp_post_url: Optional[URL]

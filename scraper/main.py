# File: main.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT

import asyncio

from httpx import Limits, Timeout, AsyncClient
from yarl import URL

from scraper.fetcher import Fetcher, FetchedItem
from scraper.logger import log
from scraper.parser import Parser


def fetcher_callback(resp: FetchedItem) -> None:
    g: bytes = resp.resp_get_content
    p: URL = resp.resp_post_url
    # print(f'GET Resp: {g}')
    if resp.url != p:
        print(f'POST Resp [{resp.item_id}]: {p}')


async def main() -> None:
    limits: Limits = Limits(max_connections=1, max_keepalive_connections=2)
    timeout: Timeout = Timeout(10.0)
    # follow_redirects=True is important for the POST.
    async with AsyncClient(limits=limits, timeout=timeout, follow_redirects=True) as client:
        site_fetcher: Fetcher = Fetcher(client)

        # The first `id_max` IDs. 0..=id_max
        id_max: int = 15
        await site_fetcher.fetch_range(range(id_max), fetcher_callback)
        # await site_fetcher.fetch_single(0, fetcher_callback)
        site_parser: Parser = Parser()


if __name__ == '__main__':
    log.info('[[ Scraper started ]]')
    asyncio.run(main())
    log.info('[[ Scraper finished ]]')

# File: main.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT

import asyncio

from httpx import Limits, Timeout, AsyncClient

from scraper.fetcher import Fetcher, Outcome
from scraper.logger import log


def fetcher_callback(resp: Outcome) -> None:
    log.debug(resp.res.status_code)
    # g: bytes = resp.resp_get_content
    # p: URL = resp.resp_post_url
    # # print(f'GET Resp: {g}')
    # if resp.url != p:
    #     print(f'POST Resp [{resp.item_id}]: {p}')


async def main() -> None:
    limits: Limits = Limits(max_connections=1, max_keepalive_connections=2)
    timeout: Timeout = Timeout(10.0)
    # follow_redirects=True is important for the POST.
    async with AsyncClient(limits=limits, timeout=timeout, follow_redirects=True) as client:
        async with Fetcher(client, print_metrics=True) as fetcher:
            await fetcher.fetch_single(0, fetcher_callback)
            await fetcher.fetch_single(1, fetcher_callback)

            # Wait for all tasks to finish.
            await fetcher.join()



if __name__ == '__main__':
    log.info('[[ Scraper started ]]')
    asyncio.run(main())
    log.info('[[ Scraper finished ]]')

# File: main.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT
import asyncio

from httpx import Limits, Timeout, AsyncClient

from scraper.fetcher import Fetcher
from scraper.logger import log
from scraper.parser import Parser


async def main() -> None:
    # Start logger
    log.info('Scraper started!')

    limits: Limits = Limits(max_connections=1, max_keepalive_connections=2)
    timeout: Timeout = Timeout(10.0)
    async with AsyncClient(limits=limits, timeout=timeout) as client:
        site_fetcher: Fetcher = Fetcher(client)
        await site_fetcher.fetch(lambda b: print(b))
        site_parser: Parser = Parser()


if __name__ == '__main__':
    asyncio.run(main())

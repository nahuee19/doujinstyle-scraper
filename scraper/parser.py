# File: parser.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT
import asyncio
from asyncio import AbstractEventLoop, Semaphore
from concurrent.futures.thread import ThreadPoolExecutor



class Parser:
    def __init__(self, max_threads: int = 8, parse_concurrency: int = 4):
        self._max_threads: int = max_threads if max_threads > 0 else 4
        self._parse_concurrency: int = parse_concurrency if parse_concurrency > 0 else 2

        _loop: AbstractEventLoop = asyncio.get_running_loop()
        _executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self._max_threads)
        _parse_sem: Semaphore = asyncio.Semaphore(self._parse_concurrency)
        _parse_tasks: set[asyncio.Task] = set()

    def fetcher_callback(self, item):
        pass

    def parse_sync(self, item: None) -> None:
        """Runs in a thread: bs4 + JSON dumping"""
        pass

# File: fetcher.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT

import asyncio
import random
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Iterable, Callable, Generator, Optional, Awaitable, Mapping, Any

import httpx
from httpx import AsyncClient, Response
from yarl import URL

from scraper.logger import log


@dataclass(frozen=True)
class GetResp:
    """
    Represents the HTTP GET response.
    """
    status_code: int
    # Content of the response in bytes
    content: bytes


@dataclass(frozen=True)
class PostResp:
    """
    Represents the HTTP POST response.
    """
    status_code: int
    # Returned URL of the HTTP POST request.
    url: URL


# TODO: Each task should has its own retry/timeout?
# TODO: Each task should has its own retry/timeout?
# TODO: Each task should has its own retry/timeout?

# A task that'll get queued up into the fetcher's task queue to be later executed based on its type.
type Task = GetTask | PostTask | StopTask

# Possible types of responses.
type Resp = GetResp | PostResp


@dataclass(frozen=True)
class Outcome:
    """
    Represents the outcome of a task, the result.
    """
    # ID of the item queried.
    item_id: int

    # URL to which the HTTP request was sent to.
    req_url: URL

    # Optional result, if it was successful.
    res: Optional[Resp] = None


# Callback function that gets called when both HTTP GET & HTTP POST requests are done,
# sending the resulting bytes to the parser.
type ReqCb = Callable[[Outcome], None]


@dataclass(frozen=True)
class GetTask:
    """
    Represents an HTTP GET request task.
    """
    # ID of the item to fetch.
    item_id: int

    # URL to GET
    url: URL

    # Custom HTTP headers
    headers: Mapping[str, str] | None = None

    # Callback that'll get called with the outcome
    callback: Optional[ReqCb] = None


@dataclass(frozen=True)
class PostTask:
    """
    Represents an HTTP POST request task.
    """
    # ID of the item to fetch.
    item_id: int

    # URL to POST to
    url: URL

    # POST data
    data: Mapping[str, Any] | None = None

    # Custom HTTP headers
    headers: Mapping[str, str] | None = None

    # Callback that'll get called with the outcome
    callback: Optional[ReqCb] = None


@dataclass(frozen=True)
class StopTask:
    """
    A task meant to stop the queue listening.
    """
    # No real purpose other than debugging.
    reason: str = "close queue processing"


# A function that does a request e.g., GET or POST.
type ReqFunc = Callable[[Task], Awaitable[Resp]]


class TaskPriorityQueue:
    """
    Represents the task queue with POST tasks always being prioritized.
    """

    def __init__(self, size: int):
        self.q_post: asyncio.Queue[PostTask | StopTask] = asyncio.Queue(maxsize=size)  # high priority
        self.q_get: asyncio.Queue[GetTask | StopTask] = asyncio.Queue(maxsize=size)  # low priority

        # If true, never accepts any task.
        self._is_sealed: bool = False

    async def put(self, task: Task) -> bool:
        """
        Calls the matching put() method. Adding a Task to the queue.

        Returns True for enqueued, False for otherwise.
        """
        log.debug(f'Enqueueing task {type(task)}...')
        if self._is_sealed:
            log.warning('Cannot put; queue sealed.')
            return False

        match task:
            case PostTask():
                await self.q_post.put(task)
            case GetTask():
                await self.q_get.put(task)
            case StopTask():
                self._is_sealed = True
                # Decide to use the POST queue to enqueue the stop tasks.
                await self.q_post.put(task)
        return True

    async def get(self) -> Task:
        """Returns a Task from the queue. Always prioritizes POST tasks."""
        # log.debug(f'POST QUEUE: {self.q_post}')
        # log.debug(f'GET QUEUE: {self.q_get}')
        while True:
            # Return directly without waiting for queue if a POST task is inside.
            try:
                return self.q_post.get_nowait()
            except asyncio.QueueEmpty:
                pass

            # If not, wait a bit for a GET task.
            # Without the loop, if the GET queue would be empty, and
            # we were awaiting a .get() on it, the function would never return.
            try:
                return await asyncio.wait_for(self.q_get.get(), timeout=0.05)
            except asyncio.TimeoutError:
                pass

    def task_done(self, item: Task):
        """Mark the item as processed on its originating queue."""
        match item:
            case PostTask():
                self.q_post.task_done()
            case GetTask():
                self.q_get.task_done()
            case StopTask():
                # We decided to only use the POST queue for stop tasks.
                self.q_post.task_done()

    async def join(self):
        """Awaits the corresponding .join() method on all queues, waiting for them to be finished processing."""
        await asyncio.gather(
            self.q_post.join(),
            self.q_get.join()
        )


class AsyncCounter:
    """Asynchronous-safe counter."""

    def __init__(self, start: int = 0):
        self._value: int = start
        self._lock: asyncio.Lock = asyncio.Lock()

    async def inc(self, value: Optional[int] = 1) -> int:
        """Increments the counter by ``value``, one by default. Returns the current value incremented by value."""
        async with self._lock:
            self._value += value
            return self._value

    async def dec(self, value: Optional[int] = 1) -> int:
        """Decrements the counter by ``value``, one by default. Returns the current value decremented by value."""
        async with self._lock:
            self._value -= value
            return self._value

    async def get(self) -> int:
        async with self._lock:
            return self._value


class Metrics:
    """Metrics during the app"""

    def __init__(self):
        self.request_count: dict[str, AsyncCounter] = {}

    async def inc_req(self, req_type: str) -> int:
        """Increments the counter for the given request type."""
        # Inc global count
        await self.request_count['ALL'].inc()

        # Create if not exist.
        if req_type not in self.request_count:
            self.request_count[req_type] = AsyncCounter(1)
            return 1

        # if exists, inc
        return await self.request_count[req_type].inc()

    @classmethod
    def hook_httpx_client(cls, client: httpx.AsyncClient):
        client.event_hooks = {
            'request': [cls._on_httpx_request],
            'response': [cls._on_httpx_response]
        }

    async def _on_httpx_request(self, request) -> None:
        # count by current request method on the wire
        print(request)
        await self.inc_req(request.method)

    async def _on_httpx_response(self, response: httpx.Response) -> None:
        return
        # Count redirects by the *original request method* for this hop
        if response.is_redirect:
            await self.metrics.redirects_total.inc()
            m = response.request.method  # method that received the redirect
            if m in self.metrics.redirects_by_method:
                await self.metrics.redirects_by_method[m].inc()

    async def make_string(self) -> str:
        """Creates a human string representation of the metrics."""
        reqs: str = ''
        for method, value in self.request_count.items():
            # indentation + metrics
            reqs += f'    {method}: {await value.get():>5}\n'

        return f"""Network Metrics:
  Sent HTTP Requests:
{reqs}"""


class Fetcher:
    """Component that fetches the website by sending HTTP GET requests."""

    # Random time interval to wait for inside each worker in seconds, in between first and second value included.
    _WORKER_JITTER: tuple[float, float] = 0.05, 0.3

    # Number of times to retry if server HTTP error code.
    _MAX_RETRIES: int = 10

    # Maximum number of tasks to be buffered in the fetcher's task queue, at maximum.
    _TASK_QUEUE_SIZE: int = 100

    def __init__(self, client: AsyncClient, base_url: str = 'https://doujinstyle.com/',
                 user_agents_file: str = Path(__file__).parent.with_name("user_agents.txt"),
                 print_metrics: bool = False
                 ) -> None:
        """
        Constructor of the `Fetcher` component.
        :param client: Asynchronous client the `Fetcher` uses to do its HTTP GET requests.
        :param base_url: Base URL of the website.
        :param user_agents_file: A text file with user agents on each line. Each HTTP request will have a randomly
        :param print_metrics: Prints some statistics on sent requests when the instance goes out of scope.
        selected user agent from this file. If none selected, a single default user agent will be used.
        """

        # If True, disallows any task to enter the task queue. Effectively disallowing put().
        self._is_sealed: bool = False

        # Base URL of the website.
        self._base_url: URL = URL(base_url)

        self._client: AsyncClient = client
        # Load the user agents in memory.
        self._user_agents: list[str] = Fetcher._load_user_agents(Path(user_agents_file))

        # Queue of tasks to execute.
        self._task_queue: TaskPriorityQueue = TaskPriorityQueue(100)

        # Our task group to run concurrently our tasks.
        self._tg: asyncio.TaskGroup | None = None

        # Records some metrics.
        self.metrics: Metrics = Metrics()

        # Hook some httpx events to count requests
        self.metrics.hook_httpx_client(client)

        self._print_metrics = print_metrics

    async def __aenter__(self):
        self._tg = asyncio.TaskGroup()
        await self._tg.__aenter__()

        # Start consuming queue
        self._tg.create_task(self._consume_queue(), name='QueueConsumer')

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self._tg is not None

        # Close the queue listener and wait for the queue to empty.
        await self._enqueue_stop()
        await self._task_queue.join()

        await self._tg.__aexit__(exc_type, exc_val, exc_tb)
        self._tg = None
        if self._print_metrics:
            print(f'\n{await self.make_metrics()}')

    async def make_metrics(self) -> str:
        """Creates a human-readable metrics string for printing."""
        return await self.metrics.make_string()

    async def enqueue(self, task: Task, timeout: Optional[float] = None):
        """
        Enqueues a task to the task queue.
        :param task: A task to execute.
        :param timeout: Maximum time allowed to enqueue the task.
        """
        if self._is_sealed:
            raise RuntimeError('Queue sealed; fetcher is closed to new tasks.')

        if not isinstance(task, GetTask | PostTask | StopTask):
            raise RuntimeError(f'Task cannot be {type(task)}.')

        if timeout is None or timeout <= 0:
            await self._task_queue.put(task)
        else:
            await asyncio.wait_for(self._task_queue.put(task), timeout)

    async def join(self):
        """Blocks until all """
        await self._task_queue.join()

    async def _wrap_and_mark(self, t: Task) -> None:
        """Wraps the worker to honour the join()."""
        try:
            await self._worker_ex_task(t)
        finally:
            self._task_queue.task_done(t)

    async def _consume_queue(self):
        """Listens on the queue and consumes it, executing tasks."""
        if not self._tg:
            raise ValueError('TaskGroup is None; please use a context manager.')

        while True:
            match task := await self._task_queue.get():
                case GetTask() | PostTask():
                    self._tg.create_task(self._wrap_and_mark(task))
                case StopTask(reason=reason):
                    self._task_queue.task_done(task)
                    log.info(f'Awaiting queue drainage...; stopped listening, reason: {reason}')
                    await self._task_queue.join()
                    break

    async def _enqueue_stop(self):
        """Enqueues a StopTask, when read by the consumer, the latter will cease to listen on the queue."""
        log.debug('Enqueueing stop sentinel task.')
        await self._task_queue.put(StopTask())

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

    async def _do_get(self, url: URL, headers: Optional[Mapping[str, str]]) -> GetResp:
        """Sends an HTTP GET request to URL and returns the bytes."""
        r: Response = await self._client.get(
            url=str(url),
            headers=(headers if headers else self._make_headers(url))
        )
        r.raise_for_status()
        count: int = await self.metrics.request_count['GET'].get()
        log.debug(f'GET #{count} {url} -> {r.status_code}')

        return GetResp(r.status_code, r.content)

    async def _do_post(self, url: URL, headers: Optional[Mapping[str, str]], data: Mapping[str, Any]) -> PostResp:
        """Sends an HTTP POST request to URL and returns the bytes."""
        # if not (url_id := str(self._get_id_from_url(url))):
        #     raise ValueError('missing id in URL query; cannot HTTP POST')
        # data: dict = {
        #     'type': '1',
        #     'id': url_id,
        #     'source': '',
        #     'download_link': ''
        # }
        r: Response = await self._client.post(
            url=str(url),
            data=data,
            headers=(headers if headers else self._make_headers(url)),
            follow_redirects=True
        )
        r.raise_for_status()
        count: int = await self.metrics.request_count['POST'].get()
        log.debug(f'POST #{count} {url} -> {r.status_code}')

        return PostResp(r.status_code, URL(r.url))

    # Note: maybe would be better as a function decorator.
    async def _worker_ex_task(self, task: Task) -> None:
        """
        Executes the corresponding request function to the task. Wrapping the execution in retries and exception handling
        making the process "safe".

        This function is being tasked using the `tg_` TaskGroup object.
        The httpx ``Limits`` in main.py is what throttles the connections.

        :param task: What type of task to execute, encapsulating task data.
        :returns: An ``Outcome`` which has an ``Optional[Resp]`` inside.
        :raises: Safe: does not raise any exceptions.
        :returns: Nothing; calls the callback function of the tasks and pass in an ``Outcome``.
        """
        retries_count: int = 0
        # Loop to retry fetch if rate-limited.
        for _ in range(self._MAX_RETRIES):
            retries_count += 1
            if retries_count > 1:
                log.info(f'Try #{retries_count:02}{self._MAX_RETRIES:02}')

            await asyncio.sleep(random.uniform(*self._WORKER_JITTER))  # stagger start, a bit of jitter
            try:
                # Fetch the website.
                match task:
                    case GetTask(item_id=item_id, url=url, headers=headers, callback=cb):
                        resp: Resp = await self._do_get(url, headers)
                    case PostTask(item_id=item_id, url=url, headers=headers, data=data, callback=cb):
                        resp: Resp = await self._do_post(url, headers, data)
                    case StopTask():
                        log.error('Worker received StopTask; undefined behavior; ignored.')
                        # Since this function is supposed to be safe, we will not either raise nor exit().
                        return None

                # Send the Outcome to the parser via callback.
                if cb is not None:
                    cb(Outcome(item_id, url, resp))
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
                log.warning(f'Request error for {task.url}: {e}')
            except asyncio.CancelledError:
                # Rethrow the TaskGroup cancellation.
                raise
            except Exception as e:
                log.warning(f'Exception in worker for {task.url}: {e}')
                return None

            return None

        if cb := task.callback is not None:
            cb(Outcome(task.item_id, task.url, None))
        return None

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

    @staticmethod
    def _make_get_task(item_id: int, url: URL, cb: ReqCb) -> GetTask:
        """Creates an HTTP GET task from a URL."""
        return GetTask(
            item_id,
            url,
            callback=cb
        )

    async def fetch_range(self, ids_range: Iterable[int], callback: ReqCb) -> None:
        """
        Fetches the HTTP response byte data returned by each request. Calls the callable with it.
        :param ids_range: The range of IDs the fetcher will try to fetch. First ID is zero.
        :param callback: Called with the HTTP responses passed in.
        Read the README.md to get the highest ID.
        """
        for item_id in ids_range:
            await self.enqueue(self._make_get_task(item_id, self._make_url_item(item_id), callback))

        # Optional pause between batches to be gentler on server.
        # await asyncio.sleep(0.5)

    async def fetch_single(self, item_id: int, callback: ReqCb) -> None:
        """Same as fetch_range() but with a single ID."""
        await self.fetch_range((item_id,), callback)

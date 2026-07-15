from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

JobWork = Callable[[], Awaitable[None]]


class BackgroundJobQueue:
    def __init__(self, *, concurrency: int = 3) -> None:
        self._queue: asyncio.Queue[tuple[str, JobWork]] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._concurrency = max(1, concurrency)
        self._started = False
        self._logger = logging.getLogger("lenquant.jobs")

    async def enqueue(self, label: str, work: JobWork) -> None:
        await self._ensure_workers()
        await self._queue.put((label, work))

    async def _ensure_workers(self) -> None:
        if self._started:
            return
        loop = asyncio.get_running_loop()
        for _ in range(self._concurrency):
            self._workers.append(loop.create_task(self._worker()))
        self._started = True

    async def _worker(self) -> None:
        while True:
            label, work = await self._queue.get()
            try:
                await work()
            except Exception:
                self._logger.exception("Background job %s failed", label)
            finally:
                self._queue.task_done()


job_queue = BackgroundJobQueue()

from __future__ import annotations

import asyncio
from typing import Any

from rq import Queue

from src.application.ports.queue_gateway import QueueGateway


class RQGateway(QueueGateway):
    """Dispatch async jobs via Redis Queue (RQ).

    Wraps the synchronous RQ enqueue call in asyncio.to_thread so it can be
    awaited from an async context without blocking the event loop.
    """

    def __init__(self, queue: Queue) -> None:
        self._queue = queue

    async def enqueue(self, job_name: str, payload: dict[str, Any]) -> str:
        job = await asyncio.to_thread(self._queue.enqueue, job_name, payload)
        return str(job.id)

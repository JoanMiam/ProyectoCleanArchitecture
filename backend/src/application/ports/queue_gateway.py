from abc import ABC, abstractmethod
from typing import Any


class QueueGateway(ABC):
    """Dispatches asynchronous jobs off the main sync path.

    Used for non-critical work (audit projections, notifications). The concrete
    adapter targets Redis/RQ; use cases depend only on this contract.
    """

    @abstractmethod
    async def enqueue(self, job_name: str, payload: dict[str, Any]) -> str: ...

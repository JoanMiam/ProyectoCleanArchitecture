"""Wall-clock implementation of :class:`Clock`."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.ports.clock import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)
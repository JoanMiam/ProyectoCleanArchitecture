from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Version:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"Version must be non-negative, got {self.value}")

    def increment(self) -> Version:
        return Version(self.value + 1)

    def is_base_for(self, current: Version) -> bool:
        """True if this version is a valid base for applying changes against `current`."""
        return self.value == current.value

    def __str__(self) -> str:
        return str(self.value)

"""Duplicate and outlier rejection for incoming coordinate updates.

Pure Python (no Qt, no I/O) so it is easy to test.  Clipboard and OCR both feed
the same filter.  A single bad copy (a mistyped paste, a stale clipboard value,
an OCR misread) must not teleport the player pin, but a genuine respawn or
long-distance travel must still be accepted.

Rules, in order:

1. Same coordinates as the last accepted fix -> ``DUPLICATE`` (ignored).
2. Outside the map's world bounds (plus a margin) -> ``REJECTED``.
3. Farther from the last accepted fix than a player could plausibly have moved
   in the elapsed time -> held as a *pending* outlier and ``REJECTED``.  If the
   very next reading lands near that pending outlier, the jump was real
   (respawn / teleport) and it is ``ACCEPTED``.
4. Otherwise ``ACCEPTED``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from core.models import Position


class FilterStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class FilterResult:
    status: FilterStatus
    reason: str = ""

    @property
    def accepted(self) -> bool:
        return self.status is FilterStatus.ACCEPTED


class PositionFilter:
    """Stateful duplicate/outlier filter.  World units are Unreal centimetres."""

    def __init__(
        self,
        *,
        max_speed: float = 4_000.0,  # cm/s, well above the fastest creature
        min_allowance: float = 25_000.0,  # cm; slack for stale/late copies
        confirm_radius: float = 6_000.0,  # cm; two bad reads this close agree
        duplicate_tolerance: float = 0.01,
        bounds: tuple[float, float, float, float] | None = None,
        bounds_margin: float = 20_000.0,
    ) -> None:
        self.max_speed = max_speed
        self.min_allowance = min_allowance
        self.confirm_radius = confirm_radius
        self.duplicate_tolerance = duplicate_tolerance
        self.bounds = bounds  # (min_x, max_x, min_y, max_y)
        self.bounds_margin = bounds_margin
        self._last: Position | None = None
        self._pending: Position | None = None

    @property
    def last_accepted(self) -> Position | None:
        return self._last

    def reset(self) -> None:
        self._last = None
        self._pending = None

    def allowed_distance(self, seconds: float) -> float:
        return self.min_allowance + self.max_speed * max(0.0, seconds)

    def check(self, position: Position) -> FilterResult:
        if self.bounds is not None:
            min_x, max_x, min_y, max_y = self.bounds
            m = self.bounds_margin
            if not (min_x - m <= position.x <= max_x + m and min_y - m <= position.y <= max_y + m):
                return FilterResult(FilterStatus.REJECTED, "outside the Gateway map")

        last = self._last
        if last is None:
            return self._accept(position)

        if (
            abs(position.x - last.x) <= self.duplicate_tolerance
            and abs(position.y - last.y) <= self.duplicate_tolerance
            and abs(position.z - last.z) <= self.duplicate_tolerance
        ):
            return FilterResult(FilterStatus.DUPLICATE, "same coordinates as last update")

        elapsed = (position.timestamp - last.timestamp).total_seconds()
        jump = math.hypot(position.x - last.x, position.y - last.y)
        if jump <= self.allowed_distance(elapsed):
            return self._accept(position)

        pending = self._pending
        if pending is not None and (
            math.hypot(position.x - pending.x, position.y - pending.y) <= self.confirm_radius
        ):
            return self._accept(position)  # two agreeing reads: a real teleport
        self._pending = position
        return FilterResult(
            FilterStatus.REJECTED,
            "sudden jump ignored - copy again to confirm if you really moved that far",
        )

    def _accept(self, position: Position) -> FilterResult:
        self._last = position
        self._pending = None
        return FilterResult(FilterStatus.ACCEPTED)

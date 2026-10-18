"""Describe tracking health (active / stale / waiting) for the status bar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

SOURCE_CLIPBOARD = "clipboard"
SOURCE_OCR = "ocr"
SOURCE_WEB_MAP = "web_map"
SOURCE_LABELS = {SOURCE_CLIPBOARD: "Clipboard", SOURCE_OCR: "OCR", SOURCE_WEB_MAP: "Live web map"}

STALE_AFTER_SECONDS = 45.0


@dataclass(frozen=True, slots=True)
class TrackingStatus:
    state: str  # "waiting" | "active" | "stale"
    text: str
    color: str


def format_age(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes, rem = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {rem:02d}s ago"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m ago"


def describe_tracking(
    last_update: datetime | None,
    source: str | None,
    now: datetime | None = None,
    stale_after: float = STALE_AFTER_SECONDS,
) -> TrackingStatus:
    if last_update is None:
        return TrackingStatus("waiting", "● WAITING · no position yet", "#e0a93b")
    now = now or datetime.now(timezone.utc)
    age = (now - last_update).total_seconds()
    label = SOURCE_LABELS.get(source or "", "Unknown")
    if age <= stale_after:
        return TrackingStatus("active", f"● ACTIVE · {label} · {format_age(age)}", "#3ddc84")
    return TrackingStatus("stale", f"● STALE · {label} · {format_age(age)}", "#e0a93b")

"""Settings helpers for the optional embedded web live map (opt-in, never automatic)."""

from __future__ import annotations

from urllib.parse import urlparse

DEFAULT_WEB_MAP_URL = "https://playorigin.gg/map"


def sanitize_web_map_url(value: object, default: str = DEFAULT_WEB_MAP_URL) -> str:
    """Return a usable https URL, or the default if the value is not one.

    Only https pages with a host are accepted, so a typo or a pasted file/script
    link can never be loaded into the overlay window.
    """

    text = str(value or "").strip()
    parsed = urlparse(text)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return default
    return text


def clamp_web_map_opacity(value: object, default: float = 0.85) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return min(1.0, max(0.3, number))

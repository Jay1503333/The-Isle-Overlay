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


def clamp_web_map_zoom(value: object, default: float = 1.0) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return min(1.5, max(0.4, number))


MAP_ONLY_STYLE_ID = "companion-map-only"

# Cosmetic, local-only view tweak: hides the site's header, sidebar and banners so
# the map fills the overlay window. It only runs on /map pages and never reads data.
MAP_ONLY_CSS = (
    "header, aside { display: none !important; }"
    "body { overflow: hidden !important; }"
    "div.flex.pt-20 { padding-top: 0 !important; }"
    "main { margin-left: 0 !important; padding: 0 !important; min-height: 0 !important; }"
    "main > div:not(:has(.leaflet-container)) { display: none !important; }"
    "main > div:has(.leaflet-container) { height: 100vh !important; }"
)


def map_only_script(enabled: bool) -> str:
    """JavaScript that applies or removes the map-only view (idempotent)."""

    css = MAP_ONLY_CSS.replace("\\", "\\\\").replace("'", "\\'")
    return (
        "(function(){"
        f"var id='{MAP_ONLY_STYLE_ID}';"
        "var el=document.getElementById(id);"
        f"var want={'true' if enabled else 'false'} && location.pathname.indexOf('/map')===0;"
        "if(want&&!el){el=document.createElement('style');el.id=id;"
        f"el.textContent='{css}';document.head.appendChild(el);}}"
        "else if(!want&&el){el.remove();}"
        "setTimeout(function(){window.dispatchEvent(new Event('resize'));},60);"
        "})();"
    )

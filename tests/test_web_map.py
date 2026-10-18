import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.settings import DEFAULT_SETTINGS, SettingsStore
from core.web_map import DEFAULT_WEB_MAP_URL, clamp_web_map_opacity, sanitize_web_map_url


def test_only_https_urls_are_accepted():
    assert sanitize_web_map_url("https://playorigin.gg/map") == "https://playorigin.gg/map"
    for bad in ("", None, "http://example.com", "file:///C:/x.html", "javascript:alert(1)", "https://"):
        assert sanitize_web_map_url(bad) == DEFAULT_WEB_MAP_URL


def test_opacity_is_clamped():
    assert clamp_web_map_opacity(5) == 1.0
    assert clamp_web_map_opacity(0) == 0.3
    assert clamp_web_map_opacity("junk") == 0.85


def test_bad_saved_web_map_settings_are_repaired(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"web_map_url": "http://evil", "web_map_opacity": 9}', encoding="utf-8")
    store = SettingsStore(path)
    assert store.values["web_map_url"] == DEFAULT_SETTINGS["web_map_url"]
    assert 0.3 <= store.values["web_map_opacity"] <= 1.0


def test_web_map_window_builds_without_loading_anything(tmp_path):
    from PySide6.QtWidgets import QApplication

    from ui.web_map_window import WebMapWindow

    app = QApplication.instance() or QApplication([])
    window = WebMapWindow(dict(DEFAULT_SETTINGS), tmp_path / "profile")
    assert window._view is None  # nothing loads until the user opens it
    assert window.interaction_enabled
    window.set_interaction_enabled(False)
    assert not window.interaction_enabled
    assert app is not None

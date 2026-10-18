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


def test_zoom_is_clamped_and_map_only_script_is_safe():
    from core.web_map import MAP_ONLY_STYLE_ID, clamp_web_map_zoom, map_only_script

    assert clamp_web_map_zoom(9) == 1.5
    assert clamp_web_map_zoom(0) == 0.4
    assert clamp_web_map_zoom("x") == 1.0
    on, off = map_only_script(True), map_only_script(False)
    assert MAP_ONLY_STYLE_ID in on and "&& location.pathname" in on
    assert "false &&" in off  # turning it off removes the style
    assert "\n" not in on  # one-line script


def test_web_map_window_edges_and_defaults(tmp_path):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtWidgets import QApplication

    from ui.web_map_window import EDGE, WebMapWindow

    QApplication.instance() or QApplication([])
    window = WebMapWindow(dict(DEFAULT_SETTINGS), tmp_path / "profile")
    assert window.width() >= 220 and window.height() >= 180
    assert window._edges_at(QPoint(1, 1)) == (Qt.Edge.LeftEdge | Qt.Edge.TopEdge)
    assert window._edges_at(QPoint(window.width() - 1, window.height() - 1)) == (
        Qt.Edge.RightEdge | Qt.Edge.BottomEdge
    )
    assert not window._edges_at(QPoint(window.width() // 2, window.height() // 2))
    assert EDGE > 0


def test_parse_live_position_reads_the_page_readout():
    from core.web_map import parse_live_position

    assert parse_live_position("Lat: -85,578  Long: 485,138") == (485138.0, -85578.0)
    assert parse_live_position("Lat: 1,200.5 Long: -3,000") == (-3000.0, 1200.5)
    assert parse_live_position("nothing here") is None
    assert parse_live_position(None) is None
    assert parse_live_position("Lat: 99,999,999 Long: 1") is None


def test_live_feed_is_off_by_default_and_script_is_one_expression():
    from core.settings import DEFAULT_SETTINGS
    from core.web_map import LIVE_POSITION_SCRIPT

    assert DEFAULT_SETTINGS["web_map_feed_position"] is False
    assert "\n" not in LIVE_POSITION_SCRIPT
    assert "fetch(" not in LIVE_POSITION_SCRIPT and "XMLHttp" not in LIVE_POSITION_SCRIPT

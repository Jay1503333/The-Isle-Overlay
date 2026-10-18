import copy
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGraphicsPolygonItem

from core.app_state import AppState
from core.coordinate_transform import load_calibration
from core.data_loader import LayerRepository
from core.models import Position
from core.settings import DEFAULT_SETTINGS, SettingsStore
from ui.main_window import MainWindow
from ui.mini_map import MiniMapWindow

ROOT = Path(__file__).resolve().parents[1]


def _build(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = copy.deepcopy(DEFAULT_SETTINGS)
    store = SettingsStore(tmp_path / "settings.json")
    store.values = settings
    calibration = load_calibration(ROOT / "assets" / "map" / "calibration.json")
    repository = LayerRepository(ROOT / "data")
    state = AppState(settings)
    full = MainWindow(ROOT, store, calibration, repository, state)
    mini = MiniMapWindow(ROOT / "assets" / "map" / "gateway.webp", calibration, repository, state)
    full.attach_mini_map(mini)
    return app, state, full, mini, store


def test_defaults_are_circular_minimap_with_full_ui_opacity():
    assert DEFAULT_SETTINGS["overlay_shape"] == "circle"
    assert DEFAULT_SETTINGS["overlay_ui_opacity"] == 1.0
    assert DEFAULT_SETTINGS["first_run_completed"] is False


def test_status_indicator_shows_source_and_state(tmp_path):
    app, state, full, mini, _ = _build(tmp_path)
    assert "WAITING" in full.tracking_indicator.text()
    state.update_position(Position.now(1000, 2000, 0), "clipboard")
    app.processEvents()
    assert "ACTIVE" in full.tracking_indicator.text()
    assert "Clipboard" in full.tracking_indicator.text()
    state.update_position(Position.now(1500, 2500, 0), "ocr")
    assert "OCR" in full.tracking_indicator.text()


def test_heading_arrow_appears_after_movement(tmp_path):
    app, state, full, mini, _ = _build(tmp_path)
    state.update_position(Position.now(0, 0, 0), "clipboard")
    group = full.map_canvas._groups["player"]
    assert not [i for i in group.childItems() if isinstance(i, QGraphicsPolygonItem)]
    state.update_position(Position.now(0, 5000, 0), "clipboard")
    arrows = [i for i in group.childItems() if isinstance(i, QGraphicsPolygonItem)]
    assert len(arrows) == 1


def test_independent_opacity(tmp_path):
    app, state, full, mini, _ = _build(tmp_path)
    state.settings["overlay_opacity"] = 0.5
    state.settings["overlay_ui_opacity"] = 1.0
    mini.apply_opacity()
    assert mini.windowOpacity() == 1.0
    assert mini._opacity_effects["map"].isEnabled()
    assert abs(mini._opacity_effects["map"].opacity() - 0.5) < 1e-6
    assert not mini._opacity_effects["ui"].isEnabled()
    state.settings["overlay_opacity"] = 0.9
    state.settings["overlay_ui_opacity"] = 0.45
    mini.apply_opacity()
    assert abs(mini.windowOpacity() - 0.9) < 0.01
    assert mini._opacity_effects["ui"].isEnabled()


def test_first_run_guide_is_marked_seen(tmp_path, monkeypatch):
    app, state, full, mini, store = _build(tmp_path)
    shown = []
    monkeypatch.setattr("ui.main_window.HowToUseDialog.exec", lambda self: shown.append(self) or 0)
    full.show_first_run_guide()
    full.show_first_run_guide()
    assert len(shown) == 1
    assert state.settings["first_run_completed"] is True


def test_click_through_is_default_and_toggles(tmp_path):
    from PySide6.QtCore import Qt

    app, state, full, mini, _ = _build(tmp_path)
    assert mini.windowFlags() & Qt.WindowType.WindowTransparentForInput
    assert mini.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    mini.set_interaction_enabled(True)
    assert not mini.windowFlags() & Qt.WindowType.WindowTransparentForInput
    mini.set_interaction_enabled(False)
    assert mini.windowFlags() & Qt.WindowType.WindowTransparentForInput


def test_minimap_zooms_in_on_first_fix_only(tmp_path):
    app, state, full, mini, _ = _build(tmp_path)
    mini.show()
    mini.resize(360, 420)
    app.processEvents()
    mini.map_canvas.reset_view()
    overview = mini.map_canvas.transform().m11()
    state.update_position(Position.now(-88000, 288000, 0), "clipboard")
    zoomed = mini.map_canvas.transform().m11()
    assert zoomed > overview * 3  # a close-up, not the whole island
    # A zoom the player picks afterwards is not overridden by later fixes.
    mini.map_canvas.scale(0.5, 0.5)
    manual = mini.map_canvas.transform().m11()
    state.update_position(Position.now(-87500, 288500, 0), "clipboard")
    assert abs(mini.map_canvas.transform().m11() - manual) < 1e-9

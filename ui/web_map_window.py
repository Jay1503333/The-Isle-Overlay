"""Optional always-on-top window that shows a server's own web live map.

The window is an ordinary embedded browser. The user signs in to the map site
themselves; the Companion never sees the password, never reads the page, never
talks to the game and sends no input to it. Nothing loads until the user opens it.

"Map only" is a cosmetic, local view tweak (it hides the site's menus so the map
fills the window); it can be switched off at any time.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.overlay_interaction import apply_windows_overlay_input_style
from core.web_map import (
    clamp_web_map_opacity,
    clamp_web_map_zoom,
    map_only_script,
    sanitize_web_map_url,
)

LOGGER = logging.getLogger(__name__)

EDGE = 7  # px of draggable border on every side
DEFAULT_SIZE = (460, 440)
MIN_SIZE = (220, 180)


class WebMapWindow(QWidget):
    interaction_changed = Signal(bool)
    settings_modified = Signal()

    def __init__(self, settings: dict, profile_dir: Path) -> None:
        super().__init__()
        self._settings = settings
        self._profile_dir = profile_dir
        self._interactive = True
        self._view = None
        self._drag_offset: QPoint | None = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self._save_geometry)

        self.setWindowTitle("The Isle Companion — Live Web Map")
        self.setMinimumSize(*MIN_SIZE)
        self.setMouseTracking(True)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(
            "WebMapWindow { background: #101418; border: 1px solid #2a3540; }"
            "QLabel, QCheckBox { color: #cfe8f2; }"
            "QPushButton { padding: 1px 7px; min-width: 18px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        layout.setSpacing(0)

        self._bar = QWidget(self)
        self._bar.setMouseTracking(True)
        bar = QHBoxLayout(self._bar)
        bar.setContentsMargins(2, 0, 2, 3)
        bar.setSpacing(4)
        grab = QLabel("⠿ drag", self._bar)
        grab.setToolTip("Drag here to move. Drag any edge or corner to resize.")
        bar.addWidget(grab)
        bar.addStretch(1)

        bar.addWidget(QLabel("Opacity", self._bar))
        self._slider = QSlider(Qt.Orientation.Horizontal, self._bar)
        self._slider.setRange(30, 100)
        self._slider.setFixedWidth(70)
        self._slider.setValue(round(clamp_web_map_opacity(settings.get("web_map_opacity")) * 100))
        self._slider.valueChanged.connect(self._opacity_changed)
        bar.addWidget(self._slider)

        zoom_out = QPushButton("−", self._bar)
        zoom_out.setToolTip("Zoom the page out (smaller text and controls)")
        zoom_out.clicked.connect(lambda: self._change_zoom(-0.1))
        zoom_in = QPushButton("+", self._bar)
        zoom_in.setToolTip("Zoom the page in")
        zoom_in.clicked.connect(lambda: self._change_zoom(0.1))
        bar.addWidget(zoom_out)
        bar.addWidget(zoom_in)

        self._map_only = QCheckBox("Map only", self._bar)
        self._map_only.setToolTip("Hide the site's menus so just the map fills this window")
        self._map_only.setChecked(bool(settings.get("web_map_map_only", True)))
        self._map_only.toggled.connect(self._map_only_toggled)
        bar.addWidget(self._map_only)

        reload_button = QPushButton("⟳", self._bar)
        reload_button.setToolTip("Reload the page")
        reload_button.clicked.connect(self.reload)
        bar.addWidget(reload_button)
        lock_button = QPushButton("Lock", self._bar)
        lock_button.setToolTip(
            "Make the window click-through so clicks reach the game. "
            "Use the Edit Web Map toolbar button to unlock it."
        )
        lock_button.clicked.connect(lambda: self.set_interaction_enabled(False))
        bar.addWidget(lock_button)
        close_button = QPushButton("✕", self._bar)
        close_button.setToolTip("Hide this window")
        close_button.clicked.connect(self.hide)
        bar.addWidget(close_button)
        layout.addWidget(self._bar)

        self._body = QWidget(self)
        self._body.setMouseTracking(True)
        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._body, 1)

        geometry = settings.get("web_map_geometry")
        if isinstance(geometry, list) and len(geometry) == 4:
            try:
                x, y, w, h = (int(v) for v in geometry)
                self.setGeometry(x, y, max(MIN_SIZE[0], w), max(MIN_SIZE[1], h))
            except (TypeError, ValueError):
                self.resize(*DEFAULT_SIZE)
        else:
            self.resize(*DEFAULT_SIZE)
        self.setWindowOpacity(clamp_web_map_opacity(settings.get("web_map_opacity")))

    # -- lazy browser ---------------------------------------------------
    def _ensure_view(self) -> None:
        if self._view is not None:
            return
        try:
            from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError as exc:  # pragma: no cover - depends on install
            LOGGER.error("Qt WebEngine is not available: %s", exc)
            return
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        profile = QWebEngineProfile("TheIsleCompanionWebMap", self)
        profile.setPersistentStoragePath(str(self._profile_dir))
        profile.setCachePath(str(self._profile_dir / "cache"))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        page = QWebEnginePage(profile, self)
        self._view = QWebEngineView(self._body)
        self._view.setPage(page)
        self._view.setZoomFactor(clamp_web_map_zoom(self._settings.get("web_map_zoom")))
        self._view.loadFinished.connect(lambda _ok: self._apply_map_only())
        self._view.urlChanged.connect(lambda _url: QTimer.singleShot(400, self._apply_map_only))
        self._body.layout().addWidget(self._view)
        self._view.setUrl(QUrl(self.current_url()))

    def current_url(self) -> str:
        return sanitize_web_map_url(self._settings.get("web_map_url"))

    def reload(self) -> None:
        if self._view is not None:
            self._view.setUrl(QUrl(self.current_url()))

    def _apply_map_only(self) -> None:
        if self._view is not None:
            self._view.page().runJavaScript(map_only_script(self._map_only.isChecked()))

    def _map_only_toggled(self, enabled: bool) -> None:
        self._settings["web_map_map_only"] = bool(enabled)
        self.settings_modified.emit()
        self._apply_map_only()

    def _change_zoom(self, delta: float) -> None:
        zoom = clamp_web_map_zoom(float(self._settings.get("web_map_zoom", 1.0)) + delta)
        self._settings["web_map_zoom"] = round(zoom, 2)
        if self._view is not None:
            self._view.setZoomFactor(zoom)
        self.settings_modified.emit()

    # -- window events --------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802
        self._ensure_view()
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_input_style)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._save_geometry()
        super().hideEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._save_timer.start()

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._save_timer.start()

    def _save_geometry(self) -> None:
        self._settings["web_map_geometry"] = [self.x(), self.y(), self.width(), self.height()]
        self.settings_modified.emit()

    # -- interaction ----------------------------------------------------
    @property
    def interaction_enabled(self) -> bool:
        return self._interactive

    def set_interaction_enabled(self, enabled: bool) -> None:
        self._interactive = bool(enabled)
        self._bar.setVisible(self._interactive)
        self._apply_input_style()
        self.interaction_changed.emit(self._interactive)

    def _apply_input_style(self) -> None:
        if self.isVisible():
            apply_windows_overlay_input_style(int(self.winId()), self._interactive)

    def _opacity_changed(self, value: int) -> None:
        opacity = clamp_web_map_opacity(value / 100.0)
        self._settings["web_map_opacity"] = opacity
        self.setWindowOpacity(opacity)
        self.settings_modified.emit()

    # -- edge resize and bar drag --------------------------------------
    def _edges_at(self, pos: QPoint) -> Qt.Edge:
        edges = Qt.Edge(0)
        if pos.x() <= EDGE:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= self.width() - EDGE:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= EDGE:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= self.height() - EDGE:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _cursor_for(edges: Qt.Edge) -> Qt.CursorShape:
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            diagonal_back = bool(edges & Qt.Edge.LeftEdge) == bool(edges & Qt.Edge.TopEdge)
            return Qt.CursorShape.SizeFDiagCursor if diagonal_back else Qt.CursorShape.SizeBDiagCursor
        if horizontal:
            return Qt.CursorShape.SizeHorCursor
        if vertical:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edges = self._edges_at(pos)
            handle = self.windowHandle()
            if edges and handle is not None:
                handle.startSystemResize(edges)
                event.accept()
                return
            if pos.y() < EDGE + self._bar.height():
                if handle is not None and handle.startSystemMove():
                    event.accept()
                    return
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        self.setCursor(self._cursor_for(self._edges_at(event.position().toPoint())))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

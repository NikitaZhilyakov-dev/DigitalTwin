from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt5.QtCore import QLibraryInfo
from PyQt5.QtWidgets import QApplication

from .ui.gui_settings import THEME, render_stylesheet
from .ui.main_window import MainWindow


def _configure_qt_plugin_paths() -> None:
    """
    Явно настраивает пути плагинов Qt для macOS/venv,
    чтобы гарантированно находился platform plugin `cocoa`.
    """
    qt_plugins = Path(QLibraryInfo.location(QLibraryInfo.PluginsPath))
    if not qt_plugins.exists():
        # Fallback для wheel-структуры PyQt5 в venv.
        qt_plugins = (
            Path(__file__).resolve().parents[1]
            / ".venv"
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
            / "PyQt5"
            / "Qt5"
            / "plugins"
        )

    qt_platforms = qt_plugins / "platforms"
    if qt_plugins.exists():
        os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)
    if qt_platforms.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_platforms)


def main() -> None:
    _configure_qt_plugin_paths()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    styles_path = Path(__file__).resolve().parent / "ui" / "styles.qss"
    THEME.load_template(styles_path)
    app.setStyleSheet(THEME.current_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


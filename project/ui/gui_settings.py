from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuiSettings:
    # Window
    WINDOW_WIDTH: int = 1400
    WINDOW_HEIGHT: int = 900
    ROOT_MARGIN_LEFT: int = 16
    ROOT_MARGIN_TOP: int = 16
    ROOT_MARGIN_RIGHT: int = 16
    ROOT_MARGIN_BOTTOM: int = 16
    ROOT_SPACING: int = 14

    # Toolbar
    TOOLBAR_MARGIN_H: int = 12
    TOOLBAR_MARGIN_V: int = 10
    TOOLBAR_SPACING: int = 10
    TIME_LIMIT_WIDTH: int = 110

    # Dashboard cards
    DASHBOARD_MARGIN: int = 8
    DASHBOARD_SPACING: int = 8
    KPI_GRID_H_SPACING: int = 10
    KPI_GRID_V_SPACING: int = 8
    KPI_CARD_HEIGHT: int = 92
    KPI_CARD_MARGIN_H: int = 12
    KPI_CARD_MARGIN_V: int = 8
    KPI_CARD_SPACING: int = 4

    # Tabs
    TAB_PANE_MARGIN_TOP: int = 12
    TAB_PADDING_V: int = 8
    TAB_PADDING_H: int = 14
    TAB_MARGIN_RIGHT: int = 6
    TAB_MARGIN_BOTTOM: int = 6
    TAB_MIN_WIDTH: int = 120
    TAB_WIDTH_EXTRA_RATIO: float = 0.5
    TAB_WIDTH_EXTRA_MIN: int = 28
    TAB_WIDTH_EXTRA_HEIGHT: int = 1

    # Font sizes
    FONT_BASE_SIZE: int = 12
    FONT_KPI_TITLE_SIZE: int = 17
    FONT_KPI_VALUE_SIZE: int = 30

    # Colors
    COLOR_BG_MAIN: str = "#1e1e1e"
    COLOR_TEXT_PRIMARY: str = "#e8e8e8"
    COLOR_TEXT_MUTED: str = "#a0a0a0"

    COLOR_PANEL_BG: str = "#2b2b2b"
    COLOR_PANEL_ALT_BG: str = "#262626"
    COLOR_PANEL_BORDER: str = "#3a3a3a"
    COLOR_PANEL_DIVIDER: str = "#333333"

    COLOR_BUTTON_BG: str = "#2f2f2f"
    COLOR_BUTTON_HOVER_BG: str = "#353535"
    COLOR_BUTTON_PRESSED_BG: str = "#2a2a2a"
    COLOR_HEADER_BG: str = "#313131"
    COLOR_ROW_HOVER_BG: str = "#343434"

    COLOR_ACCENT: str = "#4aa3df"
    COLOR_ACCENT_HOVER: str = "#5ab0ea"
    COLOR_WHITE: str = "#ffffff"


_DARK_COLORS: dict[str, str] = {
    "COLOR_BG_MAIN": "#1e1e1e",
    "COLOR_TEXT_PRIMARY": "#e8e8e8",
    "COLOR_TEXT_MUTED": "#a0a0a0",
    "COLOR_PANEL_BG": "#2b2b2b",
    "COLOR_PANEL_ALT_BG": "#262626",
    "COLOR_PANEL_BORDER": "#3a3a3a",
    "COLOR_PANEL_DIVIDER": "#333333",
    "COLOR_BUTTON_BG": "#2f2f2f",
    "COLOR_BUTTON_HOVER_BG": "#353535",
    "COLOR_BUTTON_PRESSED_BG": "#2a2a2a",
    "COLOR_HEADER_BG": "#313131",
    "COLOR_ROW_HOVER_BG": "#343434",
    "COLOR_ACCENT": "#4aa3df",
    "COLOR_ACCENT_HOVER": "#5ab0ea",
    "COLOR_WHITE": "#ffffff",
}

_LIGHT_COLORS: dict[str, str] = {
    "COLOR_BG_MAIN": "#f0f0f0",
    "COLOR_TEXT_PRIMARY": "#1a1a1a",
    "COLOR_TEXT_MUTED": "#606060",
    "COLOR_PANEL_BG": "#ffffff",
    "COLOR_PANEL_ALT_BG": "#f8f8f8",
    "COLOR_PANEL_BORDER": "#d0d0d0",
    "COLOR_PANEL_DIVIDER": "#e0e0e0",
    "COLOR_BUTTON_BG": "#e8e8e8",
    "COLOR_BUTTON_HOVER_BG": "#dcdcdc",
    "COLOR_BUTTON_PRESSED_BG": "#d0d0d0",
    "COLOR_HEADER_BG": "#e4e4e4",
    "COLOR_ROW_HOVER_BG": "#eef4fb",
    "COLOR_ACCENT": "#2980b9",
    "COLOR_ACCENT_HOVER": "#3490cc",
    "COLOR_WHITE": "#ffffff",
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def interpolate_colors(
    from_colors: dict[str, str],
    to_colors: dict[str, str],
    t: float,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for key in from_colors:
        r1, g1, b1 = _hex_to_rgb(from_colors[key])
        r2, g2, b2 = _hex_to_rgb(to_colors[key])
        r = round(r1 + (r2 - r1) * t)
        g = round(g1 + (g2 - g1) * t)
        b = round(b1 + (b2 - b1) * t)
        result[key] = _rgb_to_hex(r, g, b)
    return result


class ThemeManager:
    def __init__(self) -> None:
        self._dark = True
        self._stylesheet_template: str = ""

    @property
    def is_dark(self) -> bool:
        return self._dark

    @property
    def dark_colors(self) -> dict[str, str]:
        return _DARK_COLORS

    @property
    def light_colors(self) -> dict[str, str]:
        return _LIGHT_COLORS

    def toggle(self) -> None:
        self._dark = not self._dark

    def load_template(self, path: Path) -> None:
        if path.exists():
            self._stylesheet_template = path.read_text(encoding="utf-8")

    def current_stylesheet(self) -> str:
        return self.stylesheet_for_colors(_DARK_COLORS if self._dark else _LIGHT_COLORS)

    def stylesheet_for_colors(self, colors: dict[str, str]) -> str:
        return render_stylesheet(self._stylesheet_template, colors=colors)


THEME = ThemeManager()
GUI = GuiSettings()


def render_stylesheet(
    stylesheet_template: str,
    *,
    dark: bool = True,
    colors: dict[str, str] | None = None,
) -> str:
    if colors is None:
        colors = _DARK_COLORS if dark else _LIGHT_COLORS
    token_map = {
        "@FONT_BASE_SIZE@": str(GUI.FONT_BASE_SIZE),
        "@TAB_PANE_MARGIN_TOP@": str(GUI.TAB_PANE_MARGIN_TOP),
        "@TAB_PADDING_V@": str(GUI.TAB_PADDING_V),
        "@TAB_PADDING_H@": str(GUI.TAB_PADDING_H),
        "@TAB_MARGIN_RIGHT@": str(GUI.TAB_MARGIN_RIGHT),
        "@TAB_MARGIN_BOTTOM@": str(GUI.TAB_MARGIN_BOTTOM),
        "@TAB_MIN_WIDTH@": str(GUI.TAB_MIN_WIDTH),
        "@FONT_KPI_TITLE_SIZE@": str(GUI.FONT_KPI_TITLE_SIZE),
        "@FONT_KPI_VALUE_SIZE@": str(GUI.FONT_KPI_VALUE_SIZE),
        **{f"@{k}@": v for k, v in colors.items()},
    }
    out = stylesheet_template
    for token, value in token_map.items():
        out = out.replace(token, value)
    return out

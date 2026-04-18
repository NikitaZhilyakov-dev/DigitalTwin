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
    COLOR_BG_MAIN: str = "#111318"
    COLOR_TEXT_PRIMARY: str = "#e2e4ea"
    COLOR_TEXT_MUTED: str = "#7b7f8e"

    COLOR_PANEL_BG: str = "#1c1f27"
    COLOR_PANEL_ALT_BG: str = "#181b22"
    COLOR_PANEL_BORDER: str = "#2a2e3d"
    COLOR_PANEL_DIVIDER: str = "#232736"

    COLOR_BUTTON_BG: str = "#242838"
    COLOR_BUTTON_HOVER_BG: str = "#2d3247"
    COLOR_BUTTON_PRESSED_BG: str = "#1e2230"
    COLOR_HEADER_BG: str = "#20243200"
    COLOR_ROW_HOVER_BG: str = "#2a2e42"

    COLOR_ACCENT: str = "#6366f1"
    COLOR_ACCENT_HOVER: str = "#818cf8"
    COLOR_ACCENT_ACTION: str = "#f59e0b"
    COLOR_ACCENT_ACTION_HOVER: str = "#fbbf24"
    COLOR_WHITE: str = "#ffffff"


_DARK_COLORS: dict[str, str] = {
    "COLOR_BG_MAIN": "#111318",
    "COLOR_TEXT_PRIMARY": "#e2e4ea",
    "COLOR_TEXT_MUTED": "#7b7f8e",
    "COLOR_PANEL_BG": "#1c1f27",
    "COLOR_PANEL_ALT_BG": "#181b22",
    "COLOR_PANEL_BORDER": "#2a2e3d",
    "COLOR_PANEL_DIVIDER": "#232736",
    "COLOR_BUTTON_BG": "#242838",
    "COLOR_BUTTON_HOVER_BG": "#2d3247",
    "COLOR_BUTTON_PRESSED_BG": "#1e2230",
    "COLOR_HEADER_BG": "#202432",
    "COLOR_ROW_HOVER_BG": "#2a2e42",
    "COLOR_ACCENT": "#6366f1",
    "COLOR_ACCENT_HOVER": "#818cf8",
    "COLOR_ACCENT_ACTION": "#f59e0b",
    "COLOR_ACCENT_ACTION_HOVER": "#fbbf24",
    "COLOR_WHITE": "#ffffff",
    "COLOR_STATUS_OPTIMAL_BG": "#052e16",
    "COLOR_STATUS_OPTIMAL_BORDER": "#16a34a",
    "COLOR_STATUS_OPTIMAL_TOP": "#22c55e",
    "COLOR_STATUS_OPTIMAL_TEXT": "#bbf7d0",
    "COLOR_STATUS_FEASIBLE_BG": "#1c1407",
    "COLOR_STATUS_FEASIBLE_BORDER": "#ca8a04",
    "COLOR_STATUS_FEASIBLE_TOP": "#eab308",
    "COLOR_STATUS_FEASIBLE_TEXT": "#fef08a",
    "COLOR_STATUS_PROBLEM_BG": "#1a0505",
    "COLOR_STATUS_PROBLEM_BORDER": "#dc2626",
    "COLOR_STATUS_PROBLEM_TOP": "#ef4444",
    "COLOR_STATUS_PROBLEM_TEXT": "#fecaca",
}

_LIGHT_COLORS: dict[str, str] = {
    "COLOR_BG_MAIN": "#f4f5f9",
    "COLOR_TEXT_PRIMARY": "#1a1c2a",
    "COLOR_TEXT_MUTED": "#6b7280",
    "COLOR_PANEL_BG": "#ffffff",
    "COLOR_PANEL_ALT_BG": "#f8f9fc",
    "COLOR_PANEL_BORDER": "#e2e5ef",
    "COLOR_PANEL_DIVIDER": "#ebeef5",
    "COLOR_BUTTON_BG": "#eef0f8",
    "COLOR_BUTTON_HOVER_BG": "#e4e7f4",
    "COLOR_BUTTON_PRESSED_BG": "#d8dcee",
    "COLOR_HEADER_BG": "#edf0f8",
    "COLOR_ROW_HOVER_BG": "#eef1ff",
    "COLOR_ACCENT": "#6366f1",
    "COLOR_ACCENT_HOVER": "#4f46e5",
    "COLOR_ACCENT_ACTION": "#d97706",
    "COLOR_ACCENT_ACTION_HOVER": "#b45309",
    "COLOR_WHITE": "#ffffff",
    "COLOR_STATUS_OPTIMAL_BG": "#dcfce7",
    "COLOR_STATUS_OPTIMAL_BORDER": "#16a34a",
    "COLOR_STATUS_OPTIMAL_TOP": "#22c55e",
    "COLOR_STATUS_OPTIMAL_TEXT": "#14532d",
    "COLOR_STATUS_FEASIBLE_BG": "#fef9c3",
    "COLOR_STATUS_FEASIBLE_BORDER": "#ca8a04",
    "COLOR_STATUS_FEASIBLE_TOP": "#eab308",
    "COLOR_STATUS_FEASIBLE_TEXT": "#713f12",
    "COLOR_STATUS_PROBLEM_BG": "#fee2e2",
    "COLOR_STATUS_PROBLEM_BORDER": "#dc2626",
    "COLOR_STATUS_PROBLEM_TOP": "#ef4444",
    "COLOR_STATUS_PROBLEM_TEXT": "#7f1d1d",
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
        **{f"@{k}@": v for k, v in colors.items()},
        "@FONT_BASE_SIZE@": str(GUI.FONT_BASE_SIZE),
        "@TAB_PANE_MARGIN_TOP@": str(GUI.TAB_PANE_MARGIN_TOP),
        "@TAB_PADDING_V@": str(GUI.TAB_PADDING_V),
        "@TAB_PADDING_H@": str(GUI.TAB_PADDING_H),
        "@TAB_MARGIN_RIGHT@": str(GUI.TAB_MARGIN_RIGHT),
        "@TAB_MARGIN_BOTTOM@": str(GUI.TAB_MARGIN_BOTTOM),
        "@TAB_MIN_WIDTH@": str(GUI.TAB_MIN_WIDTH),
        "@FONT_KPI_TITLE_SIZE@": str(GUI.FONT_KPI_TITLE_SIZE),
        "@FONT_KPI_VALUE_SIZE@": str(GUI.FONT_KPI_VALUE_SIZE),
    }
    out = stylesheet_template
    for token, value in token_map.items():
        out = out.replace(token, value)
    return out

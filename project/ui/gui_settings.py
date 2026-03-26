from __future__ import annotations

from dataclasses import dataclass


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


GUI = GuiSettings()


def render_stylesheet(stylesheet_template: str) -> str:
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
        "@COLOR_BG_MAIN@": GUI.COLOR_BG_MAIN,
        "@COLOR_TEXT_PRIMARY@": GUI.COLOR_TEXT_PRIMARY,
        "@COLOR_TEXT_MUTED@": GUI.COLOR_TEXT_MUTED,
        "@COLOR_PANEL_BG@": GUI.COLOR_PANEL_BG,
        "@COLOR_PANEL_ALT_BG@": GUI.COLOR_PANEL_ALT_BG,
        "@COLOR_PANEL_BORDER@": GUI.COLOR_PANEL_BORDER,
        "@COLOR_PANEL_DIVIDER@": GUI.COLOR_PANEL_DIVIDER,
        "@COLOR_BUTTON_BG@": GUI.COLOR_BUTTON_BG,
        "@COLOR_BUTTON_HOVER_BG@": GUI.COLOR_BUTTON_HOVER_BG,
        "@COLOR_BUTTON_PRESSED_BG@": GUI.COLOR_BUTTON_PRESSED_BG,
        "@COLOR_HEADER_BG@": GUI.COLOR_HEADER_BG,
        "@COLOR_ROW_HOVER_BG@": GUI.COLOR_ROW_HOVER_BG,
        "@COLOR_ACCENT@": GUI.COLOR_ACCENT,
        "@COLOR_ACCENT_HOVER@": GUI.COLOR_ACCENT_HOVER,
        "@COLOR_WHITE@": GUI.COLOR_WHITE,
    }
    out = stylesheet_template
    for token, value in token_map.items():
        out = out.replace(token, value)
    return out

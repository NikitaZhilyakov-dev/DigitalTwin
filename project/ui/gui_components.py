from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import QDate, QSize, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import (
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .dashboard_widget import DashboardWidget
from .gantt_widget import GanttWidget
from .gui_settings import GUI
from .machine_load_widget import MachineLoadWidget
from .priority_widget import PriorityWidget
from .table_widget import OperationsTableWidget


def create_button(text: str, *, object_name: str | None = None) -> QPushButton:
    button = QPushButton(text)
    if object_name:
        button.setObjectName(object_name)
    return button


def create_time_limit_spinbox() -> QSpinBox:
    spinbox = QSpinBox()
    spinbox.setRange(1, 300)
    spinbox.setValue(30)
    spinbox.setSuffix(" сек")
    spinbox.setFixedWidth(GUI.TIME_LIMIT_WIDTH)
    return spinbox


@dataclass(frozen=True)
class ToolbarBundle:
    frame: QFrame
    load_btn: QPushButton
    run_btn: QPushButton
    time_limit: QSpinBox
    csv_file_badge: QLabel
    theme_btn: QPushButton
    planning_date_edit: QDateEdit


def create_toolbar() -> ToolbarBundle:
    toolbar_frame = QFrame()
    toolbar_frame.setObjectName("toolbarPanel")

    controls_layout = QHBoxLayout(toolbar_frame)
    controls_layout.setContentsMargins(
        GUI.TOOLBAR_MARGIN_H,
        GUI.TOOLBAR_MARGIN_V,
        GUI.TOOLBAR_MARGIN_H,
        GUI.TOOLBAR_MARGIN_V,
    )
    controls_layout.setSpacing(GUI.TOOLBAR_SPACING)

    load_btn = create_button("Загрузить CSV")
    run_btn = create_button("Запустить оптимизацию", object_name="accentButton")
    time_limit = create_time_limit_spinbox()
    csv_file_badge = QLabel("CSV не выбран")
    csv_file_badge.setObjectName("csvFileBadge")
    csv_file_badge.setProperty("loadState", "neutral")
    csv_file_badge.setAlignment(Qt.AlignCenter)
    csv_file_badge.setMinimumWidth(220)
    time_limit_label = QLabel("Лимит времени:")
    time_limit_label.setObjectName("timeLimitLabel")

    planning_date_label = QLabel("Дата начала:")
    planning_date_label.setObjectName("timeLimitLabel")
    planning_date_edit = QDateEdit()
    planning_date_edit.setCalendarPopup(True)
    planning_date_edit.setDate(QDate(2026, 3, 25))
    planning_date_edit.setDisplayFormat("dd.MM.yyyy")
    planning_date_edit.setFixedWidth(120)

    theme_btn = create_button("☀  Светлая")
    theme_btn.setObjectName("themeToggleBtn")
    theme_btn.setFixedWidth(140)

    controls_layout.addWidget(load_btn)
    controls_layout.addWidget(csv_file_badge)
    controls_layout.addWidget(time_limit_label)
    controls_layout.addWidget(time_limit)
    controls_layout.addWidget(planning_date_label)
    controls_layout.addWidget(planning_date_edit)
    controls_layout.addWidget(run_btn)
    controls_layout.addStretch(1)
    controls_layout.addWidget(theme_btn)

    return ToolbarBundle(
        frame=toolbar_frame,
        load_btn=load_btn,
        run_btn=run_btn,
        time_limit=time_limit,
        csv_file_badge=csv_file_badge,
        theme_btn=theme_btn,
        planning_date_edit=planning_date_edit,
    )


class MainTabBar(QTabBar):
    def __init__(self, widened_indices: set[int]) -> None:
        super().__init__()
        self._widened_indices = widened_indices
        self.setDrawBase(False)

    def tabSizeHint(self, index: int) -> QSize:
        size = super().tabSizeHint(index)
        if index in self._widened_indices:
            extra_width = max(GUI.TAB_WIDTH_EXTRA_MIN, int(size.width() * GUI.TAB_WIDTH_EXTRA_RATIO))
            size.setWidth(size.width() + extra_width)
        return size


class NoWheelScrollArea(QScrollArea):
    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        event.ignore()


@dataclass(frozen=True)
class MainTabsBundle:
    tabs: QTabWidget
    dashboard_widget: DashboardWidget
    gantt_machine_widget: GanttWidget
    gantt_product_widget: GanttWidget
    machine_load_widget: MachineLoadWidget
    table_widget: OperationsTableWidget
    machine_table_widget: OperationsTableWidget
    priority_widget: PriorityWidget


def create_main_tabs() -> MainTabsBundle:
    tabs = QTabWidget()
    tabs.setTabBar(MainTabBar({1, 2, 4}))
    tabs.setObjectName("mainTabs")

    dashboard_widget = DashboardWidget()
    gantt_machine_widget = GanttWidget(mode="machine")
    gantt_machine_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    gantt_machine_widget.setMinimumHeight(460)
    gantt_product_widget = GanttWidget(mode="product")
    gantt_product_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    gantt_product_widget.setMinimumHeight(460)
    machine_load_widget = MachineLoadWidget()
    table_widget = OperationsTableWidget()
    machine_table_widget = OperationsTableWidget(
        columns=["machine", "product", "part_number", "process", "start_datetime", "end_datetime", "duration"]
    )
    priority_widget = PriorityWidget()

    machine_tab_content = QWidget()
    machine_tab_layout = QVBoxLayout(machine_tab_content)
    machine_tab_layout.setContentsMargins(0, 0, 0, 0)
    machine_tab_layout.setSpacing(8)
    machine_tab_layout.addWidget(gantt_machine_widget)
    machine_tab_layout.addWidget(machine_table_widget)
    machine_tab_layout.addStretch(1)

    machine_tab_scroll = NoWheelScrollArea()
    machine_tab_scroll.setWidgetResizable(True)
    machine_tab_scroll.setWidget(machine_tab_content)

    product_tab_content = QWidget()
    product_tab_layout = QVBoxLayout(product_tab_content)
    product_tab_layout.setContentsMargins(0, 0, 0, 0)
    product_tab_layout.setSpacing(8)
    product_tab_layout.addWidget(gantt_product_widget)
    product_tab_layout.addWidget(table_widget)
    product_tab_layout.addStretch(1)

    product_tab_scroll = NoWheelScrollArea()
    product_tab_scroll.setWidgetResizable(True)
    product_tab_scroll.setWidget(product_tab_content)

    dashboard_tab_scroll = NoWheelScrollArea()
    dashboard_tab_scroll.setWidgetResizable(True)
    dashboard_tab_scroll.setWidget(dashboard_widget)

    tabs.addTab(dashboard_tab_scroll, "Dashboard")
    tabs.addTab(machine_tab_scroll, "Gantt chart (станки)")
    tabs.addTab(product_tab_scroll, "Gantt chart (изделия)")
    tabs.addTab(machine_load_widget, "Загрузка станков")
    tabs.addTab(priority_widget, "Приоритет продукции")

    return MainTabsBundle(
        tabs=tabs,
        dashboard_widget=dashboard_widget,
        gantt_machine_widget=gantt_machine_widget,
        gantt_product_widget=gantt_product_widget,
        machine_load_widget=machine_load_widget,
        table_widget=table_widget,
        machine_table_widget=machine_table_widget,
        priority_widget=priority_widget,
    )

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from .gui_settings import GUI


class DashboardWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            GUI.DASHBOARD_MARGIN,
            GUI.DASHBOARD_MARGIN,
            GUI.DASHBOARD_MARGIN,
            GUI.DASHBOARD_MARGIN,
        )
        layout.setSpacing(GUI.DASHBOARD_SPACING)

        grid = QGridLayout()
        grid.setHorizontalSpacing(GUI.KPI_GRID_H_SPACING)
        grid.setVerticalSpacing(GUI.KPI_GRID_V_SPACING)
        layout.addLayout(grid)
        layout.addStretch(1)

        self._value_labels: dict[str, QLabel] = {}
        self._subtitle_labels: dict[str, QLabel] = {}
        cards = [
            ("makespan", "Makespan (мин)", None, 0, 0),
            ("operations_count", "Количество операций", None, 0, 1),
            ("machines_count", "Количество станков", None, 0, 2),
            (
                "max_utilization_pct",
                "Максимальная загрузка станка",
                "max_utilization_machine_name",
                1,
                0,
            ),
            (
                "min_utilization_pct",
                "Минимальная загрузка станка",
                "min_utilization_machine_name",
                1,
                1,
            ),
        ]

        for value_key, title, subtitle_key, row, col in cards:
            card = QFrame()
            card.setObjectName("kpiCard")
            card.setFixedHeight(GUI.KPI_CARD_HEIGHT)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(
                GUI.KPI_CARD_MARGIN_H,
                GUI.KPI_CARD_MARGIN_V,
                GUI.KPI_CARD_MARGIN_H,
                GUI.KPI_CARD_MARGIN_V,
            )
            card_layout.setSpacing(GUI.KPI_CARD_SPACING)

            title_label = QLabel(title)
            title_label.setObjectName("kpiTitle")

            if subtitle_key:
                subtitle_label = QLabel("-")
                subtitle_label.setObjectName("kpiSubtitle")
                subtitle_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                card_layout.addWidget(title_label)
                card_layout.addWidget(subtitle_label)
                self._subtitle_labels[subtitle_key] = subtitle_label
            else:
                card_layout.addWidget(title_label)

            value_label = QLabel("-")
            value_label.setObjectName("kpiValue")
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            card_layout.addWidget(value_label)
            grid.addWidget(card, row, col)
            self._value_labels[value_key] = value_label

    def update_metrics(self, metrics: dict) -> None:
        self._value_labels["makespan"].setText(f"{float(metrics.get('makespan', 0)):.0f}")
        self._value_labels["operations_count"].setText(str(int(metrics.get("operations_count", 0))))
        self._value_labels["machines_count"].setText(str(int(metrics.get("machines_count", 0))))
        self._value_labels["max_utilization_pct"].setText(
            f"{float(metrics.get('max_utilization_pct', 0)):.1f}%"
        )
        self._value_labels["min_utilization_pct"].setText(
            f"{float(metrics.get('min_utilization_pct', 0)):.1f}%"
        )
        self._subtitle_labels["max_utilization_machine_name"].setText(
            str(metrics.get("max_utilization_machine_name", "-"))
        )
        self._subtitle_labels["min_utilization_machine_name"].setText(
            str(metrics.get("min_utilization_machine_name", "-"))
        )

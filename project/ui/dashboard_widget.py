from __future__ import annotations

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtWidgets import QStyle
from PyQt5.QtWidgets import QStyleOptionViewItem
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from .gui_settings import GUI


class NoWheelTableWidget(QTableWidget):
    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        event.ignore()


class ChangesColorDelegate(QStyledItemDelegate):
    RED_BG = QColor("#cc3333")
    GREEN_BG = QColor("#2e9b4f")
    WHITE_FG = QColor("#ffffff")

    @staticmethod
    def _to_number(value: object) -> float:
        s = str(value).strip().replace(",", ".").replace(" ", "")
        parsed = pd.to_numeric(pd.Series([s]), errors="coerce").iloc[0]
        return float(parsed) if pd.notna(parsed) else float("nan")

    def _color_for_cell(self, index) -> tuple[QColor, QColor] | None:
        model = index.model()
        headers = {
            str(model.headerData(c, Qt.Horizontal)): c for c in range(model.columnCount())
        }
        col_name = str(model.headerData(index.column(), Qt.Horizontal))
        row = index.row()

        if col_name == "new_processing_hours":
            old_col = headers.get("old_processing_hours")
            if old_col is None:
                return None
            old_v = self._to_number(model.index(row, old_col).data())
            new_v = self._to_number(index.data())
            if pd.notna(old_v) and pd.notna(new_v):
                if new_v > old_v:
                    return self.RED_BG, self.WHITE_FG
                if new_v < old_v:
                    return self.GREEN_BG, self.WHITE_FG

        if col_name == "difference_time":
            txt = str(index.data()).strip()
            if "+" in txt:
                return self.RED_BG, self.WHITE_FG
            if "-" in txt:
                return self.GREEN_BG, self.WHITE_FG

        return None

    def initStyleOption(self, option, index) -> None:  # type: ignore[override]
        super().initStyleOption(option, index)
        colors = self._color_for_cell(index)
        if colors is None:
            return
        bg, fg = colors
        option.backgroundBrush = QBrush(bg)
        option.palette.setBrush(option.palette.Text, QBrush(fg))
        option.palette.setBrush(option.palette.HighlightedText, QBrush(fg))

    def paint(self, painter, option, index) -> None:  # type: ignore[override]
        colors = self._color_for_cell(index)
        if colors is None:
            super().paint(painter, option, index)
            return
        bg, fg = colors
        painter.save()
        painter.fillRect(option.rect, bg)
        forced = QStyleOptionViewItem(option)
        # Убираем состояние "selected", чтобы стандартный selection не перекрашивал ячейку.
        forced.state = forced.state & ~QStyle.State_Selected
        forced.palette.setColor(forced.palette.Text, fg)
        forced.palette.setColor(forced.palette.WindowText, fg)
        super().paint(painter, forced, index)
        painter.restore()


class DashboardWidget(QWidget):
    operational_schedule_changed = pyqtSignal(object)

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

        self._operational_title = QLabel("Фактическое расписание после оптимизации (основная таблица)")
        self._operational_title.setObjectName("kpiTitle")
        layout.addWidget(self._operational_title)
        self._operational_table = NoWheelTableWidget(0, 0)
        self._operational_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self._operational_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._operational_table.setAlternatingRowColors(False)
        self._operational_table.setShowGrid(False)
        self._operational_table.setWordWrap(False)
        self._operational_table.verticalHeader().setVisible(False)
        self._operational_table.horizontalHeader().setStretchLastSection(False)
        self._operational_table.setSortingEnabled(False)
        layout.addWidget(self._operational_table)
        self._set_table_visible_rows_height(self._operational_table, 0, max_rows=12)
        self._operational_title.hide()
        self._operational_table.hide()

        self._changes_title = QLabel("Изменения process_hours и обновленное раписание для измененных process_hours")
        self._changes_title.setObjectName("kpiTitle")
        layout.addWidget(self._changes_title)
        self._changes_table = NoWheelTableWidget(0, 0)
        self._changes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._changes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._changes_table.setAlternatingRowColors(False)
        self._changes_table.setShowGrid(False)
        self._changes_table.setWordWrap(False)
        self._changes_table.verticalHeader().setVisible(False)
        self._changes_table.horizontalHeader().setStretchLastSection(False)
        self._changes_table.setItemDelegate(ChangesColorDelegate(self._changes_table))
        layout.addWidget(self._changes_table)

        self._set_table_visible_rows_height(self._changes_table, 0, max_rows=10)
        self._changes_title.hide()
        self._changes_table.hide()

        self._overall_impact_title = QLabel("Обновленное общее расписание")
        self._overall_impact_title.setObjectName("kpiTitle")
        layout.addWidget(self._overall_impact_title)
        self._overall_impact_table = NoWheelTableWidget(0, 0)
        self._overall_impact_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._overall_impact_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._overall_impact_table.setAlternatingRowColors(False)
        self._overall_impact_table.setShowGrid(False)
        self._overall_impact_table.setWordWrap(False)
        self._overall_impact_table.verticalHeader().setVisible(False)
        self._overall_impact_table.horizontalHeader().setStretchLastSection(False)
        self._overall_impact_table.setItemDelegate(ChangesColorDelegate(self._overall_impact_table))
        layout.addWidget(self._overall_impact_table)

        self._set_table_visible_rows_height(self._overall_impact_table, 0, max_rows=12)
        self._overall_impact_title.hide()
        self._overall_impact_table.hide()

        self._operational_df = pd.DataFrame()
        self._operational_op_keys: list[str] = []
        self._operational_locked_keys: set[str] = set()
        self._operational_duration_col_idx = -1
        self._is_updating_operational = False
        self._operational_table.cellChanged.connect(self._on_operational_cell_changed)
        layout.addStretch(1)

        self._value_labels: dict[str, QLabel] = {}
        self._subtitle_labels: dict[str, QLabel] = {}
        self._status_card: QFrame | None = None
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
            ("solver_status_message", "Статус решения", None, 1, 2),
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
            if value_key == "solver_status_message":
                self._status_card = card

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
        self._value_labels["solver_status_message"].setText(
            str(metrics.get("solver_status_message", "-"))
        )
        self._apply_status_card_style(str(metrics.get("solver_status_level", "neutral")))
        self._subtitle_labels["max_utilization_machine_name"].setText(
            str(metrics.get("max_utilization_machine_name", "-"))
        )
        self._subtitle_labels["min_utilization_machine_name"].setText(
            str(metrics.get("min_utilization_machine_name", "-"))
        )

    def _apply_status_card_style(self, status_level: str) -> None:
        if self._status_card is None:
            return
        level = status_level if status_level in {"optimal", "feasible", "problem"} else "neutral"
        self._status_card.setProperty("statusLevel", level)
        style = self._status_card.style()
        style.unpolish(self._status_card)
        style.polish(self._status_card)
        self._status_card.update()

    def _set_table_visible_rows_height(
        self,
        table: QTableWidget,
        rows_count: int,
        max_rows: int,
    ) -> None:
        visible_rows = min(max(rows_count, 1), max_rows)
        header_height = table.horizontalHeader().height()
        row_height = table.verticalHeader().defaultSectionSize()
        frame_height = table.frameWidth() * 2
        h_scroll_height = table.horizontalScrollBar().sizeHint().height()
        target_height = frame_height + header_height + (visible_rows * row_height) + h_scroll_height
        table.setMinimumHeight(target_height)
        table.setMaximumHeight(target_height)

    def update_operational_schedule(
        self,
        source_df: pd.DataFrame,
        locked_op_keys: list[str] | None = None,
    ) -> None:
        table = self._operational_table
        self._is_updating_operational = True
        table.blockSignals(True)
        table.setRowCount(0)
        table.setColumnCount(0)
        self._operational_df = source_df.copy()
        self._operational_locked_keys = set(str(k) for k in (locked_op_keys or []))
        if source_df.empty:
            self._operational_op_keys = []
            self._operational_duration_col_idx = -1
            self._set_table_visible_rows_height(table, 0, max_rows=12)
            table.blockSignals(False)
            self._is_updating_operational = False
            self._operational_title.hide()
            self._operational_table.hide()
            return

        hidden_cols = {"op_key"}
        columns = [str(c) for c in source_df.columns.tolist() if str(c) not in hidden_cols]
        self._operational_df = source_df[columns].copy()
        self._operational_op_keys = (
            source_df["op_key"].astype(str).tolist() if "op_key" in source_df.columns else []
        )
        self._operational_duration_col_idx = (
            columns.index("duration") if "duration" in columns else -1
        )
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)

        rows_count = len(self._operational_df)
        table.setRowCount(rows_count)
        for row_idx, row in self._operational_df.reset_index(drop=True).iterrows():
            for col_idx, column in enumerate(columns):
                item = QTableWidgetItem(str(row[column]))
                item.setTextAlignment(Qt.AlignCenter)
                if col_idx != self._operational_duration_col_idx:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_idx, col_idx, item)

        self._apply_operational_locks()
        table.horizontalHeader().setSectionResizeMode(table.horizontalHeader().Stretch)
        self._set_table_visible_rows_height(table, rows_count, max_rows=12)
        table.blockSignals(False)
        self._is_updating_operational = False
        self._operational_title.show()
        self._operational_table.show()

    def _apply_operational_locks(self) -> None:
        if self._operational_duration_col_idx < 0:
            return
        if not self._operational_op_keys:
            return
        for row_idx in range(self._operational_table.rowCount()):
            item = self._operational_table.item(row_idx, self._operational_duration_col_idx)
            if item is None:
                continue
            op_key = (
                self._operational_op_keys[row_idx]
                if row_idx < len(self._operational_op_keys)
                else ""
            )
            is_locked = op_key in self._operational_locked_keys
            if is_locked:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setBackground(QBrush(QColor("#3a3a3a")))
            else:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                item.setBackground(QBrush())

    def update_changes_tables(self, merged_df: pd.DataFrame, overall_impact_df: pd.DataFrame) -> None:
        self._fill_readonly_table(self._changes_table, merged_df, max_rows=10)
        has_rows = not merged_df.empty
        self._changes_title.setVisible(has_rows)
        self._changes_table.setVisible(has_rows)
        self._fill_readonly_table(self._overall_impact_table, overall_impact_df, max_rows=12)
        has_impact_rows = not overall_impact_df.empty
        self._overall_impact_title.setVisible(has_impact_rows)
        self._overall_impact_table.setVisible(has_impact_rows)

    def _fill_readonly_table(self, table: QTableWidget, df: pd.DataFrame, max_rows: int) -> None:
        table.setSortingEnabled(False)
        table.setRowCount(0)
        table.setColumnCount(0)
        if df.empty:
            self._set_table_visible_rows_height(table, 0, max_rows=max_rows)
            table.setSortingEnabled(True)
            return

        columns = [str(c) for c in df.columns.tolist()]
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(df))
        for row_idx, row in df.reset_index(drop=True).iterrows():
            for col_idx, column in enumerate(columns):
                item = QTableWidgetItem(str(row[column]))
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_idx, col_idx, item)
        table.horizontalHeader().setSectionResizeMode(table.horizontalHeader().Stretch)
        self._set_table_visible_rows_height(table, len(df), max_rows=max_rows)
        table.setSortingEnabled(True)
        table.viewport().update()

    def _on_operational_cell_changed(self, row: int, column: int) -> None:
        if self._is_updating_operational or self._operational_df.empty:
            return
        if column != self._operational_duration_col_idx:
            return
        item = self._operational_table.item(row, column)
        if item is None:
            return
        self._operational_df.iat[row, column] = item.text()
        updated = self._operational_df.copy()
        if self._operational_op_keys:
            updated["op_key"] = self._operational_op_keys
        self.operational_schedule_changed.emit(updated)

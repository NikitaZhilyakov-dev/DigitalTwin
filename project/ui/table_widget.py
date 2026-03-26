from __future__ import annotations

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class OperationsTableWidget(QWidget):
    DEFAULT_COLUMNS = ["product", "part_number", "process", "machine", "start_datetime", "end_datetime", "duration"]
    MAX_VISIBLE_ROWS = 20

    def __init__(self, columns: list[str] | None = None) -> None:
        super().__init__()
        self.columns = columns or self.DEFAULT_COLUMNS
        self.table = QTableWidget(0, len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.table)
        self._set_table_visible_rows_height(0)

    def _set_table_visible_rows_height(self, rows_count: int) -> None:
        visible_rows = min(max(rows_count, 1), self.MAX_VISIBLE_ROWS)
        header_height = self.table.horizontalHeader().height()
        row_height = self.table.verticalHeader().defaultSectionSize()
        frame_height = self.table.frameWidth() * 2
        h_scroll_height = self.table.horizontalScrollBar().sizeHint().height()
        target_height = frame_height + header_height + (visible_rows * row_height) + h_scroll_height
        self.table.setMinimumHeight(target_height)
        self.table.setMaximumHeight(target_height)

    def update_table(self, schedule_df: pd.DataFrame) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        if schedule_df.empty:
            self._set_table_visible_rows_height(0)
            self.table.setSortingEnabled(True)
            return

        data = schedule_df[self.columns].copy()
        self.table.setRowCount(len(data))
        for row_idx, row in data.reset_index(drop=True).iterrows():
            for col_idx, column in enumerate(self.columns):
                item = QTableWidgetItem(str(row[column]))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)
        self.table.horizontalHeader().setSectionResizeMode(self.table.horizontalHeader().Stretch)
        self._set_table_visible_rows_height(len(data))
        self.table.setSortingEnabled(True)

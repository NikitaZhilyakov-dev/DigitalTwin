from __future__ import annotations

import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _PriorityTable(QTableWidget):
    row_moved = pyqtSignal(int, int)

    def __init__(self) -> None:
        super().__init__(0, 2)
        self._drag_row = -1
        self.setHorizontalHeaderLabels(["priority_rank", "product"])
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDragDropOverwriteMode(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setObjectName("priorityTable")

    def mousePressEvent(self, event) -> None:
        self._drag_row = self.indexAt(event.pos()).row()
        super().mousePressEvent(event)

    def dropEvent(self, event) -> None:
        source_row = self._drag_row
        if source_row < 0:
            event.ignore()
            return

        target_row = self.indexAt(event.pos()).row()
        if target_row < 0:
            target_row = self.rowCount()
        elif self.dropIndicatorPosition() == QAbstractItemView.BelowItem:
            target_row += 1

        if target_row > source_row:
            target_row -= 1
        if target_row == source_row:
            event.accept()
            self._drag_row = -1
            return
        event.accept()
        self._drag_row = -1
        self.row_moved.emit(source_row, target_row)


class PriorityWidget(QWidget):
    priority_changed = pyqtSignal(pd.DataFrame)

    def __init__(self) -> None:
        super().__init__()
        self._products_order: list[str] = []
        self.table = _PriorityTable()
        self.table.row_moved.connect(self._on_row_moved)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        hint = QLabel("Перетащите строку, чтобы изменить приоритет продукции")
        hint.setObjectName("hintLabel")
        layout.addWidget(hint)
        layout.addWidget(self.table)

    def update_products(self, products: list[str]) -> None:
        self._products_order = [str(p) for p in products]
        self._render_table()
        self._emit_priority()

    def _on_row_moved(self, source_row: int, target_row: int) -> None:
        if source_row < 0 or source_row >= len(self._products_order):
            return
        if target_row < 0:
            target_row = 0
        if target_row >= len(self._products_order):
            target_row = len(self._products_order) - 1
        product = self._products_order.pop(source_row)
        self._products_order.insert(target_row, product)
        self._render_table(selected_row=target_row)
        self._emit_priority()

    def _render_table(self, selected_row: int = -1) -> None:
        self.table.setRowCount(len(self._products_order))
        for idx, product in enumerate(self._products_order):
            rank_item = QTableWidgetItem(str(idx + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            product_item = QTableWidgetItem(str(product))
            self.table.setItem(idx, 0, rank_item)
            self.table.setItem(idx, 1, product_item)
        if 0 <= selected_row < self.table.rowCount():
            self.table.selectRow(selected_row)
        self.table.resizeColumnsToContents()

    def _normalize_ranks(self) -> None:
        self._render_table()
        self._emit_priority()

    def get_priority_df(self) -> pd.DataFrame:
        rows = []
        for row in range(self.table.rowCount()):
            rank_item = self.table.item(row, 0)
            product_item = self.table.item(row, 1)
            if rank_item is None or product_item is None:
                continue
            product_name = product_item.text().strip()
            if not product_name:
                continue
            rows.append(
                {
                    "priority_rank": int(rank_item.text()),
                    "product": product_name,
                }
            )
        return pd.DataFrame(rows)

    def _emit_priority(self) -> None:
        self.priority_changed.emit(self.get_priority_df())

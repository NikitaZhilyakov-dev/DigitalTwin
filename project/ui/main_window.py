from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt5.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..ui_backend import run_scheduler
from ..ui_utils import calculate_metrics
from .gui_components import create_main_tabs, create_toolbar
from .gui_settings import GUI


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Digital Twin MES - Планирование загрузки станков")
        self.resize(GUI.WINDOW_WIDTH, GUI.WINDOW_HEIGHT)

        self.input_df = pd.DataFrame()
        self.schedule_df = pd.DataFrame()
        self.priority_df = pd.DataFrame(columns=["priority_rank", "product"])
        self.machine_name_map: dict[str, str] = {}

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(
            GUI.ROOT_MARGIN_LEFT,
            GUI.ROOT_MARGIN_TOP,
            GUI.ROOT_MARGIN_RIGHT,
            GUI.ROOT_MARGIN_BOTTOM,
        )
        root_layout.setSpacing(GUI.ROOT_SPACING)

        toolbar_bundle = create_toolbar()
        self.load_btn = toolbar_bundle.load_btn
        self.run_btn = toolbar_bundle.run_btn
        self.time_limit = toolbar_bundle.time_limit
        root_layout.addWidget(toolbar_bundle.frame)

        tabs_bundle = create_main_tabs()
        self.tabs = tabs_bundle.tabs
        self.dashboard_widget = tabs_bundle.dashboard_widget
        self.gantt_machine_widget = tabs_bundle.gantt_machine_widget
        self.gantt_product_widget = tabs_bundle.gantt_product_widget
        self.machine_load_widget = tabs_bundle.machine_load_widget
        self.table_widget = tabs_bundle.table_widget
        self.machine_table_widget = tabs_bundle.machine_table_widget
        self.priority_widget = tabs_bundle.priority_widget
        root_layout.addWidget(self.tabs)

        self.load_btn.clicked.connect(self._load_csv)
        self.run_btn.clicked.connect(self._run_optimization)
        self.priority_widget.priority_changed.connect(self._on_priority_changed)

    def _load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите входной CSV",
            str(Path.cwd()),
            "CSV files (*.csv)",
        )
        if not path:
            return
        try:
            self.input_df = pd.read_csv(path, sep=";", dtype=str)
            self.machine_name_map = self._build_machine_name_map(self.input_df)
            products = (
                self.input_df["product"].dropna().astype(str).drop_duplicates().tolist()
                if "product" in self.input_df.columns
                else []
            )
            self.priority_widget.update_products(products)
            QMessageBox.information(self, "Успех", f"CSV загружен: {Path(path).name}")
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить CSV:\n{exc}")

    def _run_optimization(self) -> None:
        if self.input_df.empty:
            QMessageBox.warning(self, "Нет данных", "Сначала загрузите CSV файл.")
            return
        try:
            schedule_df = run_scheduler(
                data=self.input_df,
                priority_df=self.priority_df,
                time_limit_seconds=int(self.time_limit.value()),
            )
            self.schedule_df = self._localize_machine_names(schedule_df)
            self._refresh_tabs()
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Ошибка оптимизации", str(exc))

    def _refresh_tabs(self) -> None:
        if self.schedule_df.empty:
            QMessageBox.warning(self, "Пустой результат", "Оптимизация не вернула расписание.")
            return

        metrics = calculate_metrics(self.schedule_df)
        util_series = metrics.get("utilization_by_machine", pd.Series(dtype=float))
        metrics["max_utilization_pct"] = float(util_series.max()) if not util_series.empty else 0.0
        metrics["min_utilization_pct"] = float(util_series.min()) if not util_series.empty else 0.0
        metrics["machines_count"] = int(util_series.shape[0]) if not util_series.empty else 0
        metrics["max_utilization_machine_name"] = (
            str(util_series.idxmax()) if not util_series.empty else "-"
        )
        metrics["min_utilization_machine_name"] = (
            str(util_series.idxmin()) if not util_series.empty else "-"
        )

        self.dashboard_widget.update_metrics(metrics)
        self.gantt_machine_widget.update_chart(self.schedule_df)
        self.gantt_product_widget.update_chart(self.schedule_df)
        self.machine_load_widget.update_chart(util_series)
        self.machine_table_widget.update_table(self.schedule_df)
        self.table_widget.update_table(self.schedule_df)

    def _on_priority_changed(self, priority_df: pd.DataFrame) -> None:
        self.priority_df = priority_df

    @staticmethod
    def _build_machine_name_map(input_df: pd.DataFrame) -> dict[str, str]:
        if "machine" not in input_df.columns:
            return {}
        machines = input_df["machine"].dropna().astype(str).drop_duplicates().tolist()
        return {machine: machine for machine in machines}

    def _localize_machine_names(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        if schedule_df.empty or "machine" not in schedule_df.columns:
            return schedule_df
        out = schedule_df.copy()
        out["machine"] = out["machine"].astype(str).map(
            lambda m: self.machine_name_map.get(m, str(m))
        )
        return out

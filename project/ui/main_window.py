from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from PyQt5.QtCore import QObject, QThread, QTimeLine, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QVBoxLayout,
    QWidget,
)

from PyQt5.QtWidgets import QApplication

from ..scheduler import SolveResult
from ..ui_backend import run_scheduler
from ..ui_utils import calculate_metrics
from .gui_components import create_main_tabs, create_toolbar
from .gui_settings import GUI, THEME, interpolate_colors


class OptimizationWorker(QObject):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal(object, object, object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        data: pd.DataFrame,
        baseline_data: pd.DataFrame,
        priority_df: pd.DataFrame,
        time_limit_seconds: int,
    ) -> None:
        super().__init__()
        self._data = data.copy()
        self._baseline_data = baseline_data.copy()
        self._priority_df = priority_df.copy()
        self._time_limit_seconds = int(time_limit_seconds)

    @pyqtSlot()
    def run(self) -> None:
        try:
            baseline_schedule_df = pd.DataFrame()
            if not self._baseline_data.empty:
                self.progress_changed.emit(5, "Расчет базового расписания")
                baseline_schedule_df, _ = run_scheduler(
                    data=self._baseline_data,
                    priority_df=self._priority_df,
                    time_limit_seconds=self._time_limit_seconds,
                    progress_callback=lambda v, m: self.progress_changed.emit(
                        max(5, min(45, int(5 + v * 0.4))), str(m)
                    ),
                )
                self.progress_changed.emit(50, "Расчет обновленного расписания")
            effective_data = self._build_effective_input_data(self._data, baseline_schedule_df)
            schedule_df, solve_result = run_scheduler(
                data=effective_data,
                priority_df=self._priority_df,
                time_limit_seconds=self._time_limit_seconds,
                progress_callback=lambda v, m: self.progress_changed.emit(
                    max(50, min(100, int(50 + v * 0.5))), str(m)
                ),
            )
            self.finished.emit(schedule_df, solve_result, baseline_schedule_df)
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))

    @staticmethod
    def _to_numeric_hours(series: pd.Series) -> pd.Series:
        return pd.to_numeric(
            series.astype(str).str.replace(",", ".", regex=False).str.strip(),
            errors="coerce",
        )

    @staticmethod
    def _build_op_key(df: pd.DataFrame) -> pd.Series:
        return (
            df["product"].astype(str)
            + "|"
            + df["assembly"].astype(str)
            + "|"
            + df["part_number"].astype(str)
            + "|"
            + df["process_sequence"].astype(str)
            + "|"
            + df["process"].astype(str)
            + "|"
            + df["machine"].astype(str)
        )

    def _build_effective_input_data(
        self,
        source_df: pd.DataFrame,
        baseline_schedule_df: pd.DataFrame,
    ) -> pd.DataFrame:
        if source_df.empty or baseline_schedule_df.empty:
            return source_df.copy()
        required = ["product", "assembly", "part_number", "process_sequence", "process", "machine"]
        if not all(c in baseline_schedule_df.columns for c in required):
            return source_df.copy()

        now_ts = pd.Timestamp(datetime.now())
        baseline = baseline_schedule_df.copy()
        baseline["op_key"] = self._build_op_key(baseline)
        baseline["start_datetime"] = pd.to_datetime(baseline["start_datetime"], errors="coerce")
        baseline["end_datetime"] = pd.to_datetime(baseline["end_datetime"], errors="coerce")
        baseline["start_time"] = pd.to_numeric(baseline["start_time"], errors="coerce")
        baseline["duration"] = pd.to_numeric(baseline["duration"], errors="coerce")

        baseline = baseline.dropna(subset=["op_key", "start_datetime", "end_datetime", "start_time", "duration"])
        if baseline.empty:
            return source_df.copy()

        effective = source_df.copy()
        if "op_key" not in effective.columns and all(c in effective.columns for c in required):
            effective["op_key"] = self._build_op_key(effective)
        if "op_key" not in effective.columns:
            return source_df.copy()

        baseline_small = baseline[["op_key", "start_datetime", "end_datetime", "start_time", "duration"]].drop_duplicates(
            subset=["op_key"], keep="last"
        )
        merged = effective.merge(baseline_small, on="op_key", how="left")
        merged["processing_hours"] = self._to_numeric_hours(merged["processing_hours"])

        in_progress_mask = (merged["start_datetime"] < now_ts) & (merged["end_datetime"] > now_ts)
        if in_progress_mask.any():
            elapsed_frac = (
                (now_ts - merged.loc[in_progress_mask, "start_datetime"]).dt.total_seconds()
                / (
                    merged.loc[in_progress_mask, "end_datetime"]
                    - merged.loc[in_progress_mask, "start_datetime"]
                ).dt.total_seconds()
            ).clip(lower=0.0, upper=1.0)
            elapsed_minutes = (merged.loc[in_progress_mask, "duration"] * elapsed_frac).round().astype(float)
            new_total_minutes = (merged.loc[in_progress_mask, "processing_hours"] * 60.0).fillna(
                merged.loc[in_progress_mask, "duration"]
            )
            merged.loc[in_progress_mask, "processing_hours"] = (
                new_total_minutes.clip(lower=(elapsed_minutes + 1.0)) / 60.0
            )
            merged.loc[in_progress_mask, "fixed_start_time"] = merged.loc[in_progress_mask, "start_time"]

        # Уже завершенные операции тоже фиксируем по факту, чтобы не перепланировать прошлое.
        completed_mask = merged["end_datetime"] <= now_ts
        if completed_mask.any():
            merged.loc[completed_mask, "processing_hours"] = merged.loc[completed_mask, "duration"] / 60.0
            merged.loc[completed_mask, "fixed_start_time"] = merged.loc[completed_mask, "start_time"]

        merged["processing_hours"] = merged["processing_hours"].round(4)
        out_cols = source_df.columns.tolist()
        if "fixed_start_time" in merged.columns and "fixed_start_time" not in out_cols:
            out_cols.append("fixed_start_time")
        return merged[out_cols].copy()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Digital Twin MES - Планирование загрузки станков")
        self.resize(GUI.WINDOW_WIDTH, GUI.WINDOW_HEIGHT)

        self.input_df = pd.DataFrame()
        self.input_df_original = pd.DataFrame()
        self.schedule_df = pd.DataFrame()
        self.priority_df = pd.DataFrame(columns=["priority_rank", "product"])
        self.machine_name_map: dict[str, str] = {}
        self.solve_result: SolveResult | None = None
        self._opt_thread: QThread | None = None
        self._opt_worker: OptimizationWorker | None = None
        self._progress_dialog: QProgressDialog | None = None
        self._pending_changed_df = pd.DataFrame()
        self._pending_changed_keys: list[str] = []
        self._theme_timeline: QTimeLine | None = None

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
        self.csv_file_badge = toolbar_bundle.csv_file_badge
        self.theme_btn = toolbar_bundle.theme_btn
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
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.priority_widget.priority_changed.connect(self._on_priority_changed)
        self.dashboard_widget.operational_schedule_changed.connect(
            self._on_operational_schedule_changed
        )

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
            self.input_df = self._attach_op_key(self.input_df)
            self.input_df_original = self.input_df.copy()
            self.machine_name_map = self._build_machine_name_map(self.input_df)
            products = (
                self.input_df["product"].dropna().astype(str).drop_duplicates().tolist()
                if "product" in self.input_df.columns
                else []
            )
            self.priority_widget.update_products(products)
            self.dashboard_widget.update_changes_tables(pd.DataFrame(), pd.DataFrame())
            self.dashboard_widget.update_operational_schedule(pd.DataFrame())
            self._set_csv_file_badge(Path(path).name, "success")
        except Exception as exc:  # pragma: no cover
            self.dashboard_widget.update_changes_tables(pd.DataFrame(), pd.DataFrame())
            self.dashboard_widget.update_operational_schedule(pd.DataFrame())
            self._set_csv_file_badge("Ошибка загрузки CSV", "error")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить CSV:\n{exc}")

    def _run_optimization(self) -> None:
        if self.input_df.empty:
            QMessageBox.warning(self, "Нет данных", "Сначала загрузите CSV файл.")
            return
        if self._opt_thread is not None:
            return

        self._progress_dialog = QProgressDialog("Подготовка входных данных", "", 0, 100, self)
        self._progress_dialog.setWindowTitle("Выполняется оптимизация")
        self._progress_dialog.setWindowModality(Qt.WindowModal)
        self._progress_dialog.setCancelButton(None)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setValue(0)
        self._progress_dialog.show()

        self.load_btn.setEnabled(False)
        self.run_btn.setEnabled(False)

        self._opt_thread = QThread(self)
        pending_changed_df, pending_changed_keys = self._collect_processing_hours_changes()
        self._pending_changed_df = pending_changed_df
        self._pending_changed_keys = pending_changed_keys
        baseline_input_df = self.input_df_original if not self.input_df_original.empty else pd.DataFrame()
        self._opt_worker = OptimizationWorker(
            data=self.input_df,
            baseline_data=baseline_input_df,
            priority_df=self.priority_df,
            time_limit_seconds=int(self.time_limit.value()),
        )
        self._opt_worker.moveToThread(self._opt_thread)

        self._opt_thread.started.connect(self._opt_worker.run)
        self._opt_worker.progress_changed.connect(self._on_optimization_progress)
        self._opt_worker.finished.connect(self._on_optimization_finished)
        self._opt_worker.failed.connect(self._on_optimization_failed)
        self._opt_worker.finished.connect(self._opt_thread.quit)
        self._opt_worker.failed.connect(self._opt_thread.quit)
        self._opt_thread.finished.connect(self._cleanup_optimization_thread)

        self._opt_thread.start()

    @pyqtSlot(int, str)
    def _on_optimization_progress(self, value: int, status_message: str) -> None:
        if self._progress_dialog is None:
            return
        bounded = max(0, min(100, int(value)))
        self._progress_dialog.setLabelText(status_message)
        self._progress_dialog.setValue(bounded)

    @pyqtSlot(object, object, object)
    def _on_optimization_finished(
        self,
        schedule_df: pd.DataFrame,
        solve_result: SolveResult,
        baseline_schedule_df: pd.DataFrame,
    ) -> None:
        self.solve_result = solve_result
        self.schedule_df = self._localize_machine_names(schedule_df)
        self._close_progress_dialog()
        self.load_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        combined_changes_df = self._build_combined_changes_table(
            changed_df=self._pending_changed_df,
            changed_keys=self._pending_changed_keys,
            new_schedule_df=self.schedule_df,
            old_schedule_df=self._localize_machine_names(baseline_schedule_df),
        )
        overall_impact_df = self._build_overall_impact_table(
            new_schedule_df=self.schedule_df,
            old_schedule_df=self._localize_machine_names(baseline_schedule_df),
        )
        self.dashboard_widget.update_changes_tables(combined_changes_df, overall_impact_df)
        schedule_for_dashboard = self._attach_op_key(self.schedule_df.copy())
        completed_keys = self._extract_completed_op_keys(
            baseline_schedule_df=self._localize_machine_names(baseline_schedule_df),
            now_ts=datetime.now(),
        )
        self.dashboard_widget.update_operational_schedule(
            schedule_for_dashboard,
            locked_op_keys=completed_keys,
        )
        self._refresh_tabs()

    @pyqtSlot(str)
    def _on_optimization_failed(self, error_message: str) -> None:
        self._close_progress_dialog()
        self.load_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        QMessageBox.critical(self, "Ошибка оптимизации", error_message)

    @pyqtSlot()
    def _cleanup_optimization_thread(self) -> None:
        if self._opt_worker is not None:
            self._opt_worker.deleteLater()
            self._opt_worker = None
        if self._opt_thread is not None:
            self._opt_thread.deleteLater()
            self._opt_thread = None

    def _close_progress_dialog(self) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.setValue(100)
            self._progress_dialog.close()
            self._progress_dialog.deleteLater()
            self._progress_dialog = None

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
        metrics["solver_status_message"] = self._solver_status_message()
        metrics["solver_status_level"] = self._solver_status_level()

        self.dashboard_widget.update_metrics(metrics)
        self.gantt_machine_widget.update_chart(self.schedule_df)
        self.gantt_product_widget.update_chart(self.schedule_df)
        self.machine_load_widget.update_chart(util_series)
        self.machine_table_widget.update_table(self.schedule_df)
        self.table_widget.update_table(self.schedule_df)

    def _solver_status_message(self) -> str:
        if self.solve_result is None:
            return "-"
        status = str(self.solve_result.status).upper()
        if status == "OPTIMAL":
            return "Найдено оптимальное решение"
        if status == "FEASIBLE":
            return "Найдено наилучшее решение"
        if status == "INFEASIBLE":
            return "Решение не найдено (ограничения противоречивы)"
        if status == "UNKNOWN":
            return "Статус неизвестен (возможно, не хватило времени)"
        if status == "MODEL_INVALID":
            return "Ошибка модели (MODEL_INVALID)"
        return f"Статус решателя: {status}"

    def _solver_status_level(self) -> str:
        if self.solve_result is None:
            return "neutral"
        status = str(self.solve_result.status).upper()
        if status == "OPTIMAL":
            return "optimal"
        if status == "FEASIBLE":
            return "feasible"
        if status in {"INFEASIBLE", "UNKNOWN", "MODEL_INVALID"}:
            return "problem"
        return "neutral"

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

    def _set_csv_file_badge(self, text: str, state: str) -> None:
        badge: QLabel = self.csv_file_badge
        normalized_state = state if state in {"neutral", "success", "error"} else "neutral"
        badge.setText(text)
        badge.setProperty("loadState", normalized_state)
        style = badge.style()
        style.unpolish(badge)
        style.polish(badge)
        badge.update()

    def _toggle_theme(self) -> None:
        if self._theme_timeline is not None and self._theme_timeline.state() != QTimeLine.NotRunning:
            return

        from_colors = THEME.dark_colors if THEME.is_dark else THEME.light_colors
        THEME.toggle()
        to_colors = THEME.dark_colors if THEME.is_dark else THEME.light_colors
        self.theme_btn.setEnabled(False)
        if THEME.is_dark:
            self.theme_btn.setText("☀  Светлая")
        else:
            self.theme_btn.setText("☾  Тёмная")

        self._theme_timeline = QTimeLine(500, self)
        self._theme_timeline.setUpdateInterval(16)  # ~60 fps
        self._theme_timeline.valueChanged.connect(
            lambda t: self._apply_interpolated_theme(from_colors, to_colors, t)
        )
        self._theme_timeline.finished.connect(self._on_theme_transition_done)
        self._theme_timeline.start()

    def _apply_interpolated_theme(
        self,
        from_colors: dict,
        to_colors: dict,
        t: float,
    ) -> None:
        colors = interpolate_colors(from_colors, to_colors, t)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(THEME.stylesheet_for_colors(colors))

    def _on_theme_transition_done(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(THEME.current_stylesheet())
        self.theme_btn.setEnabled(True)
        if self._theme_timeline is not None:
            self._theme_timeline.deleteLater()
            self._theme_timeline = None

    def _on_operational_schedule_changed(self, schedule_df: pd.DataFrame) -> None:
        if schedule_df.empty:
            return
        if "op_key" not in schedule_df.columns or "duration" not in schedule_df.columns:
            return
        if self.input_df.empty or "op_key" not in self.input_df.columns:
            return
        durations = pd.to_numeric(schedule_df["duration"], errors="coerce")
        op_keys = schedule_df["op_key"].astype(str)
        updated_hours = (durations / 60.0).round(4)
        duration_map = {k: v for k, v in zip(op_keys, updated_hours) if pd.notna(v)}
        if not duration_map:
            return
        input_copy = self.input_df.copy()
        input_copy["op_key"] = input_copy["op_key"].astype(str)
        mask = input_copy["op_key"].isin(set(duration_map.keys()))
        if not mask.any():
            return
        input_copy.loc[mask, "processing_hours"] = (
            input_copy.loc[mask, "op_key"].map(duration_map).astype(str)
        )
        self.input_df = input_copy

    @staticmethod
    def _build_op_key(df: pd.DataFrame) -> pd.Series:
        return (
            df["product"].astype(str)
            + "|"
            + df["assembly"].astype(str)
            + "|"
            + df["part_number"].astype(str)
            + "|"
            + df["process_sequence"].astype(str)
            + "|"
            + df["process"].astype(str)
            + "|"
            + df["machine"].astype(str)
        )

    def _attach_op_key(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        required = ["product", "assembly", "part_number", "process_sequence", "process", "machine"]
        if all(c in out.columns for c in required):
            out["op_key"] = self._build_op_key(out)
        return out

    @staticmethod
    def _to_numeric_hours(series: pd.Series) -> pd.Series:
        return pd.to_numeric(
            series.astype(str).str.replace(",", ".", regex=False).str.strip(),
            errors="coerce",
        )

    def _collect_processing_hours_changes(self) -> tuple[pd.DataFrame, list[str]]:
        if self.input_df.empty or self.input_df_original.empty:
            return pd.DataFrame(), []
        if "op_key" not in self.input_df.columns or "op_key" not in self.input_df_original.columns:
            return pd.DataFrame(), []
        if "processing_hours" not in self.input_df.columns or "processing_hours" not in self.input_df_original.columns:
            return pd.DataFrame(), []

        original = self.input_df_original.copy().set_index("op_key")
        edited = self.input_df.copy().set_index("op_key")
        common_keys = original.index.intersection(edited.index)
        if common_keys.empty:
            return pd.DataFrame(), []

        old_hours = self._to_numeric_hours(original.loc[common_keys, "processing_hours"])
        new_hours = self._to_numeric_hours(edited.loc[common_keys, "processing_hours"])
        diff_mask = (new_hours - old_hours).abs() > 1e-9
        changed_keys = diff_mask[diff_mask].index.tolist()
        if not changed_keys:
            return pd.DataFrame(), []

        changed_rows = edited.loc[changed_keys].copy()
        changed_rows["old_processing_hours"] = old_hours.loc[changed_keys].values
        changed_rows["new_processing_hours"] = new_hours.loc[changed_keys].values
        cols = [
            "product",
            "part_number",
            "process_sequence",
            "process",
            "machine",
            "old_processing_hours",
            "new_processing_hours",
        ]
        available_cols = [c for c in cols if c in changed_rows.columns]
        out = changed_rows[available_cols].reset_index(drop=True)
        return out, changed_keys

    def _build_updated_schedule_for_changed_ops(
        self,
        schedule_df: pd.DataFrame,
        changed_keys: list[str],
    ) -> pd.DataFrame:
        if schedule_df.empty or not changed_keys:
            return pd.DataFrame()
        required = ["product", "assembly", "part_number", "process_sequence", "process", "machine"]
        if not all(c in schedule_df.columns for c in required):
            return pd.DataFrame()

        sched = schedule_df.copy()
        sched["op_key"] = self._build_op_key(sched)
        subset_cols = [
            "product",
            "part_number",
            "process_sequence",
            "process",
            "machine",
            "start_time",
            "end_time",
            "duration",
        ]
        if "start_datetime" in sched.columns and "end_datetime" in sched.columns:
            subset_cols.extend(["start_datetime", "end_datetime"])
        existing_cols = [c for c in subset_cols if c in sched.columns]
        return sched[sched["op_key"].isin(set(changed_keys))][existing_cols].reset_index(drop=True)

    @staticmethod
    def _format_difference_minutes(total_minutes: float) -> str:
        sign = "+" if total_minutes > 0 else "-" if total_minutes < 0 else "0"
        minutes_abs = int(abs(round(total_minutes)))
        days = minutes_abs // (24 * 60)
        rem = minutes_abs % (24 * 60)
        hours = rem // 60
        minutes = rem % 60
        if sign == "0":
            return "0 дней 0 часов 0 минут"
        return f"{sign}{days} дней {hours} часов {minutes} минут"

    def _build_combined_changes_table(
        self,
        changed_df: pd.DataFrame,
        changed_keys: list[str],
        new_schedule_df: pd.DataFrame,
        old_schedule_df: pd.DataFrame,
    ) -> pd.DataFrame:
        if changed_df.empty or not changed_keys:
            return pd.DataFrame()

        keys = ["product", "part_number", "process_sequence", "process", "machine"]
        old_subset = self._build_updated_schedule_for_changed_ops(old_schedule_df, changed_keys)
        new_subset = self._build_updated_schedule_for_changed_ops(new_schedule_df, changed_keys)
        if old_subset.empty and new_subset.empty:
            return changed_df.copy()

        old = old_subset.copy()
        new = new_subset.copy()
        rename_old = {}
        rename_new = {}
        if "start_datetime" in old.columns:
            rename_old["start_datetime"] = "old_start_datetime"
        if "end_datetime" in old.columns:
            rename_old["end_datetime"] = "old_end_datetime"
        if "start_datetime" in new.columns:
            rename_new["start_datetime"] = "new_start_datetime"
        if "end_datetime" in new.columns:
            rename_new["end_datetime"] = "new_end_datetime"
        old = old.rename(columns=rename_old)
        new = new.rename(columns=rename_new)
        old = old[[c for c in keys + ["old_start_datetime", "old_end_datetime"] if c in old.columns]]
        new = new[[c for c in keys + ["new_start_datetime", "new_end_datetime", "duration"] if c in new.columns]]
        for k in keys:
            if k in old.columns:
                old[k] = old[k].astype(str)
            if k in new.columns:
                new[k] = new[k].astype(str)

        combined = changed_df.copy()
        for k in keys:
            if k in combined.columns:
                combined[k] = combined[k].astype(str)
        combined = combined.merge(old, on=[k for k in keys if k in combined.columns and k in old.columns], how="left")
        combined = combined.merge(new, on=[k for k in keys if k in combined.columns and k in new.columns], how="left")

        if "old_start_datetime" in combined.columns and "new_start_datetime" in combined.columns:
            old_dt = pd.to_datetime(combined["old_start_datetime"], errors="coerce")
            new_dt = pd.to_datetime(combined["new_start_datetime"], errors="coerce")
            diff_minutes = (new_dt - old_dt).dt.total_seconds() / 60.0
            combined["difference_time"] = diff_minutes.apply(
                lambda v: self._format_difference_minutes(v) if pd.notna(v) else "-"
            )
        else:
            combined["difference_time"] = "-"

        preferred_order = [
            "product",
            "part_number",
            "process_sequence",
            "process",
            "machine",
            "old_processing_hours",
            "new_processing_hours",
            "old_start_datetime",
            "old_end_datetime",
            "new_start_datetime",
            "new_end_datetime",
            "difference_time",
        ]
        cols = [c for c in preferred_order if c in combined.columns]
        return combined[cols].reset_index(drop=True)

    def _build_overall_impact_table(
        self,
        new_schedule_df: pd.DataFrame,
        old_schedule_df: pd.DataFrame,
    ) -> pd.DataFrame:
        if new_schedule_df.empty or old_schedule_df.empty:
            return pd.DataFrame()
        required = ["product", "assembly", "part_number", "process_sequence", "process", "machine"]
        if not all(c in new_schedule_df.columns for c in required):
            return pd.DataFrame()
        if not all(c in old_schedule_df.columns for c in required):
            return pd.DataFrame()

        old = old_schedule_df.copy()
        new = new_schedule_df.copy()
        old["op_key"] = self._build_op_key(old)
        new["op_key"] = self._build_op_key(new)
        old_subset = old.rename(
            columns={
                "start_datetime": "old_start_datetime",
                "end_datetime": "old_end_datetime",
            }
        )
        new_subset = new.rename(
            columns={
                "start_datetime": "new_start_datetime",
                "end_datetime": "new_end_datetime",
            }
        )
        keys = ["op_key", "product", "part_number", "process_sequence", "process", "machine"]
        old_keep = [c for c in keys + ["old_start_datetime", "old_end_datetime"] if c in old_subset.columns]
        new_keep = [c for c in keys + ["new_start_datetime", "new_end_datetime"] if c in new_subset.columns]
        merged = new_subset[new_keep].merge(old_subset[old_keep], on=[c for c in keys if c in old_keep and c in new_keep], how="inner")
        if merged.empty:
            return pd.DataFrame()

        if "processing_hours" in self.input_df_original.columns and "op_key" in self.input_df_original.columns:
            old_hours_lookup = (
                self.input_df_original[["op_key", "processing_hours"]]
                .drop_duplicates(subset=["op_key"], keep="last")
                .set_index("op_key")["processing_hours"]
            )
            merged["old_processing_hours"] = self._to_numeric_hours(
                merged["op_key"].map(old_hours_lookup).fillna("")
            )
        else:
            merged["old_processing_hours"] = float("nan")

        if "processing_hours" in self.input_df.columns and "op_key" in self.input_df.columns:
            new_hours_lookup = (
                self.input_df[["op_key", "processing_hours"]]
                .drop_duplicates(subset=["op_key"], keep="last")
                .set_index("op_key")["processing_hours"]
            )
            merged["new_processing_hours"] = self._to_numeric_hours(
                merged["op_key"].map(new_hours_lookup).fillna("")
            )
        else:
            merged["new_processing_hours"] = float("nan")

        old_start = pd.to_datetime(merged["old_start_datetime"], errors="coerce")
        new_start = pd.to_datetime(merged["new_start_datetime"], errors="coerce")
        diff_minutes = (new_start - old_start).dt.total_seconds() / 60.0
        merged["difference_time"] = diff_minutes.apply(
            lambda v: self._format_difference_minutes(v) if pd.notna(v) else "-"
        )
        merged["abs_shift"] = diff_minutes.abs().fillna(0.0)
        merged = merged.sort_values("abs_shift", ascending=False).drop(columns=["abs_shift"])

        preferred_order = [
            "product",
            "part_number",
            "process_sequence",
            "process",
            "machine",
            "old_processing_hours",
            "new_processing_hours",
            "old_start_datetime",
            "old_end_datetime",
            "new_start_datetime",
            "new_end_datetime",
            "difference_time",
        ]
        cols = [c for c in preferred_order if c in merged.columns]
        return merged[cols].reset_index(drop=True)

    def _extract_completed_op_keys(
        self,
        baseline_schedule_df: pd.DataFrame,
        now_ts: datetime,
    ) -> list[str]:
        if baseline_schedule_df.empty:
            return []
        required = ["product", "assembly", "part_number", "process_sequence", "process", "machine"]
        if not all(c in baseline_schedule_df.columns for c in required):
            return []
        if "end_datetime" not in baseline_schedule_df.columns:
            return []
        work = baseline_schedule_df.copy()
        work["op_key"] = self._build_op_key(work)
        work["end_datetime"] = pd.to_datetime(work["end_datetime"], errors="coerce")
        done = work[work["end_datetime"] <= pd.Timestamp(now_ts)]
        if done.empty:
            return []
        return done["op_key"].dropna().astype(str).drop_duplicates().tolist()

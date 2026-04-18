from __future__ import annotations

from datetime import datetime, timedelta

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QScrollBar, QSizePolicy, QVBoxLayout, QWidget

class GanttWidget(QWidget):
    def __init__(self, mode: str = "machine") -> None:
        super().__init__()
        self.mode = mode
        self.figure = Figure(facecolor="#1e1e1e")
        self.canvas = FigureCanvas(self.figure)
        self.h_scroll = QScrollBar(Qt.Horizontal)
        self.h_scroll.setRange(0, 0)
        self.h_scroll.setVisible(True)
        self.h_scroll.setFixedHeight(14)
        self._bars = []
        self._annotation = None
        self._ax = None
        self._data_x_min = 0.0
        self._data_x_max = 1.0
        self._zoom_factor = 1.0
        self._zoom_step = 1.15
        self._min_zoom = 1.0
        self._max_zoom = 8.0
        self._scroll_resolution = 1000
        self._is_syncing_scroll = False
        self._apply_scrollbar_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.canvas)
        layout.addWidget(self.h_scroll)
        layout.addStretch(1)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        self.canvas.mpl_connect("scroll_event", self._on_scroll_zoom)
        self.h_scroll.valueChanged.connect(self._on_scrollbar_changed)

    def _apply_scrollbar_style(self) -> None:
        is_active = self._zoom_factor > 1.0
        handle_color = "#62b0ff" if is_active else "#1f1f1f"
        handle_hover_color = "#7bc0ff" if is_active else "#1f1f1f"
        self.h_scroll.setStyleSheet(
            f"""
            QScrollBar:horizontal {{
                background: #1f1f1f;
                border: none;
                border-radius: 7px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {handle_color};
                border: none;
                border-radius: 7px;
                min-width: 64px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {handle_hover_color};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
                border: none;
                width: 0px;
            }}
            """
        )

    @staticmethod
    def _build_segments(data: pd.DataFrame) -> pd.DataFrame:
        planning_base = data["planning_date"].iloc[0] if "planning_date" in data.columns and not data.empty else datetime(2026, 3, 25)
        default_work_minutes = 8 * 60
        default_shift_start = 8 * 60

        def to_datetime(processing_minutes: int, work_minutes_per_day: int, shift_start_minutes: int) -> datetime:
            day_idx = processing_minutes // work_minutes_per_day
            min_in_day = processing_minutes % work_minutes_per_day
            return planning_base + timedelta(days=day_idx, minutes=shift_start_minutes + min_in_day)

        rows = []
        for _, row in data.iterrows():
            work_minutes_per_day = int(
                row["working_minutes_per_day"]
            ) if "working_minutes_per_day" in data.columns and pd.notna(row["working_minutes_per_day"]) else default_work_minutes
            shift_start_minutes = int(
                row["shift_start_minutes"]
            ) if "shift_start_minutes" in data.columns and pd.notna(row["shift_start_minutes"]) else default_shift_start

            t0 = int(float(row["start_time"]))
            d_proc = int(float(row["duration"]))
            t_end = t0 + d_proc
            curr = t0

            while curr < t_end:
                min_in_day = curr % work_minutes_per_day
                available = work_minutes_per_day - min_in_day
                seg_len = min(available, t_end - curr)
                seg_start = curr
                seg_end = curr + seg_len

                rows.append(
                    {
                        **row.to_dict(),
                        "start_time": seg_start,
                        "end_time": seg_end,
                        "duration": seg_len,
                        "start_dt": to_datetime(seg_start, work_minutes_per_day, shift_start_minutes),
                        "end_dt": to_datetime(seg_end, work_minutes_per_day, shift_start_minutes),
                    }
                )
                curr = seg_end

        return pd.DataFrame(rows)

    def update_chart(self, schedule_df: pd.DataFrame) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._ax = ax
        ax.set_facecolor("#2b2b2b")
        self.figure.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.15)

        if schedule_df.empty:
            ax.text(0.5, 0.5, "Нет данных для визуализации", color="white", ha="center", va="center")
            ax.set_xticks([])
            ax.set_yticks([])
            self._zoom_factor = self._min_zoom
            self.h_scroll.setVisible(True)
            self.h_scroll.setRange(0, 0)
            self.canvas.draw_idle()
            return

        y_field = "machine" if self.mode == "machine" else "product"
        if y_field not in schedule_df.columns or "product" not in schedule_df.columns:
            ax.text(0.5, 0.5, "Недостаточно колонок для Gantt", color="white", ha="center", va="center")
            self._zoom_factor = self._min_zoom
            self.h_scroll.setVisible(True)
            self.h_scroll.setRange(0, 0)
            self.canvas.draw_idle()
            return

        data = schedule_df.copy()
        data["start_time"] = pd.to_numeric(data["start_time"], errors="coerce")
        data["duration"] = pd.to_numeric(data["duration"], errors="coerce")
        if "end_time" in data.columns:
            data["end_time"] = pd.to_numeric(data["end_time"], errors="coerce")
        data = data.dropna(subset=["start_time", "duration"]).sort_values(["start_time", y_field]).reset_index(
            drop=True
        )
        segments = self._build_segments(data)
        if segments.empty:
            ax.text(0.5, 0.5, "Нет данных для визуализации", color="white", ha="center", va="center")
            ax.set_xticks([])
            ax.set_yticks([])
            self._zoom_factor = self._min_zoom
            self.h_scroll.setVisible(True)
            self.h_scroll.setRange(0, 0)
            self.canvas.draw_idle()
            return
        categories = data[y_field].astype(str).drop_duplicates().tolist()
        category_to_y = {c: idx for idx, c in enumerate(categories)}
        products = data["product"].astype(str).drop_duplicates().tolist()
        color_palette = ["#4fc3f7", "#81c784", "#ffb74d", "#ba68c8", "#e57373", "#64b5f6", "#90a4ae"]
        product_colors = {p: color_palette[idx % len(color_palette)] for idx, p in enumerate(products)}

        bars = []
        for _, row in segments.iterrows():
            y_name = str(row[y_field])
            y_pos = category_to_y[y_name]
            start = mdates.date2num(pd.to_datetime(row["start_dt"]).to_pydatetime())
            end = mdates.date2num(pd.to_datetime(row["end_dt"]).to_pydatetime())
            duration = max(1e-9, end - start)
            color = product_colors[str(row["product"])]
            bar = ax.barh(y=y_pos, width=duration, left=start, height=0.78, color=color, alpha=0.95)[0]
            bars.append((bar, row))

        ax.set_yticks(list(category_to_y.values()))
        ax.set_yticklabels(list(category_to_y.keys()), color="white")
        ax.tick_params(axis="x", colors="#e8e8e8")
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set_xlabel("Дата/время", color="#e8e8e8")
        ax.set_ylabel("Станки" if self.mode == "machine" else "Изделия", color="#e8e8e8")
        ax.set_title(
            "Gantt chart (станки)" if self.mode == "machine" else "Gantt chart (изделия)",
            color="#e8e8e8",
            pad=12,
        )
        ax.grid(axis="x", color="#3a3a3a", linewidth=0.8, alpha=0.5)
        for spine in ax.spines.values():
            spine.set_visible(False)
        min_start = mdates.date2num(pd.to_datetime(segments["start_dt"]).min().to_pydatetime())
        max_end = mdates.date2num(pd.to_datetime(segments["end_dt"]).max().to_pydatetime())
        x_padding = max((10.0 / 1440.0), (max_end - min_start) * 0.02)
        self._data_x_min = min_start - x_padding
        self._data_x_max = max_end + x_padding
        self._zoom_factor = self._min_zoom
        ax.set_xlim(self._data_x_min, self._data_x_max)
        self._sync_scrollbar()
        self._bars = bars
        self._annotation = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox={"boxstyle": "round,pad=0.4", "fc": "#2b2b2b", "ec": "#4aa3df"},
            color="#e8e8e8",
        )
        self._annotation.set_visible(False)
        self.canvas.draw_idle()

    def _on_hover(self, event) -> None:
        if not hasattr(self, "_bars") or self._annotation is None:
            return
        visible = False
        for bar, row in self._bars:
            contains, _ = bar.contains(event)
            if not contains:
                continue
            part_number = str(row.get("part_number", "-"))
            process = str(row.get("process", "-"))
            machine = str(row.get("machine", "-"))
            start_time = int(float(row.get("start_time", 0)))
            end_time = int(float(row.get("end_time", start_time)))
            duration = int(float(row.get("duration", max(0, end_time - start_time))))
            start_dt = pd.to_datetime(row.get("start_dt")).strftime("%Y-%m-%d %H:%M")
            end_dt = pd.to_datetime(row.get("end_dt")).strftime("%Y-%m-%d %H:%M")
            text = (
                f"part_number: {part_number}\n"
                f"process: {process}\n"
                f"machine: {machine}\n"
                f"start_dt: {start_dt}\n"
                f"end_dt: {end_dt}\n"
                f"start_time: {start_time}\n"
                f"end_time: {end_time}\n"
                f"duration: {duration}"
            )
            self._annotation.xy = (event.xdata, event.ydata)
            self._annotation.set_text(text)
            self._annotation.set_visible(True)
            visible = True
            break
        if not visible and self._annotation.get_visible():
            self._annotation.set_visible(False)
        self.canvas.draw_idle()

    def _on_scroll_zoom(self, event) -> None:
        if self._ax is None:
            return
        old_xlim = self._ax.get_xlim()
        old_span = max(1e-6, old_xlim[1] - old_xlim[0])
        if event.xdata is None:
            anchor_x = old_xlim[0] + old_span / 2.0
        else:
            anchor_x = float(event.xdata)
        if event.button == "up":
            self._zoom_factor = min(self._zoom_factor * self._zoom_step, self._max_zoom)
        elif event.button == "down":
            self._zoom_factor = max(self._zoom_factor / self._zoom_step, self._min_zoom)
        else:
            return
        full_span = max(1e-6, self._data_x_max - self._data_x_min)
        new_span = full_span / self._zoom_factor
        left = anchor_x - new_span / 2.0
        left = max(self._data_x_min, min(left, self._data_x_max - new_span))
        right = left + new_span
        self._ax.set_xlim(left, right)
        self._sync_scrollbar()
        self.canvas.draw_idle()

    def _on_scrollbar_changed(self, value: int) -> None:
        if self._ax is None or self._is_syncing_scroll:
            return
        full_span = max(1e-6, self._data_x_max - self._data_x_min)
        view_span = full_span / self._zoom_factor
        max_start = max(0.0, full_span - view_span)
        start_offset = max_start * (value / self._scroll_resolution)
        left = self._data_x_min + start_offset
        right = left + view_span
        self._ax.set_xlim(left, right)
        self.canvas.draw_idle()

    def _sync_scrollbar(self) -> None:
        if self._ax is None:
            return
        self._apply_scrollbar_style()
        full_span = max(1e-6, self._data_x_max - self._data_x_min)
        view_span = full_span / self._zoom_factor
        if view_span >= full_span - 1e-6:
            self._is_syncing_scroll = True
            self.h_scroll.setVisible(True)
            self.h_scroll.setRange(0, 0)
            self.h_scroll.setValue(0)
            self._is_syncing_scroll = False
            return

        x_left, _ = self._ax.get_xlim()
        max_start = max(1e-6, full_span - view_span)
        start_offset = max(0.0, min(x_left - self._data_x_min, max_start))
        value = int((start_offset / max_start) * self._scroll_resolution)
        self._is_syncing_scroll = True
        self.h_scroll.setVisible(True)
        self.h_scroll.setRange(0, self._scroll_resolution)
        self.h_scroll.setPageStep(max(1, int((view_span / full_span) * self._scroll_resolution)))
        self.h_scroll.setValue(value)
        self._is_syncing_scroll = False

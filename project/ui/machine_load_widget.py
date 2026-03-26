from __future__ import annotations

import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QVBoxLayout, QWidget


class MachineLoadWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.figure = Figure(facecolor="#1e1e1e")
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.canvas)

    def update_chart(self, utilization_series: pd.Series) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#2b2b2b")
        self.figure.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.2)
        ax.tick_params(axis="x", colors="#e8e8e8", rotation=28)
        ax.tick_params(axis="y", colors="#e8e8e8")
        ax.set_xlabel("Станок", color="#e8e8e8")
        ax.set_ylabel("Загрузка, %", color="#e8e8e8")
        ax.set_title("Загрузка станков", color="#e8e8e8", pad=12)
        ax.grid(axis="y", color="#3a3a3a", linewidth=0.8, alpha=0.5)
        for spine in ax.spines.values():
            spine.set_visible(False)

        if utilization_series.empty:
            ax.text(0.5, 0.5, "Нет данных", color="#a0a0a0", ha="center", va="center")
            self.canvas.draw_idle()
            return

        util_df = utilization_series.reset_index()
        util_df.columns = ["machine", "utilization_pct"]
        util_df = util_df.sort_values("utilization_pct", ascending=False)
        ax.bar(util_df["machine"], util_df["utilization_pct"], color="#4aa3df", width=0.65)
        self.canvas.draw_idle()

from __future__ import annotations

import tempfile
from typing import Callable, Optional

import pandas as pd
import plotly.graph_objects as go

from .data_loader import load_operations
from .scheduler import SolveResult, solve_schedule
from .ui_utils import calculate_metrics, create_gantt_chart, create_product_gantt_chart


def run_scheduler(
    data: pd.DataFrame,
    priority_df: Optional[pd.DataFrame] = None,
    time_limit_seconds: int = 30,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> tuple[pd.DataFrame, SolveResult]:
    """
    Тонкая обертка над CP-SAT без изменения бизнес-логики.
    """
    if progress_callback:
        progress_callback(10, "Подготовка входных данных")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
        data.to_csv(tmp_path, sep=";", index=False)

    operations_df, machine_params, horizon_minutes = load_operations(tmp_path)
    if progress_callback:
        progress_callback(35, "Проверка и применение приоритетов")
    product_priorities: dict[str, int] = {}
    if priority_df is not None and not priority_df.empty:
        if "product" in priority_df.columns and "priority_rank" in priority_df.columns:
            pr = priority_df[["product", "priority_rank"]].copy()
            pr["product"] = pr["product"].astype(str)
            pr["priority_rank"] = pd.to_numeric(pr["priority_rank"], errors="coerce")
            pr = pr.dropna(subset=["priority_rank"]).drop_duplicates(subset=["product"])
            if not pr.empty:
                product_priorities = pr.set_index("product")["priority_rank"].astype(int).to_dict()

    if progress_callback:
        progress_callback(60, "Запуск оптимизации CP-SAT")
    schedule_df, solve_result = solve_schedule(
        operations_df=operations_df,
        machine_params=machine_params,
        horizon_minutes=horizon_minutes,
        max_time_seconds=time_limit_seconds,
        product_priorities=product_priorities if product_priorities else None,
    )
    if progress_callback:
        progress_callback(85, "Формирование результата")
        progress_callback(100, "Оптимизация завершена")
    return schedule_df, solve_result


def create_gantt_chart_figure(schedule_df: pd.DataFrame, by: str = "machine") -> go.Figure:
    if by == "product":
        return create_product_gantt_chart(schedule_df)
    return create_gantt_chart(schedule_df)

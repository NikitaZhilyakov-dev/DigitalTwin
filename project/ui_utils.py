from __future__ import annotations

from typing import Dict, Iterable, Optional, Sequence, Tuple

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px


def filter_schedule(
    schedule_df: pd.DataFrame,
    machines: Optional[Sequence[str]] = None,
    products: Optional[Sequence[str]] = None,
    processes: Optional[Sequence[str]] = None,
    time_range: Optional[Tuple[float, float]] = None,
    bottlenecks_only: bool = False,
) -> pd.DataFrame:
    """
    Фильтрует расписание по критериям, не меняя бизнес-логику оптимизации.
    """
    df = schedule_df.copy()

    if machines:
        df = df[df["machine"].isin(list(machines))]
    if products and "product" in df.columns:
        df = df[df["product"].isin(list(products))]
    if processes:
        df = df[df["process"].isin(list(processes))]

    if time_range is not None and len(time_range) == 2:
        t0, t1 = time_range
        # Оставляем операции, пересекающиеся с диапазоном по времени старта.
        df = df[(df["start_time"] >= t0) & (df["start_time"] <= t1)]

    if bottlenecks_only and not df.empty:
        metrics = calculate_metrics(schedule_df)
        bottleneck_machines = set(metrics["bottlenecks"])
        if bottleneck_machines:
            df = df[df["machine"].isin(bottleneck_machines)]

    return df


def calculate_metrics(schedule_df: pd.DataFrame) -> Dict[str, object]:
    """
    KPI для Dashboard и для определения узких мест.

    utilization(machine) = sum(duration_on_machine) / makespan
    """
    if schedule_df.empty:
        return {
            "makespan": 0,
            "avg_utilization_pct": 0,
            "most_utilized_machine": None,
            "least_utilized_machine": None,
            "operations_count": 0,
            "avg_operation_duration": 0,
            "utilization_by_machine": pd.Series(dtype=float),
            "bottlenecks": [],
        }

    required = ["machine", "duration", "end_time"]
    for c in required:
        if c not in schedule_df.columns:
            raise ValueError(f"schedule_df должен содержать колонку {c}")

    # Считаем makespan "по календарю", если есть start/end_datetime.
    # Это лучше отражает реальную картину с перерывами/ночью.
    if "end_datetime" in schedule_df.columns and "start_datetime" in schedule_df.columns:
        if schedule_df["end_datetime"].notna().any():
            planning_base = schedule_df["planning_date"].iloc[0] if "planning_date" in schedule_df.columns else datetime(2026, 3, 25)
            if "shift_start_minutes" in schedule_df.columns:
                shift_start = int(schedule_df["shift_start_minutes"].dropna().iloc[0])
            else:
                shift_start = 8 * 60
            wall_start = planning_base + timedelta(minutes=shift_start)
            makespan = float(
                (pd.to_datetime(schedule_df["end_datetime"]).max() - wall_start).total_seconds()
                / 60.0
            )
        else:
            makespan = 0.0
    else:
        makespan = float(schedule_df["end_time"].max())

    if makespan <= 0:
        makespan = 1.0

    utilization_by_machine = (
        schedule_df.groupby("machine", sort=False)["duration"].sum() / makespan * 100.0
    )

    avg_utilization_pct = float(utilization_by_machine.mean())
    most_utilized_machine = utilization_by_machine.idxmax()
    least_utilized_machine = utilization_by_machine.idxmin()

    operations_count = int(len(schedule_df))
    avg_operation_duration = float(schedule_df["duration"].mean())

    # Узкие места: машины с utilization >= 0.8 от максимальной (если max > 0).
    max_util = float(utilization_by_machine.max())
    if max_util > 0:
        bottlenecks = utilization_by_machine[utilization_by_machine >= 0.8 * max_util].index.tolist()
    else:
        bottlenecks = []

    return {
        "makespan": makespan,
        "avg_utilization_pct": avg_utilization_pct,
        "most_utilized_machine": most_utilized_machine,
        "least_utilized_machine": least_utilized_machine,
        "operations_count": operations_count,
        "avg_operation_duration": avg_operation_duration,
        "utilization_by_machine": utilization_by_machine,
        "bottlenecks": bottlenecks,
    }


def _build_segments(df: pd.DataFrame, planning_date: datetime | None = None) -> pd.DataFrame:
    planning_base = planning_date if planning_date is not None else (
        df["planning_date"].iloc[0] if "planning_date" in df.columns else datetime(2026, 3, 25)
    )
    # Время в schedule_df считается в "рабочих минутах" (ночью не течет).
    # Поэтому на Ганте разрезаем операцию на сегменты по рабочим окнам.
    default_work_minutes = 8 * 60
    default_shift_start = 8 * 60

    def to_datetime(processing_minutes: int, work_minutes_per_day: int, shift_start_minutes: int) -> datetime:
        day_idx = processing_minutes // work_minutes_per_day
        min_in_day = processing_minutes % work_minutes_per_day
        return planning_base + timedelta(days=day_idx, minutes=shift_start_minutes + min_in_day)

    # Сегментируем операции по рабочим окнам, чтобы увидеть "прерывание ночью".
    rows = []
    if not df.empty:
        for _, r in df.iterrows():
            work_minutes_per_day = int(
                r["working_minutes_per_day"]
            ) if "working_minutes_per_day" in df.columns and pd.notna(r["working_minutes_per_day"]) else default_work_minutes
            shift_start_minutes = int(
                r["shift_start_minutes"]
            ) if "shift_start_minutes" in df.columns and pd.notna(r["shift_start_minutes"]) else default_shift_start

            t0 = int(r["start_time"])
            d_proc = int(r["duration"])
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
                        **{k: r[k] for k in ["product", "assembly", "part_number", "process", "machine"] if k in df.columns},
                        "start_time": seg_start,
                        "end_time": seg_end,
                        "duration": seg_len,
                        "start_dt": to_datetime(seg_start, work_minutes_per_day, shift_start_minutes),
                        "end_dt": to_datetime(seg_end, work_minutes_per_day, shift_start_minutes),
                    }
                )
                curr = seg_end

    return pd.DataFrame(rows)


def _create_gantt_figure(
    segments_df: pd.DataFrame,
    y_field: str,
    color_field: str,
    title: str,
    y_title: str,
    legend_title: str,
):
    if segments_df.empty:
        return px.timeline(title=f"{title}: нет данных")

    hover_data: Dict[str, object] = {
        "part_number": True,
        "process": True,
        "duration": True,
        "start_time": True,
        "end_time": True,
        "machine": True,
    }
    if "product" in segments_df.columns:
        hover_data["product"] = True
    if "assembly" in segments_df.columns:
        hover_data["assembly"] = True

    fig = px.timeline(
        segments_df,
        x_start="start_dt",
        x_end="end_dt",
        y=y_field,
        color=color_field,
        hover_name="part_number",
        hover_data=hover_data,
        title=title,
    )

    fig.update_yaxes(title_text=y_title)
    fig.update_xaxes(title_text="Время")
    fig.update_layout(
        dragmode="pan",
        height=650,
        hovermode="closest",
        legend_title_text=legend_title,
    )
    # Ползунок/скроллинг для удобного зума.
    fig.update_xaxes(rangeslider=dict(visible=True), fixedrange=False)
    return fig


def create_gantt_chart(schedule_df: pd.DataFrame, machines: Optional[Sequence[str]] = None):
    """
    Устойчивая к расширениям визуализация Ганта на plotly.

    Требуемые колонки:
    part_number, process, machine, start_time, end_time, duration, product
    """
    df = schedule_df.copy()
    if machines:
        df = df[df["machine"].isin(list(machines))]

    segments_df = _build_segments(df)
    color_field = "product" if "product" in segments_df.columns else "part_number"
    return _create_gantt_figure(
        segments_df=segments_df,
        y_field="machine",
        color_field=color_field,
        title="Ghant Chart machine",
        y_title="Станок",
        legend_title="Изделие",
    )


def create_product_gantt_chart(schedule_df: pd.DataFrame, machines: Optional[Sequence[str]] = None):
    """Диаграмма жизненного цикла продукта для Streamlit."""
    df = schedule_df.copy()
    if machines:
        df = df[df["machine"].isin(list(machines))]

    segments_df = _build_segments(df)
    return _create_gantt_figure(
        segments_df=segments_df,
        y_field="product",
        color_field="machine",
        title="Ghant Chart product",
        y_title="Изделие",
        legend_title="Станок",
    )


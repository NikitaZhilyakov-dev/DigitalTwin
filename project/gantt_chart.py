from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px  # type: ignore[reportMissingImports]


def _build_segments(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """Разрезает операции на рабочие дневные сегменты для корректной визуализации пауз."""
    df = schedule_df.copy()

    planning_base = datetime(2026, 3, 25)
    default_work_minutes = 8 * 60
    default_shift_start = 8 * 60

    def to_datetime(processing_minutes: int, work_minutes_per_day: int, shift_start_minutes: int) -> datetime:
        day_idx = processing_minutes // work_minutes_per_day
        min_in_day = processing_minutes % work_minutes_per_day
        return planning_base + timedelta(days=day_idx, minutes=shift_start_minutes + min_in_day)

    # Разрезаем операции на сегменты по рабочим окнам, чтобы визуально отразить паузы ночью.
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

                row = {
                    "machine": r["machine"],
                    "part_number": r["part_number"] if "part_number" in df.columns else None,
                    "process": r["process"] if "process" in df.columns else None,
                    "duration": seg_len,
                    "start_time": seg_start,
                    "end_time": seg_end,
                    "start_dt": to_datetime(seg_start, work_minutes_per_day, shift_start_minutes),
                    "end_dt": to_datetime(seg_end, work_minutes_per_day, shift_start_minutes),
                }
                if "product" in df.columns:
                    row["product"] = r["product"]
                if "assembly" in df.columns:
                    row["assembly"] = r["assembly"]
                rows.append(row)
                curr = seg_end

    return pd.DataFrame(rows)


def _build_timeline_chart(
    segments_df: pd.DataFrame,
    output_html_path: str,
    title: str,
    y_field: str,
    color_field: str,
    legend_title: str,
) -> None:
    if segments_df.empty:
        raise ValueError("Невозможно построить диаграмму: пустое расписание.")

    has_assembly = "assembly" in segments_df.columns

    hover_name = "process"

    hover_data = {
        "process": True,
        "duration": True,
        "part_number": True,
        "start_time": True,
        "end_time": True,
        "machine": True,
    }
    if "product" in segments_df.columns:
        hover_data["product"] = True
    if has_assembly:
        hover_data["assembly"] = True

    fig = px.timeline(
        segments_df,
        x_start="start_dt",
        x_end="end_dt",
        y=y_field,
        color=color_field,
        hover_name=hover_name,
        hover_data=hover_data,
        title=title,
    )
    fig.update_yaxes(title_text=y_field.capitalize())
    fig.update_xaxes(title_text="Время", rangeslider=dict(visible=True), fixedrange=False)
    fig.update_layout(
        dragmode="pan",
        height=650,
        hovermode="closest",
        legend_title_text=legend_title,
    )
    fig.write_html(output_html_path)


def build_machine_gantt_chart(schedule_df: pd.DataFrame, output_html_path: str) -> None:
    """Текущая диаграмма загрузки станков."""
    segments_df = _build_segments(schedule_df)
    color_field = "product" if "product" in segments_df.columns else "part_number"
    _build_timeline_chart(
        segments_df=segments_df,
        output_html_path=output_html_path,
        title="Ghant Chart machine",
        y_field="machine",
        color_field=color_field,
        legend_title="Изделие",
    )


def build_product_gantt_chart(schedule_df: pd.DataFrame, output_html_path: str) -> None:
    """Диаграмма жизненного цикла продуктов по времени."""
    segments_df = _build_segments(schedule_df)
    _build_timeline_chart(
        segments_df=segments_df,
        output_html_path=output_html_path,
        title="Ghant Chart product",
        y_field="product",
        color_field="machine",
        legend_title="Станок",
    )


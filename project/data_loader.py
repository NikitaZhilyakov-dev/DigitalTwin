from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd


def _to_float_series(s: pd.Series) -> pd.Series:
    """
    Преобразует строковые числа с десятичной запятой в float.
    Пустые значения -> NaN.
    """
    s = s.astype(str).str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})
    s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _to_int_series(s: pd.Series) -> pd.Series:
    """Преобразует числовые строки в int (NaN -> NaN)."""
    return _to_float_series(s).round().astype("Int64")


@dataclass(frozen=True)
class MachineParams:
    working_minutes_per_day: int
    maintenance_required: bool
    maintenance_minutes: int  # зазор МЕЖДУ операциями на этом станке


def load_operations(csv_path: str) -> tuple[pd.DataFrame, dict[str, MachineParams], int]:
    """
    Загружает CSV и приводит данные к типам, пригодным для CP-SAT.

    Принято допущение для обслуживания:
    - если на строках конкретного `machine` указано `maintenance_between_operations=yes`,
      то на этом станке требуется фиксированный зазор `maintenance_time_hours` между любыми
      двумя последовательными операциями.
    """
    df = pd.read_csv(csv_path, sep=";")

    required_cols = [
        "product",
        "assembly",
        "part_number",
        "process_sequence",
        "process",
        "machine",
        "processing_hours",
        "working_hours_per_day",
        "assigned_staff",
        "maintenance_between_operations",
        "maintenance_time_hours",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"В CSV не найдены колонки: {missing}")

    df = df.copy()

    df["process_sequence"] = _to_int_series(df["process_sequence"])
    df["processing_hours"] = _to_float_series(df["processing_hours"])
    df["processing_minutes"] = (df["processing_hours"] * 60).round().astype("Int64")

    df["working_hours_per_day"] = _to_float_series(df["working_hours_per_day"])
    df["assigned_staff"] = _to_float_series(df["assigned_staff"])

    df["maintenance_time_hours"] = _to_float_series(df["maintenance_time_hours"])
    df["maintenance_time_minutes"] = (df["maintenance_time_hours"] * 60).round().astype("Int64")
    if "fixed_start_time" in df.columns:
        df["fixed_start_time"] = _to_int_series(df["fixed_start_time"])

    df["maintenance_between_operations"] = (
        df["maintenance_between_operations"].astype(str).str.strip().str.lower()
    )
    # `read_csv` нередко превращает пустоты в строку 'nan', поэтому нормализуем все невалидные значения.
    df.loc[
        df["maintenance_between_operations"].isin(["", "nan", "none", "null", "na"]),
        "maintenance_between_operations",
    ] = "no"

    # Базовые проверки качества входа.
    if df["processing_minutes"].isna().any():
        bad = df[df["processing_minutes"].isna()].head(5)
        raise ValueError(
            "В данных есть строки с пропущенным `processing_hours`/`processing_minutes` (пример):\n"
            f"{bad[['part_number','process_sequence','process','machine','processing_hours']]}"
        )
    if df["process_sequence"].isna().any():
        raise ValueError("В данных есть строки с пропущенным `process_sequence`.")

    # Уберем строки с пустым machine/part_number/process_sequence.
    df = df.dropna(subset=["machine", "part_number", "process_sequence", "process"])

    # Параметры станков: working_hours_per_day и обслуживание.
    global_working_hours = float(df["working_hours_per_day"].dropna().median()) if df["working_hours_per_day"].notna().any() else 8.0
    if math.isnan(global_working_hours) or global_working_hours <= 0:
        global_working_hours = 8.0

    machine_params: dict[str, MachineParams] = {}
    for machine, mdf in df.groupby("machine", sort=False):
        working_hours = float(mdf["working_hours_per_day"].dropna().median()) if mdf["working_hours_per_day"].notna().any() else global_working_hours
        if working_hours <= 0:
            working_hours = global_working_hours

        maintenance_required = (mdf["maintenance_between_operations"] == "yes").any()
        maint_minutes = 0
        if maintenance_required:
            maint_minutes = int(mdf.loc[mdf["maintenance_between_operations"] == "yes", "maintenance_time_minutes"].dropna().max() or 0)

        machine_params[str(machine)] = MachineParams(
            working_minutes_per_day=int(round(working_hours * 60)),
            maintenance_required=bool(maintenance_required),
            maintenance_minutes=int(maint_minutes),
        )

    # Переводим в int минут и гарантируем тип.
    df["processing_minutes"] = df["processing_minutes"].astype(int)
    df["process_sequence"] = df["process_sequence"].astype(int)

    # Горизонт планирования (в минутах).
    # Считаем минимальный span на каждом станке: сумма обработок + обслуживание между операциями.
    horizon_minutes = 0
    for machine, mdf in df.groupby("machine", sort=False):
        params = machine_params[str(machine)]
        n_ops = len(mdf)
        proc_sum = int(mdf["processing_minutes"].sum())
        gap_sum = params.maintenance_minutes * max(0, n_ops - 1) if params.maintenance_required else 0
        min_span = proc_sum + gap_sum

        working_day = max(1, params.working_minutes_per_day)
        days_needed = int(math.ceil(min_span / working_day)) + 1
        horizon_machine = days_needed * working_day
        horizon_minutes = max(horizon_minutes, horizon_machine)

    # Дополнительная безопасная верхняя оценка:
    # если все операции условно "вынудить" идти последовательно,
    # то makespan не должен превысить сумму длительностей обработок
    # и обслуживания (в приближении occupancy-отрезков).
    total_processing = int(df["processing_minutes"].sum())
    total_maintenance_occ = 0
    for machine, mdf in df.groupby("machine", sort=False):
        params = machine_params[str(machine)]
        if params.maintenance_required and params.maintenance_minutes > 0:
            total_maintenance_occ += params.maintenance_minutes * len(mdf)

    horizon_upper = total_processing + total_maintenance_occ
    horizon_minutes = max(horizon_minutes, horizon_upper, 60)  # хотя бы 1 час

    # Удобная нумерация операций.
    df = df.reset_index(drop=True)
    df["op_id"] = df.index

    return df, machine_params, horizon_minutes


def df_to_schedule_schema(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводит выходные колонки к требуемому формату.
    Ожидаются столбцы: part_number, process, machine, start_time, end_time, duration.
    """
    cols = ["part_number", "process", "machine", "start_time", "end_time", "duration"]
    missing = [c for c in cols if c not in schedule_df.columns]
    if missing:
        raise ValueError(f"В schedule_df отсутствуют колонки: {missing}")
    return schedule_df[cols].copy()


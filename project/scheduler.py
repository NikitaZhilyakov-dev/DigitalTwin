from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd
from ortools.sat.python import cp_model  # type: ignore[reportMissingImports]

from .constraints import add_machine_no_overlap, add_part_precedence, build_total_idle
from .data_loader import MachineParams


@dataclass(frozen=True)
class SolveResult:
    status: str
    objective_value: float | None
    makespan_minutes: int | None


def solve_schedule(
    operations_df: pd.DataFrame,
    machine_params: Dict[str, MachineParams],
    horizon_minutes: int,
    max_time_seconds: int = 30,
    log_search_progress: bool = False,
    product_priorities: Dict[str, int] | None = None,
) -> Tuple[pd.DataFrame, SolveResult]:
    """
    Строит и решает CP-SAT модель.

    Стратегия обслуживания (в терминах интервалов на станке):
    - создается interval "occupancy" для каждой операции, длительность которого =
      processing_minutes + maintenance_gap_minutes (если для станка обслуживание требуется).
    - это автоматически добавляет зазор между операциями на одном и том же станке за счет `AddNoOverlap`.
    - переменные end/start в выводе соответствуют фактическому завершению обработки (без обслуживания после последней операции).
    """
    model = cp_model.CpModel()
    # Дата начала планирования (нулевая точка времени в минутах).
    # Визуализация/календарные расчеты от этой даты.
    planning_date = datetime(2026, 3, 25)

    # Рабочий график (визуальная интерпретация):
    # - рабочий день начинается с 08:00
    # - "start_time/end_time" рассматриваются как рабочие минуты (ночью время не течет)
    shift_start_minutes = 8 * 60
    day_length_minutes = 24 * 60

    # ---- Переменные времени и интервалов ----
    start_proc: Dict[int, cp_model.IntVar] = {}
    end_proc: Dict[int, cp_model.IntVar] = {}
    occupancy_intervals: Dict[int, cp_model.IntervalVar] = {}

    proc_duration: Dict[int, int] = {}

    # Делаем op_id ключом для надежного доступа к строке.
    ops = operations_df.set_index("op_id", drop=False)
    all_ops = ops["op_id"].tolist()
    for i in all_ops:
        row = ops.loc[i]
        machine = str(row["machine"])
        mparams = machine_params[machine]

        d_proc = int(row["processing_minutes"])
        d_gap = int(mparams.maintenance_minutes) if mparams.maintenance_required else 0
        d_occ = d_proc + d_gap

        s = model.NewIntVar(0, horizon_minutes, f"start_proc_{i}")
        e = model.NewIntVar(0, horizon_minutes, f"end_proc_{i}")
        model.Add(e == s + d_proc)

        e_occ = model.NewIntVar(0, horizon_minutes + d_gap + 1, f"end_occ_{i}")
        model.Add(e_occ == s + d_occ)

        interval = model.NewIntervalVar(s, d_occ, e_occ, f"occ_interval_{i}")

        start_proc[i] = s
        end_proc[i] = e
        occupancy_intervals[i] = interval
        proc_duration[i] = d_proc

    # ---- Ограничения ----
    # 1) Порядок операций внутри каждой детали
    add_part_precedence(model, operations_df, start_vars=start_proc, end_vars=end_proc)

    # 2) Непересечение по станкам (с учетом обслуживания через occupancy)
    add_machine_no_overlap(model, operations_df, occupancy_intervals=occupancy_intervals)

    # ---- Целевая функция ----
    # Makespan: завершение всех операций (по фактическому окончанию обработки).
    makespan = model.NewIntVar(0, horizon_minutes, "makespan")
    model.AddMaxEquality(makespan, [end_proc[i] for i in all_ops])

    total_idle = build_total_idle(
        model=model,
        operations_df=operations_df,
        start_vars=start_proc,
        end_vars=end_proc,
        machine_params=machine_params,
        horizon_minutes=horizon_minutes,
    )

    # Лексикографическая приоритизация: сначала makespan, затем idle.
    # CP-SAT поддерживает только одну цель, поэтому используем "большой коэффициент".
    max_machines = max(1, len(machine_params))
    # total_idle <= horizon_minutes * max_machines (оценка по верхним границам idle_m).
    big = horizon_minutes * max_machines + 1
    objective = big * makespan + total_idle

    # Мягкий приоритет продуктов: чем выше продукт в пользовательском ранге, тем сильнее
    # модель стремится уменьшить его время завершения. При этом makespan остается главным.
    if product_priorities:
        products = [str(p) for p in ops["product"].dropna().unique().tolist()]
        if products:
            max_rank = max(int(r) for r in product_priorities.values()) if product_priorities else len(products)
            max_rank = max(1, max_rank)
            total_weight = 0
            weighted_completion_terms = []

            for idx, product in enumerate(products):
                product_op_ids = ops.loc[ops["product"] == product, "op_id"].tolist()
                if not product_op_ids:
                    continue
                product_end = model.NewIntVar(0, horizon_minutes, f"product_end_{idx}")
                model.AddMaxEquality(product_end, [end_proc[i] for i in product_op_ids])

                rank = int(product_priorities.get(product, max_rank + 1))
                weight = max(1, max_rank - rank + 2)
                total_weight += weight
                weighted_completion_terms.append(weight * product_end)

            if weighted_completion_terms and total_weight > 0:
                weighted_completion = model.NewIntVar(
                    0, horizon_minutes * total_weight, "weighted_completion"
                )
                model.Add(weighted_completion == sum(weighted_completion_terms))
                weighted_completion_avg = model.NewIntVar(
                    0, horizon_minutes, "weighted_completion_avg"
                )
                model.AddDivisionEquality(
                    weighted_completion_avg, weighted_completion, total_weight
                )
                objective = objective + weighted_completion_avg

    model.Minimize(objective)

    # ---- Решение ----
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(max_time_seconds)
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = log_search_progress

    status_code = solver.Solve(model)

    # ---- Извлечение решения ----
    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }
    status = status_map.get(status_code, f"CODE_{status_code}")

    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Интерпретируем время как "рабочие минуты" и переводим в wall-clock через календарь.
        # Чтобы не нарушать precedence (там сравниваются end/start в одной шкале),
        # используем единый global working window для всех машин.
        global_work_minutes_per_day = int(
            round(
                pd.Series([mp.working_minutes_per_day for mp in machine_params.values()]).median()
            )
        )
        global_work_minutes_per_day = max(1, global_work_minutes_per_day)

        def to_datetime(processing_minutes: int) -> datetime:
            day_idx = processing_minutes // global_work_minutes_per_day
            min_in_day = processing_minutes % global_work_minutes_per_day
            # В рамках одной календарной недели рабочее окно: [08:00, 08:00 + work_minutes_per_day)
            return planning_date + timedelta(
                days=day_idx,
                minutes=shift_start_minutes + min_in_day,
            )

        start_times = {i: solver.Value(start_proc[i]) for i in all_ops}
        end_times = {i: solver.Value(end_proc[i]) for i in all_ops}

        out_df = operations_df.copy()
        out_df["start_time"] = out_df["op_id"].map(start_times)
        out_df["end_time"] = out_df["op_id"].map(end_times)
        out_df["duration"] = out_df["op_id"].map(proc_duration)

        # Добавляем календарные даты (удобно для Ганта и выгрузки).
        out_df["working_minutes_per_day"] = global_work_minutes_per_day
        out_df["shift_start_minutes"] = shift_start_minutes
        out_df["start_datetime"] = out_df["start_time"].map(to_datetime)
        out_df["end_datetime"] = out_df["end_time"].map(to_datetime)

        out_df = out_df.sort_values(["product", "part_number", "process_sequence", "machine"])[
            [
                "product",
                "assembly",
                "part_number",
                "process_sequence",
                "process",
                "machine",
                "start_time",
                "end_time",
                "start_datetime",
                "end_datetime",
                "duration",
            ]
        ]

        solve_result = SolveResult(
            status=status,
            objective_value=float(solver.ObjectiveValue()),
            makespan_minutes=int(solver.Value(makespan)),
        )
        return out_df.reset_index(drop=True), solve_result

    solve_result = SolveResult(
        status=status,
        objective_value=None,
        makespan_minutes=None,
    )
    cols = [
        "product",
        "assembly",
        "part_number",
        "process_sequence",
        "process",
        "machine",
        "start_time",
        "end_time",
        "start_datetime",
        "end_datetime",
        "working_minutes_per_day",
        "shift_start_minutes",
        "duration",
    ]
    return pd.DataFrame(columns=cols), solve_result


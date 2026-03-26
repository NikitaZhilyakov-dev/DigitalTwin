from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd
from ortools.sat.python import cp_model  # type: ignore[reportMissingImports]

from .data_loader import MachineParams

def add_part_precedence(
    model: cp_model.CpModel,
    operations_df: pd.DataFrame,
    start_vars: Dict[int, cp_model.IntVar],
    end_vars: Dict[int, cp_model.IntVar],
) -> None:
    """
    Ограничение порядка операций для каждой детали (part_number):
    операция с process_sequence=k+1 не может начаться раньше завершения операции k.
    """
    for part_number, pdf in operations_df.groupby("part_number", sort=False):
        pdf = pdf.sort_values("process_sequence")
        idxs: List[int] = pdf["op_id"].tolist()
        for a, b in zip(idxs, idxs[1:]):
            model.Add(start_vars[b] >= end_vars[a])


def add_machine_no_overlap(
    model: cp_model.CpModel,
    operations_df: pd.DataFrame,
    occupancy_intervals: Dict[int, cp_model.IntervalVar],
) -> None:
    """
    Один станок не может выполнять две операции одновременно.

    Важно:
    - используется интервал "occupancy", который включает время обработки + обслуживание после операции,
      если обслуживание требуется на этом станке.
    """
    for machine, mdf in operations_df.groupby("machine", sort=False):
        idxs: List[int] = mdf["op_id"].tolist()
        if len(idxs) <= 1:
            continue
        model.AddNoOverlap([occupancy_intervals[i] for i in idxs])


def build_total_idle(
    model: cp_model.CpModel,
    operations_df: pd.DataFrame,
    start_vars: Dict[int, cp_model.IntVar],
    end_vars: Dict[int, cp_model.IntVar],
    machine_params: Dict[str, MachineParams],
    horizon_minutes: int,
) -> cp_model.IntVar:
    """
    Пытается минимизировать простой станков через оценку:
    idle_m = (last_end_proc - first_start_proc) - sum(proc_durations) - maintenance_gap*(n_ops-1)
    """
    idle_vars: List[cp_model.IntVar] = []
    for machine, mdf in operations_df.groupby("machine", sort=False):
        idxs: List[int] = mdf["op_id"].tolist()
        n_ops = len(idxs)
        if n_ops <= 1:
            idle_vars.append(model.NewIntVar(0, horizon_minutes, f"idle_{machine}_0"))
            continue

        first_start = model.NewIntVar(0, horizon_minutes, f"first_start_{machine}")
        last_end = model.NewIntVar(0, horizon_minutes, f"last_end_{machine}")
        model.AddMinEquality(first_start, [start_vars[i] for i in idxs])
        model.AddMaxEquality(last_end, [end_vars[i] for i in idxs])

        proc_total = int(mdf["processing_minutes"].sum())

        params = machine_params[str(machine)]
        g = params.maintenance_minutes if params.maintenance_required else 0
        maintenance_total = g * (n_ops - 1)

        idle_var = model.NewIntVar(0, horizon_minutes, f"idle_{machine}")
        model.Add(idle_var == last_end - first_start - proc_total - maintenance_total)
        idle_vars.append(idle_var)

    total_idle = model.NewIntVar(0, horizon_minutes * 1000, "total_idle")
    model.Add(total_idle == sum(idle_vars))
    return total_idle


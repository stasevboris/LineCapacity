from __future__ import annotations

from linecapacity.settings import CalculationSettings

from ..scheme.editor import EditError
from ..scheme.model import Scheme
from .results import run

SEASON_NAMES = {"0": "лето", "1": "зима"}


def season_row(scheme: Scheme, number: str, data: dict) -> dict:
    worst = scheme.consumers[data["min_consumer"]] if scheme.consumers else None
    transformer = data["transformer"]
    return {
        "season": SEASON_NAMES[number],
        "min_voltage": data["min_voltage"],
        "min_consumer": worst.address if worst else "",
        "voltage_loss_percent": data["voltage_loss_percent"],
        "loss_kw": data["loss_kw"],
        "loss_percent": data["loss_percent"],
        "max_temperature": data["max_temperature"],
        "max_line": scheme.lines[data["max_line"]].label if scheme.lines else "",
        "p_total_kw": data["p_total_kw"],
        "load_factor": transformer["load_factor"],
        "winding": transformer["winding"],
        "oil": transformer["oil"],
        "wear_hours": transformer["wear_hours"],
        "transformer_state": transformer["state"],
    }


def summary(scheme: Scheme, name: str, period: int, min_load: bool, settings: CalculationSettings) -> dict:
    row = {"name": name, "period": period, "min_load": min_load}
    try:
        result = run(scheme, period, min_load, settings)
    except EditError as error:
        return {**row, "error": str(error), "good": None, "seasons": [], "max_voltage": None}
    row["good"] = result["good"]
    row["error"] = None
    row["seasons"] = [season_row(scheme, number, result["seasons"][number]) for number in sorted(result["seasons"])]
    block = result["min_load_mode"]
    row["max_voltage"] = block["max_voltage"] if block else None
    row["max_consumer"] = scheme.consumers[block["max_consumer"]].address if block else None
    return row

from __future__ import annotations

from linecapacity.model import CircuitModel, PhaseMode
from linecapacity.settings import CalculationSettings
from linecapacity.solver import CalculationResults, calculate

from ..scheme.editor import EditError
from ..scheme.model import Scheme
from .bridge import to_model
from .losses import annual_losses
from .results import check_scheme, report

GOST_DEVIATION = 10.0
LOWER_IS_BETTER = ("voltage_loss_percent", "loss_kw", "max_temperature", "load_factor", "wear_hours",
                   "annual_kwh", "annual_cost_usd")


def own_voltages(model: CircuitModel, index: int, phases) -> list[float]:
    consumer = model.consumers[index]
    if consumer.phase_mode == PhaseMode.THREE_PHASE:
        return [float(value) for value in phases]
    return [float(phases[consumer.phase_no - 1])]


def gost_quality(model: CircuitModel, results: CalculationResults, settings: CalculationSettings) -> dict:
    nominal = settings.voltage_rated
    worst_low = 0.0
    worst_high = 0.0
    outside: set[int] = set()
    rows = []
    modes = [(f"{number}", results.seasons[number].phase_voltages) for number in results.season_order]
    if results.min_load_voltages:
        modes.append(("2", results.min_load_voltages))
    for index, consumer in enumerate(model.consumers):
        low = high = 0.0
        for _, voltages in modes:
            for value in own_voltages(model, index, voltages[index]):
                deviation = (value - nominal) * 100.0 / nominal
                low, high = min(low, deviation), max(high, deviation)
        if low < -GOST_DEVIATION or high > GOST_DEVIATION:
            outside.add(index)
        worst_low, worst_high = min(worst_low, low), max(worst_high, high)
        rows.append({"consumer": consumer.address or consumer.label, "low_percent": low, "high_percent": high,
                     "ok": index not in outside})
    return {"ok": not outside, "outside": len(outside), "total": len(model.consumers), "nominal": nominal,
            "worst_low_percent": worst_low, "worst_high_percent": worst_high, "consumers": rows}


def variant_row(name: str, scheme: Scheme, settings: CalculationSettings, period: int, min_load: bool,
                price_usd: float | None) -> dict:
    row = {"name": name}
    try:
        check_scheme(scheme)
    except EditError as error:
        return {**row, "error": str(error)}
    model = to_model(scheme)
    results = calculate(model, settings, period, min_load)
    with_min = bool(results.has_typical and results.min_load_requested and results.min_load_voltages)
    _, good = report(scheme, model, settings, results, with_min)
    seasons = [results.seasons[number] for number in results.season_order]
    quality = gost_quality(model, results, settings)
    worst = min(seasons, key=lambda season: season.lowest_voltage)
    row.update({
        "error": None,
        "good": good,
        "quality": quality,
        "min_voltage": min(season.lowest_voltage for season in seasons),
        "min_consumer": scheme.consumers[worst.lowest_consumer].address if scheme.consumers else "",
        "voltage_loss_percent": max(season.voltage_loss_percent for season in seasons),
        "loss_kw": max(season.line_loss_kw for season in seasons),
        "max_temperature": max(season.hottest_temperature for season in seasons),
        "load_factor": max(max(season.load_factor) for season in seasons),
        "wear_hours": max(season.wear_hours for season in seasons),
        "annual": None,
    })
    if price_usd is not None:
        try:
            row["annual"] = annual_losses(model, results, price_usd)
        except EditError:
            row["annual"] = None
    row["annual_kwh"] = row["annual"]["total_kwh"] if row["annual"] else None
    row["annual_cost_usd"] = row["annual"]["cost_usd"] if row["annual"] else None
    return row


def rank_key(row: dict) -> tuple:
    return (not row["good"], not row["quality"]["ok"], -row["min_voltage"], row["loss_kw"])


def compare(rows: list[dict]) -> dict:
    valid = [index for index, row in enumerate(rows) if not row.get("error")]
    best = min(valid, key=lambda index: rank_key(rows[index])) if valid else None
    marks = {}
    if valid:
        marks["min_voltage"] = max(rows[index]["min_voltage"] for index in valid)
        for key in LOWER_IS_BETTER:
            values = [rows[index][key] for index in valid if rows[index].get(key) is not None]
            if values:
                marks[key] = min(values)
    return {"rows": rows, "best": best, "best_values": marks}

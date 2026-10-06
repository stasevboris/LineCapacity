from __future__ import annotations

from linecapacity.model import CircuitModel, LineType, PhaseMode
from linecapacity.settings import CalculationSettings
from linecapacity.solver import CalculationResults, Layout, calculate

from ..scheme.editor import EditError
from ..scheme.model import Scheme
from .bridge import to_model
from .results import check_scheme


def pole_voltages(potentials, node: int) -> list[float]:
    neutral = potentials[node + 3]
    return [float(abs(potentials[node + phase] - neutral)) for phase in range(3)]


def path_to(model: CircuitModel, layout: Layout, consumer_index: int) -> list[tuple[str, int, float]]:
    consumer = model.consumers[consumer_index]
    steps: list[tuple[str, int, float]] = []
    point = (consumer.x, consumer.y)
    guard = 0
    while guard <= len(model.lines):
        guard += 1
        line_index = layout.ending.get(point)
        if line_index is None:
            raise EditError("Потребитель не присоединён к шинам ТП")
        line = model.lines[line_index]
        if line.line_type == LineType.OUTGOING:
            steps.append(("bus", -1, line.length_m))
            return list(reversed(steps))
        pole_index = layout.poles.get((line.x, line.y))
        if pole_index is None:
            raise EditError("Потребитель не присоединён к шинам ТП")
        steps.append(("pole", pole_index, line.length_m))
        pole = model.poles[pole_index]
        point = (pole.x, pole.y)
    raise EditError("Потребитель не присоединён к шинам ТП")


def voltage_profile(scheme: Scheme, settings: CalculationSettings, consumer_index: int | None = None,
                    season: int = 1) -> dict:
    check_scheme(scheme)
    model = to_model(scheme)
    results: CalculationResults = calculate(model, settings, season, False)
    data = results.seasons[season]
    index = data.lowest_consumer if consumer_index is None else consumer_index
    if not 0 <= index < len(model.consumers):
        raise EditError("Потребитель не найден")
    layout = Layout(model)
    points = []
    distance = 0.0
    for kind, number, length in path_to(model, layout, index):
        if kind == "bus":
            points.append({"name": "Шины ТП", "distance_m": 0.0,
                           "voltages": [float(abs(value)) for value in data.bus_voltages]})
        else:
            pole = model.poles[number]
            points.append({"name": f"Опора {pole.label}", "distance_m": distance,
                           "voltages": pole_voltages(data.potentials, 3 + 4 * number)})
        distance += length
    consumer = model.consumers[index]
    voltages = [float(value) for value in data.phase_voltages[index]]
    if consumer.phase_mode == PhaseMode.SINGLE_PHASE:
        voltages = [value if phase == consumer.phase_no - 1 else None for phase, value in enumerate(voltages)]
    points.append({"name": consumer.address or f"Потребитель {consumer.label}",
                   "distance_m": distance, "voltages": voltages})
    return {"season": season, "consumer": index, "points": points,
            "limits": {"low": settings.voltage_min, "high": settings.voltage_max}}

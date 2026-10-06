from __future__ import annotations

import math
from typing import Any

import numpy as np

from linecapacity.constants import (
    BARE_WIRE_LIMIT,
    LONG_OVERLOAD_WEAR_HOURS,
    OIL_LIMIT,
    OIL_OVERLOAD,
    PVC_WIRE_LIMIT,
    WINDING_LIMIT,
    WINDING_OVERLOAD,
    XLPE_WIRE_LIMIT,
)
from linecapacity.model import CircuitModel, Consumer, InsulationType, Line, LineType, PhaseMode
from linecapacity.settings import CalculationSettings
from linecapacity.solver import CalculationResults, SeasonResult, calculate, pole_lookup

from ..scheme.editor import EditError
from ..scheme.model import Scheme
from .bridge import to_model
from .text import fixed, general

HEAT_LIMITS = {InsulationType.NONE: BARE_WIRE_LIMIT, InsulationType.XLPE: XLPE_WIRE_LIMIT,
               InsulationType.PVC: PVC_WIRE_LIMIT}
CURRENT_SHOWN_MIN = 0.001
VOLTAGE_SHOWN_MIN = 0.1
REPORT_TITLES = {0: "Расчёт для летнего периода:", 1: "Расчёт для зимнего периода:"}
REFUSED = " Расчёт не запущен!"

Row = dict[str, str]
Phases = tuple[float, float, float]


def check_scheme(scheme: Scheme) -> None:
    for line in scheme.lines:
        for point in scheme.connection_points:
            if point.x == line.end_x and point.y == line.end_y:
                if point.active:
                    raise EditError("В схеме имеются неприсоединённые ЛЭП!" + REFUSED)
                break
    if not scheme.consumers:
        raise EditError("В схеме отсутствуют потребители!" + REFUSED)
    if not scheme.lines:
        raise EditError("В схеме отсутствуют ЛЭП!" + REFUSED)
    if any(line.length_m == 0 for line in scheme.lines):
        raise EditError("В схеме имеются ЛЭП нулевой длины!" + REFUSED)
    ends = {(line.end_x, line.end_y) for line in scheme.lines}
    if any((consumer.x, consumer.y) not in ends for consumer in scheme.consumers):
        raise EditError("В схеме имеются потребители, не присоединённые к ЛЭП!" + REFUSED)
    if any((pole.x, pole.y) not in ends for pole in scheme.poles):
        raise EditError("В схеме имеются опоры без питающей ЛЭП!" + REFUSED)
    poles = pole_lookup(scheme.poles)
    for line in scheme.lines:
        if line.line_type != LineType.OUTGOING and (line.x, line.y) not in poles:
            raise EditError(f"ЛЭП «{line.label}» не начинается на опоре!" + REFUSED)
        if Line(type_name=line.type_name).section_mm2() is None:
            raise EditError(f"В марке провода «{line.type_name}» ЛЭП «{line.label}» нет сечения жилы!" + REFUSED)
    for consumer in scheme.consumers:
        if consumer.load_type == 1 and consumer.cos_phi <= 0:
            raise EditError(f"У потребителя «{consumer.label}» с индивидуальной нагрузкой cos φ не больше нуля!"
                            + REFUSED)


def voltage_branches(model: CircuitModel) -> int:
    return sum(3 if consumer.phase_mode == PhaseMode.THREE_PHASE else 1 for consumer in model.consumers)


def consumer_voltages(consumer: Consumer, phases: Phases) -> list[float]:
    if consumer.phase_mode == PhaseMode.THREE_PHASE:
        return [float(v) for v in phases]
    return [float(phases[consumer.phase_no - 1])]


def overheated(line: Line, temperature: float) -> bool:
    return bool(temperature > HEAT_LIMITS.get(line.insulation(), BARE_WIRE_LIMIT))


def outside(voltage: float, settings: CalculationSettings) -> bool:
    return bool(voltage < settings.voltage_min or voltage > settings.voltage_max)


def transformer_state(season: SeasonResult) -> tuple[str, bool]:
    if season.oil_peak > OIL_LIMIT or season.winding_peak > WINDING_LIMIT:
        return "Внимание! Недопустимая температура трансформатора!", True
    if season.oil_peak > OIL_OVERLOAD or season.winding_peak > WINDING_OVERLOAD:
        if season.wear_hours < LONG_OVERLOAD_WEAR_HOURS:
            return "Трансформатор работает с кратковременной (допустимой) перегрузкой!", True
        return "Внимание! Трансформатор работает с длительной перегрузкой!", True
    return "Трансформатор работает без перегрузки!", False


def hottest_line_text(scheme: Scheme, index: int) -> str:
    poles = pole_lookup(scheme.poles)
    line = scheme.lines[index]

    def pole(x: int, y: int) -> str:
        return scheme.poles[poles.get((x, y), 0)].label if scheme.poles else ""

    if line.line_type == LineType.OUTGOING:
        return f"Максимальная температура на ЛЭП между ТП и опорой №{pole(line.end_x, line.end_y)}"
    if line.line_type in (LineType.SPAN, LineType.BRANCH_TO_LINE):
        return (f"Максимальная температура на ЛЭП между опорами №{pole(line.x, line.y)}"
                f" и №{pole(line.end_x, line.end_y)}")
    consumer = next((c for c in scheme.consumers if c.x == line.end_x and c.y == line.end_y), scheme.consumers[0])
    return f"Максимальная температура на ЛЭП между опорой №{pole(line.x, line.y)} и потребителем: {consumer.address}"


def extra_load_marks(model: CircuitModel, settings: CalculationSettings, targets: list[list[int]]) -> list[bool]:
    marks = []
    for index, consumer in enumerate(model.consumers):
        feeders = targets[consumer.phase_no - 1] if 1 <= consumer.phase_no <= 3 else []
        marks.append(bool(settings.extra_load_enabled and consumer.phase_mode == PhaseMode.SINGLE_PHASE
                          and consumer.feeder_no < len(feeders) and feeders[consumer.feeder_no] == index))
    return marks


def season_headers(number: int) -> list[str]:
    return ["Летний период:"] if number == 0 else ["", "Зимний период:"]


def current_text(value: complex) -> str:
    magnitude = abs(complex(value))
    return fixed(0.0 if magnitude < CURRENT_SHOWN_MIN else magnitude, 5, 3)


def voltage_text(value: float) -> str:
    return fixed(0.0 if value < VOLTAGE_SHOWN_MIN else value, 4, 1)


def line_memo(model: CircuitModel, results: CalculationResults, index: int) -> list[str]:
    line = model.lines[index]
    offset = results.wire_offsets[index]
    rows = []
    for number in results.season_order:
        season = results.seasons[number]
        rows += season_headers(number)
        wires = season.wire_currents[offset:offset + 4]
        if line.phase_mode == PhaseMode.THREE_PHASE:
            rows += [f"Ток в фазном проводе L{i + 1}: {current_text(wires[i])} А" for i in range(3)]
            rows.append(f"Ток в нулевом проводе: {current_text(wires[3])} А")
        else:
            rows.append(f"Ток в фазном проводе: {current_text(wires[0])} А")
            rows.append(f"Ток в нулевом проводе: {current_text(wires[1])} А")
        rows.append(f"Температура провода: {fixed(season.wire_temperatures[index], 4, 1)} град. Цельсия")
    return rows


def voltage_rows(consumer: Consumer, phases: Phases) -> list[str]:
    if consumer.phase_mode == PhaseMode.THREE_PHASE:
        return [f"Напряжение фазы L{i + 1}: {voltage_text(v)} B" for i, v in enumerate(phases)]
    return [f"Напряжение: {voltage_text(phases[consumer.phase_no - 1])} В"]


def consumer_memo(model: CircuitModel, results: CalculationResults, index: int, marked: bool,
                  min_load: bool) -> list[str]:
    consumer = model.consumers[index]
    rows = []
    for number in results.season_order:
        season = results.seasons[number]
        rows += season_headers(number)
        rows += voltage_rows(consumer, season.phase_voltages[index])
        if consumer.phase_mode == PhaseMode.SINGLE_PHASE and marked:
            rows.append("Потребителю добавлена мощность утяжеления!")
        rows.append(f"Активная мощность: {fixed(season.consumer_p[index] / 1000.0, 5, 2)} кВт")
        rows.append(f"Реактивная мощность: {fixed(season.consumer_q[index] / 1000.0, 5, 2)} квар")
    if min_load:
        rows += ["", "Режим минимальных нагрузок:"]
        rows += voltage_rows(consumer, results.min_load_voltages[index])
    return rows


def transformer_memo(model: CircuitModel, results: CalculationResults) -> list[str]:
    rows = []
    for number in results.season_order:
        season = results.seasons[number]
        rows += season_headers(number)
        rows += [f"U{i + 1}= {fixed(abs(complex(u)), 4, 1)} В" for i, u in enumerate(season.bus_voltages)]
        rows += [f"P{i + 1}= {fixed(p / 1000.0, 5, 2)} кВт" for i, p in enumerate(season.phase_p)]
        rows += [f"Q{i + 1}= {fixed(q / 1000.0, 5, 2)} квар" for i, q in enumerate(season.phase_q)]
        rows.append(f"Мощность утяжеления нагрузки: {fixed(season.extra_load_w / 1000.0, 5, 2)} кВт")
        rows.append("Параметры трансформатора:")
        rows.append(f" макс. мощность загрузки: {fixed(season.load_va / 1000.0, 5, 2)} кВA")
        rows.append(f" макс. коэффициент загрузки: {fixed(max(season.load_factor), 4, 2)}")
        if not model.transformer.is_dry():
            rows.append(f" макс. температура масла: {fixed(season.oil_peak, 4, 1)} град. Цельсия")
        rows.append(f" макс. температура обмоток: {fixed(season.winding_peak, 4, 1)} град. Цельсия")
        rows.append(f" суточный износ изоляции: {fixed(season.wear_hours, 6, 2)} ч")
    return rows


def transformer_charts(model: CircuitModel, results: CalculationResults) -> dict[str, dict]:
    oil = not model.transformer.is_dry()
    charts = {}
    for number in results.season_order:
        season = results.seasons[number]
        charts[str(number)] = {
            "load": [float(value) for value in season.load_factor],
            "winding": [float(value) for value in season.winding_temps],
            "oil": [float(value) for value in season.oil_temps] if oil else None,
        }
    return charts


def consumer_labels(model: CircuitModel, settings: CalculationSettings, voltages: list[Phases]) -> list[list[dict]]:
    return [[{"text": general(v, 4), "bad": outside(v, settings)} for v in consumer_voltages(consumer, phases)]
            for consumer, phases in zip(model.consumers, voltages, strict=True)]


def season_labels(model: CircuitModel, settings: CalculationSettings, season: SeasonResult) -> dict:
    head = "" if model.transformer.is_dry() else f"Масло: {fixed(season.oil_peak, 4, 1)} град.  "
    return {
        "consumers": consumer_labels(model, settings, season.phase_voltages),
        "lines": [{"text": fixed(t, 4, 1), "bad": overheated(line, t)}
                  for line, t in zip(model.lines, season.wire_temperatures, strict=True)],
        "bus": [{"text": f"U{i + 1}={fixed(abs(complex(u)), 4, 1)} В", "bad": outside(abs(complex(u)), settings)}
                for i, u in enumerate(season.bus_voltages)],
        "sums": [
            f"P={fixed((season.bus_p - season.extra_load_w) / 1000.0, 5, 2)} кВт",
            f"Q={fixed(season.bus_q / 1000.0, 5, 2)} квар",
            f"Pут={fixed(season.extra_load_w / 1000.0, 5, 2)} кВт",
        ],
        "transformer": f"{head}Обмотки: {fixed(season.winding_peak, 4, 1)} град.",
        "min_consumer": int(season.lowest_consumer),
        "max_line": int(season.hottest_line),
    }


def season_numbers(model: CircuitModel, season: SeasonResult) -> dict:
    state, alarm = transformer_state(season)
    return {
        "min_voltage": float(season.lowest_voltage),
        "min_consumer": int(season.lowest_consumer),
        "max_temperature": float(season.hottest_temperature),
        "max_line": int(season.hottest_line),
        "voltage_loss_percent": float(season.voltage_loss_percent),
        "consumer_voltages": [consumer_voltages(c, v) for c, v in zip(model.consumers, season.phase_voltages,
                                                                       strict=True)],
        "line_temperatures": [float(t) for t in season.wire_temperatures],
        "p_consumers_kw": [float(p) / 1000.0 for p in season.consumer_p],
        "q_consumers_kvar": [float(q) / 1000.0 for q in season.consumer_q],
        "bus_voltages": [abs(complex(u)) for u in season.bus_voltages],
        "p_total_kw": float(season.bus_p - season.extra_load_w) / 1000.0,
        "q_total_kvar": float(season.bus_q) / 1000.0,
        "extra_load_kw": float(season.extra_load_w) / 1000.0,
        "loss_kw": float(season.line_loss_kw),
        "loss_percent": float(season.line_loss_percent),
        "transformer": {
            "oil": None if model.transformer.is_dry() else float(season.oil_peak),
            "winding": float(season.winding_peak),
            "wear_hours": float(season.wear_hours),
            "load_kva": float(season.load_va) / 1000.0,
            "load_factor": float(max(season.load_factor)),
            "state": state,
            "alarm": alarm,
        },
    }


def report(scheme: Scheme, model: CircuitModel, settings: CalculationSettings, results: CalculationResults,
           min_load: bool) -> tuple[list[Row], bool]:
    rows: list[Row] = []
    good = True

    def say(message: str, tone: str) -> None:
        rows.append({"text": message, "tone": tone})

    for number in results.season_order:
        season = results.seasons[number]
        say(REPORT_TITLES[number], "title")
        consumer = model.consumers[season.lowest_consumer]
        say(f"Минимальное напряжение у потребителя с адресом: {consumer.address}", "info")
        say(f"Значение минимального напряжения: {fixed(season.lowest_voltage, 4, 1)} В", "value")
        if season.lowest_voltage <= settings.voltage_min:
            say("Внимание! Недопустимо низкое напряжение у потребителя!", "alert")
        if season.lowest_voltage >= settings.voltage_max:
            say("Внимание! Недопустимо высокое напряжение у потребителя!", "alert")
        say(f"Максимальные потери напряжения на ЛЭП: {fixed(season.voltage_loss_percent, 4, 1)}%", "value")
        if season.voltage_loss_percent >= settings.voltage_loss_limit:
            say("Внимание! Недопустимо высокие потери напряжения!", "alert")
            good = False
        say(f"Потери мощности в ЛЭП: {fixed(season.line_loss_kw, 5, 2)} кВт "
            f"({fixed(season.line_loss_percent, 4, 2)}%)", "value")
        say(hottest_line_text(scheme, season.hottest_line), "info")
        say(f"Значение максимальной температуры на ЛЭП: {fixed(season.hottest_temperature, 4, 1)} град. Цельсия",
            "value")
        if overheated(model.lines[season.hottest_line], season.hottest_temperature):
            say("Внимание! Недопустимая температура провода!", "alert")
            good = False
        state, alarm = transformer_state(season)
        say(state, "alert" if alarm else "ok")
        if state.startswith("Внимание! Трансформатор работает с длительной"):
            say("Суточный износ изоляции трансформатора превышает 24 часа!", "alert")
        if alarm and not state.startswith("Трансформатор работает с кратковременной"):
            good = False
        shares = season.phase_shares
        say("Распределение активной мощности по фазам на шинах ТП: "
            f"L1: {fixed(shares[0], 4, 1)}%; L2: {fixed(shares[1], 4, 1)}%; L3: {fixed(shares[2], 4, 1)}%",
            "phase")
        say("", "gap")
        say("", "gap")
    if min_load:
        say("Расчёт в режиме минимальных нагрузок:", "title")
        consumer = model.consumers[results.min_load_peak_consumer]
        say(f"Максимальное напряжение у потребителя с адресом: {consumer.address}", "info")
        say(f"Значение максимального напряжения: {fixed(results.min_load_peak, 4, 1)} В", "value")
        if results.min_load_peak >= settings.voltage_max:
            say("Внимание! Недопустимо высокое напряжение у потребителя!", "alert")
    say("", "gap")
    say("", "gap")
    say("Заключение о пропускной способности сети:", "title")
    say("Пропускная способность сети достаточна!" if good else "Пропускная способность сети недостаточна!",
        "good" if good else "alert")
    return rows, good


def plain(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: plain(item) for key, item in data.items()}
    if isinstance(data, (list, tuple)):
        return [plain(item) for item in data]
    if isinstance(data, np.generic):
        data = data.item()
    if isinstance(data, float) and not math.isfinite(data):
        return None
    return data


def run(scheme: Scheme, period: int = 2, min_load: bool = True, settings: CalculationSettings | None = None) -> dict:
    check_scheme(scheme)
    model = to_model(scheme)
    settings = settings or CalculationSettings()
    results = calculate(model, settings, period, min_load)
    with_min_load = bool(results.has_typical and results.min_load_requested and results.min_load_voltages)
    marks = extra_load_marks(model, settings, results.extra_load_targets)
    rows, good = report(scheme, model, settings, results, with_min_load)
    seasons = {str(n): season_numbers(model, results.seasons[n]) for n in results.season_order}
    labels = {str(n): season_labels(model, settings, results.seasons[n]) for n in results.season_order}
    if with_min_load:
        labels["2"] = {"consumers": consumer_labels(model, settings, results.min_load_voltages)}
    memo = {
        "transformer": transformer_memo(model, results),
        "lines": [line_memo(model, results, i) for i in range(len(model.lines))],
        "consumers": [consumer_memo(model, results, i, marks[i], with_min_load) for i in range(len(model.consumers))],
    }
    min_load_block = None
    if with_min_load:
        min_load_block = {
            "consumer_voltages": [consumer_voltages(c, v) for c, v in zip(model.consumers, results.min_load_voltages,
                                                                           strict=True)],
            "max_voltage": float(results.min_load_peak),
            "max_consumer": int(results.min_load_peak_consumer),
        }
    return plain({
        "period": period,
        "min_load": with_min_load,
        "good": good,
        "seasons": seasons,
        "min_load_mode": min_load_block,
        "labels": labels,
        "memo": memo,
        "charts": transformer_charts(model, results),
        "report": rows,
        "show_report": len(model.consumers) > 1,
        "report_ready": voltage_branches(model) > 1,
    })

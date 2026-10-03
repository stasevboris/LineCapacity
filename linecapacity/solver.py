from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu

from .constants import (
    AIR_PRESSURE_PA,
    ALUMINIUM_TEMP_COEFF,
    BARE_DIAMETER_FACTOR,
    BARE_REFERENCE_TEMP,
    CONVECTION_COEFF,
    COOLING_BY_CORES,
    COPPER_TEMP_COEFF,
    DEFAULT_SECTION_M2,
    DRY_TIME_CONSTANT_S,
    EMISSIVITY,
    HALF_HOURS,
    HOURS_PER_YEAR,
    INSULATED_REFERENCE_TEMP,
    INSULATION_THICKNESS_M,
    KELVIN,
    MIN_SURFACE_RISE,
    OIL_EXPONENT,
    OIL_RISE_RATED,
    OIL_TIME_CONSTANT_S,
    PVC_CONDUCTIVITY,
    START_HEAT_TRANSFER,
    STEFAN_BOLTZMANN,
    STEP_S,
    THERMAL_ITERATIONS,
    WEAR_DOUBLING_STEP,
    WEAR_REFERENCE_TEMP,
    WINDING_EXPONENT,
    WINDING_GRADIENT_RATED,
    WIRE_HEATING_ALLOWANCE,
    XLPE_CONDUCTIVITY,
    seasons_for,
)
from .model import (
    CircuitModel,
    ConsumerCategory,
    ConsumerLoadType,
    InsulationType,
    Line,
    LineType,
    PhaseMode,
    WireMaterial,
)
from .settings import CalculationSettings

TIE = 1e-9
TINY = 1e-9
NEGLIGIBLE_KW = 1e-15
OPEN_OHM = 1e15
MINIMAL_SEASON = 2
BRANCH_STEP = 30
QUIET_POWER_W = 0.01
DEFAULT_RATIO = 25.0
Phases = tuple[float, float, float]


@dataclass
class SeasonResult:
    potentials: np.ndarray
    branch_voltages: np.ndarray
    wire_currents: np.ndarray
    phase_voltages: list[Phases]
    consumer_p: list[float]
    consumer_q: list[float]
    wire_temperatures: list[float]
    oil_peak: float
    winding_peak: float
    voltage_loss_percent: float
    lowest_voltage: float
    lowest_consumer: int
    hottest_temperature: float
    hottest_line: int
    bus_p: float
    bus_q: float
    phase_p: Phases
    phase_q: Phases
    extra_load_w: float
    load_va: float
    load_curve_va: list[float]
    load_factor: list[float]
    wear_hours: float
    winding_temps: list[float]
    oil_temps: list[float]
    bus_voltages: tuple[complex, complex, complex]
    feeder_currents: list[complex]
    line_loss_kw: float
    line_loss_percent: float
    phase_shares: Phases
    load_impedances: list[tuple[float, float]]


@dataclass
class CalculationResults:
    seasons: dict[int, SeasonResult] = field(default_factory=dict)
    season_order: list[int] = field(default_factory=list)
    has_typical: bool = False
    min_load_requested: bool = True
    min_load_voltages: list[Phases] = field(default_factory=list)
    min_load_peak: float = 0.0
    min_load_peak_consumer: int = 0
    extra_load_targets: list[list[int]] = field(default_factory=list)
    wire_offsets: list[int] = field(default_factory=list)


def power(base: float, exponent: float) -> float:
    try:
        return base**exponent
    except OverflowError:
        return math.inf


def _phasor(magnitude: float, angle_deg: float) -> complex:
    angle = math.radians(angle_deg)
    return complex(magnitude * math.cos(angle), magnitude * math.sin(angle))


def _is_single_drop(line: Line) -> bool:
    return line.phase_mode == PhaseMode.SINGLE_PHASE and line.line_type == LineType.BRANCH_TO_CONSUMER


def pole_lookup(poles: list) -> dict[tuple[int, int], int]:
    found: dict[tuple[int, int], int] = {}
    for index, pole in enumerate(poles):
        found.setdefault((pole.x, pole.y), index)
        found.setdefault((pole.end_x, pole.end_y), index)
        for branch in range(pole.branch_count):
            found.setdefault((pole.x + (branch + 1) * BRANCH_STEP, pole.y), index)
    return found


class Layout:
    def __init__(self, model: CircuitModel) -> None:
        self.wire_offsets: list[int] = []
        position = 3
        for line in model.lines:
            self.wire_offsets.append(position)
            position += 2 if _is_single_drop(line) else 4
        self.load_offsets: list[int] = []
        self.inlet_nodes: list[int] = []
        branch = position
        node = 3 + 4 * len(model.poles)
        for consumer in model.consumers:
            self.load_offsets.append(branch)
            self.inlet_nodes.append(node)
            three = consumer.phase_mode == PhaseMode.THREE_PHASE
            branch += 3 if three else 1
            node += 4 if three else 2
        self.nodes = node
        self.branches = branch
        self.poles = pole_lookup(model.poles)
        self.starting: dict[tuple[int, int], int] = {}
        self.ending: dict[tuple[int, int], int] = {}
        for index, line in enumerate(model.lines):
            self.starting.setdefault((line.x, line.y), index)
            self.ending.setdefault((line.end_x, line.end_y), index)
        self.taps: dict[tuple[int, int], tuple[int, int]] = {}
        for point in model.connection_points:
            pole_index = self.poles.get((point.x, point.y))
            if point.point_kind == 2 and pole_index is not None:
                self.taps.setdefault((pole_index, point.branch_no), (point.x, point.y))


class Connections:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], float] = {}

    def put(self, node: int, branch: int, sign: float) -> None:
        self.cells[(node, branch)] = sign

    def by_branch(self) -> dict[int, list[tuple[int, float]]]:
        grouped: dict[int, list[tuple[int, float]]] = {}
        for (node, branch), sign in sorted(self.cells.items(), key=lambda item: (item[0][1], item[0][0])):
            if sign:
                grouped.setdefault(branch, []).append((node, sign))
        return grouped

    @staticmethod
    def wire_signs(leaving: bool, phase: int | None) -> list[float]:
        sign = 1.0 if leaving else -1.0
        signs = [sign, sign, sign] if phase is None else [sign if p == phase - 1 else 0.0 for p in range(3)]
        return signs + [-sign]

    def four_wires(self, node: int, branch: int, leaving: bool) -> None:
        for offset, sign in enumerate(self.wire_signs(leaving, None)):
            self.put(node + offset, branch + offset, sign)

    def phase_wires(self, node: int, branch: int, leaving: bool, phase: int | None) -> None:
        for offset, sign in enumerate(self.wire_signs(leaving, phase)[:3]):
            self.put(node + offset, branch + offset, sign)

    def phases_to_one_node(self, node: int, branch: int, leaving: bool, phase: int | None) -> None:
        for offset, sign in enumerate(self.wire_signs(leaving, phase)[:3]):
            self.put(node, branch + offset, sign)

    def one_wire_from_phases(self, node: int, branch: int, leaving: bool, phase: int) -> None:
        signs = self.wire_signs(leaving, phase)
        for offset in range(3):
            self.put(node + offset, branch, signs[offset])
        self.put(node + 3, branch + 1, signs[3])

    def single(self, node: int, branch: int, leaving: bool) -> None:
        self.put(node, branch, 1.0 if leaving else -1.0)


def _connect(model: CircuitModel, layout: Layout) -> Connections:
    links = Connections()
    links.phase_wires(0, 0, False, None)
    for index, line in enumerate(model.lines):
        if line.line_type == LineType.OUTGOING:
            links.phase_wires(0, layout.wire_offsets[index], True, None)
    for pole_index, pole in enumerate(model.poles):
        node = 4 * pole_index + 3
        feeding = layout.ending.get((pole.x, pole.y))
        if feeding is not None:
            links.four_wires(node, layout.wire_offsets[feeding], False)
        onward = layout.starting.get((pole.end_x, pole.end_y))
        if onward is not None:
            links.four_wires(node, layout.wire_offsets[onward], True)
        for branch in range(pole.branch_count):
            tap = layout.taps.get((pole_index, branch + 1))
            line_index = layout.starting.get(tap) if tap else None
            if line_index is None:
                continue
            line = model.lines[line_index]
            if line.phase_mode == PhaseMode.THREE_PHASE or line.line_type == LineType.BRANCH_TO_LINE:
                links.four_wires(node, layout.wire_offsets[line_index], True)
            else:
                links.one_wire_from_phases(node, layout.wire_offsets[line_index], True, line.phase_no)
    for consumer_index, consumer in enumerate(model.consumers):
        line_index = layout.ending.get((consumer.x, consumer.y))
        if line_index is None:
            continue
        line = model.lines[line_index]
        node = layout.inlet_nodes[consumer_index]
        wire = layout.wire_offsets[line_index]
        load = layout.load_offsets[consumer_index]
        single_line = line.phase_mode == PhaseMode.SINGLE_PHASE
        phase = line.phase_no if single_line else None
        if single_line:
            links.single(node, wire, False)
        else:
            links.phase_wires(node, wire, False, None)
        if consumer.phase_mode == PhaseMode.THREE_PHASE:
            links.phase_wires(node, load, True, phase)
            links.phases_to_one_node(node + 3, load, False, phase)
            links.single(node + 3, wire + 3, True)
        else:
            links.single(node, load, True)
            links.single(node + 1, load, False)
            links.single(node + 1, wire + 1, True)
    return links


def _solve(
    by_branch: dict[int, list[tuple[int, float]]], admittance: np.ndarray, emf: np.ndarray, nodes: int
) -> np.ndarray:
    stamps: dict[tuple[int, int], complex] = {}
    injected = np.zeros((nodes,), dtype=complex)
    for branch, ends in by_branch.items():
        conductance = admittance[branch]
        for first, first_sign in ends:
            for second, second_sign in ends:
                key = (first, second)
                stamps[key] = stamps.get(key, 0j) + first_sign * conductance * second_sign
            if emf[branch]:
                injected[first] -= first_sign * conductance * emf[branch]
    matrix = sparse.csc_matrix(
        (list(stamps.values()), ([key[0] for key in stamps], [key[1] for key in stamps])),
        shape=(nodes, nodes),
        dtype=complex,
    )
    try:
        return splu(matrix).solve(injected)
    except RuntimeError:
        dense = matrix.toarray()
        try:
            return np.linalg.solve(dense, injected)
        except np.linalg.LinAlgError:
            return np.linalg.lstsq(dense, injected, rcond=None)[0]


def extra_load_targets(model: CircuitModel, phase_no: int) -> list[int]:
    targets = [0] * model.outgoing_count
    for feeder in range(model.outgoing_count):
        farthest_x = 0
        for index, consumer in enumerate(model.consumers):
            eligible = (
                consumer.feeder_no == feeder
                and consumer.phase_mode == PhaseMode.SINGLE_PHASE
                and consumer.phase_no == phase_no
                and consumer.load_type == ConsumerLoadType.TYPICAL
            )
            if eligible and consumer.x > farthest_x:
                targets[feeder] = index
                farthest_x = consumer.x
    return targets


def _load_impedance(
    settings: CalculationSettings, three_phase: bool, p_kw: float, cos_phi: float
) -> tuple[float, float]:
    apparent = p_kw / cos_phi if cos_phi else 0.0
    q_kvar = math.sqrt(max(apparent * apparent - p_kw * p_kw, 0.0)) or NEGLIGIBLE_KW
    p_kw = p_kw or NEGLIGIBLE_KW
    factor = 3 if three_phase else 1
    return factor * settings.voltage_rated**2 / (p_kw * 1e3), factor * settings.voltage_rated**2 / (q_kvar * 1e3)


def _standard_load(
    settings: CalculationSettings,
    category: ConsumerCategory,
    season: int,
    scale: float,
    annual_kwh: float,
    extra_kw: float,
) -> tuple[float, float] | None:
    around_the_clock = annual_kwh / HOURS_PER_YEAR
    table = {
        0: {
            ConsumerCategory.HOUSEHOLD_NO_CIE: (settings.home_summer_kw * scale + extra_kw, settings.home_summer_cos),
            ConsumerCategory.HOUSEHOLD_WITH_CIE: (
                settings.electric_home_summer_kw * scale,
                settings.electric_home_summer_cos,
            ),
            ConsumerCategory.LIGHTING: (settings.street_light_summer_kw * scale, settings.street_light_summer_cos),
            ConsumerCategory.OTHER: (around_the_clock, settings.home_winter_cos),
        },
        1: {
            ConsumerCategory.HOUSEHOLD_NO_CIE: (settings.home_winter_kw * scale + extra_kw, settings.home_winter_cos),
            ConsumerCategory.HOUSEHOLD_WITH_CIE: (
                settings.electric_home_winter_kw * scale,
                settings.electric_home_winter_cos,
            ),
            ConsumerCategory.LIGHTING: (settings.street_light_winter_kw * scale, settings.street_light_winter_cos),
            ConsumerCategory.OTHER: (around_the_clock, settings.home_winter_cos),
        },
        MINIMAL_SEASON: {
            ConsumerCategory.HOUSEHOLD_NO_CIE: (settings.home_minimal_kw * scale, settings.home_winter_cos),
            ConsumerCategory.HOUSEHOLD_WITH_CIE: (
                settings.electric_home_minimal_kw * scale,
                settings.electric_home_winter_cos,
            ),
            ConsumerCategory.LIGHTING: (NEGLIGIBLE_KW, settings.street_light_winter_cos),
            ConsumerCategory.OTHER: (NEGLIGIBLE_KW, settings.home_winter_cos),
        },
    }
    return table[season].get(category)


def _annual_scale(settings: CalculationSettings, category: ConsumerCategory, annual_kwh: float) -> float:
    if not settings.scale_by_annual:
        return 1.0
    reference = {
        ConsumerCategory.HOUSEHOLD_NO_CIE: settings.home_annual_kwh,
        ConsumerCategory.HOUSEHOLD_WITH_CIE: settings.electric_home_annual_kwh,
        ConsumerCategory.LIGHTING: settings.street_light_annual_kwh,
    }.get(category)
    return annual_kwh / reference if reference else 1.0


def _consumer_load(
    model: CircuitModel,
    settings: CalculationSettings,
    index: int,
    season: int,
    has_typical: bool,
    min_load: bool,
    targets: list[list[int]],
) -> tuple[float, float, float]:
    consumer = model.consumers[index]
    three_phase = consumer.phase_mode == PhaseMode.THREE_PHASE
    impedance = (OPEN_OHM, OPEN_OHM)
    extra_w = 0.0
    if consumer.load_type == ConsumerLoadType.TYPICAL:
        chosen = any(
            0 <= consumer.feeder_no < len(targets[phase]) and targets[phase][consumer.feeder_no] == index
            for phase in range(3)
        )
        extra_kw = settings.extra_load_kw if chosen and settings.extra_load_enabled else 0.0
        scale = _annual_scale(settings, consumer.category, consumer.annual_kwh)
        load = _standard_load(settings, consumer.category, season, scale, consumer.annual_kwh, extra_kw)
        if load is not None:
            impedance = _load_impedance(settings, three_phase, *load)
        if consumer.category == ConsumerCategory.HOUSEHOLD_NO_CIE and season != MINIMAL_SEASON:
            extra_w = extra_kw * 1000
    elif not (has_typical and min_load and season == MINIMAL_SEASON):
        impedance = _load_impedance(settings, three_phase, consumer.p_kw, consumer.cos_phi)
    resistance, reactance = impedance
    return resistance or OPEN_OHM, reactance or OPEN_OHM, extra_w


def _wire_resistances(line: Line, settings: CalculationSettings, air: float) -> tuple[float, float]:
    reference = BARE_REFERENCE_TEMP if line.insulation() == InsulationType.NONE else INSULATED_REFERENCE_TEMP
    heating = 1 + ALUMINIUM_TEMP_COEFF * (air + WIRE_HEATING_ALLOWANCE - reference)
    branch = line.line_type in (LineType.BRANCH_TO_LINE, LineType.BRANCH_TO_CONSUMER)
    contact = settings.contact_resistance_ohm if branch else 0.0
    return line.r_phase_ohm * heating + contact, line.r_neutral_ohm * heating + contact


def _admittances(
    model: CircuitModel,
    settings: CalculationSettings,
    layout: Layout,
    season: int,
    air: float,
    has_typical: bool,
    min_load: bool,
    targets: list[list[int]],
) -> tuple[np.ndarray, list[tuple[float, float]], float]:
    admittance = np.zeros((layout.branches,), dtype=complex)
    admittance[0:3] = 1 / complex(model.transformer.r_ohm or TINY, model.transformer.x_ohm or TINY)
    for index, line in enumerate(model.lines):
        phase_r, neutral_r = _wire_resistances(line, settings, air)
        start = layout.wire_offsets[index]
        if _is_single_drop(line):
            admittance[start : start + 2] = 1 / complex(phase_r or TINY, 0.0)
        else:
            admittance[start : start + 3] = 1 / complex(phase_r or TINY, 0.0)
            admittance[start + 3] = 1 / complex(neutral_r or TINY, 0.0)
    extra_w = 0.0
    impedances: list[tuple[float, float]] = []
    for index, consumer in enumerate(model.consumers):
        resistance, reactance, extra = _consumer_load(model, settings, index, season, has_typical, min_load, targets)
        extra_w += extra
        impedances.append((resistance, reactance))
        start = layout.load_offsets[index]
        width = 3 if consumer.phase_mode == PhaseMode.THREE_PHASE else 1
        admittance[start : start + width] = complex(1 / resistance, -1 / reactance)
    return admittance, impedances, extra_w


def _sources(model: CircuitModel, settings: CalculationSettings, layout: Layout) -> np.ndarray:
    emf = np.zeros((layout.branches,), dtype=complex)
    ratio = model.transformer.kt or DEFAULT_RATIO
    phase_emf = settings.high_voltage_kv * 1e3 / (ratio * math.sqrt(3))
    for phase, angle in enumerate((0.0, -120.0, 120.0)):
        emf[phase] = _phasor(phase_emf, angle)
    return emf


def _inlet_voltages(model: CircuitModel, potentials: np.ndarray, layout: Layout) -> tuple[np.ndarray, list[Phases]]:
    branch_voltages: list[complex] = []
    phases: list[Phases] = []
    for index, consumer in enumerate(model.consumers):
        node = layout.inlet_nodes[index]
        if consumer.phase_mode == PhaseMode.THREE_PHASE:
            neutral = potentials[node + 3]
            values = [potentials[node + phase] - neutral for phase in range(3)]
            branch_voltages.extend(values)
            phases.append(tuple(abs(value) for value in values))
        else:
            value = potentials[node] - potentials[node + 1]
            branch_voltages.append(value)
            magnitudes = [1000.0, 1000.0, 1000.0]
            magnitudes[consumer.phase_no - 1] = abs(value)
            phases.append(tuple(magnitudes))
    return np.asarray(branch_voltages, dtype=complex), phases


def _wire_currents(
    model: CircuitModel,
    potentials: np.ndarray,
    by_branch: dict[int, list[tuple[int, float]]],
    layout: Layout,
    settings: CalculationSettings,
    air: float,
) -> np.ndarray:
    currents: list[complex] = []
    for index, line in enumerate(model.lines):
        phase_r, neutral_r = _wire_resistances(line, settings, air)
        wires = 2 if _is_single_drop(line) else 4
        start = layout.wire_offsets[index]
        for wire in range(wires):
            leaving = 0j
            entering = 0j
            for node, sign in by_branch.get(start + wire, []):
                if sign == -1:
                    entering = potentials[node]
                elif sign == 1:
                    leaving = potentials[node]
            if wire == wires - 1:
                drop = leaving if line.line_type == LineType.OUTGOING else leaving - entering
                currents.append(drop / complex(neutral_r or TINY, 0.0))
            else:
                currents.append((leaving - entering) / complex(phase_r or TINY, 0.0))
    return np.asarray(currents, dtype=complex)


def _consumer_powers(
    model: CircuitModel, branch_voltages: np.ndarray, impedances: list[tuple[float, float]]
) -> tuple[list[float], list[float]]:
    active: list[float] = []
    reactive: list[float] = []
    position = 0
    for index, consumer in enumerate(model.consumers):
        width = 3 if consumer.phase_mode == PhaseMode.THREE_PHASE else 1
        resistance, reactance = impedances[index]
        p_total = 0.0
        q_total = 0.0
        for _ in range(width):
            magnitude = abs(branch_voltages[position])
            p_total += magnitude * magnitude / resistance
            q_total += magnitude * magnitude / reactance
            position += 1
        active.append(p_total)
        reactive.append(q_total)
    return active, reactive


def _wire_temperature(line: Line, current: float, air: float) -> float:
    section = (line.section_mm2() or 0.0) * 1e-6
    if section <= 0:
        section = DEFAULT_SECTION_M2
    cooling = COOLING_BY_CORES[min(max(line.cores(), 1), 4)]
    temp_coeff = ALUMINIUM_TEMP_COEFF if line.material() == WireMaterial.ALUMINUM else COPPER_TEMP_COEFF
    insulation = line.insulation()
    core_diameter = math.sqrt(4 * section / math.pi)
    if insulation == InsulationType.NONE:
        outer_diameter = core_diameter * BARE_DIAMETER_FACTOR
        insulation_resistance = 0.0
        reference = BARE_REFERENCE_TEMP
    else:
        outer_diameter = core_diameter + 2 * INSULATION_THICKNESS_M
        conductivity = XLPE_CONDUCTIVITY if insulation == InsulationType.XLPE else PVC_CONDUCTIVITY
        insulation_resistance = math.log(outer_diameter / core_diameter) / (
            cooling * 2 * math.pi * conductivity * line.length_m
        )
        reference = INSULATED_REFERENCE_TEMP
    surface = cooling * math.pi * outer_diameter * line.length_m
    core_temp = air
    heat_transfer = START_HEAT_TRANSFER
    for _ in range(THERMAL_ITERATIONS):
        heat = current * current * line.r_phase_ohm * (1 + temp_coeff * (core_temp - reference))
        surface_resistance = 1 / (heat_transfer * surface)
        core_temp = heat * (insulation_resistance + surface_resistance) + air
        surface_temp = core_temp if insulation == InsulationType.NONE else heat * surface_resistance + air
        rise = surface_temp - air
        if rise < MIN_SURFACE_RISE:
            heat_transfer = START_HEAT_TRANSFER
        else:
            radiation = (
                EMISSIVITY * STEFAN_BOLTZMANN * (power(surface_temp + KELVIN, 4) - power(air + KELVIN, 4)) / rise
            )
            convection = (
                CONVECTION_COEFF * math.sqrt(AIR_PRESSURE_PA / (air + KELVIN)) * power(rise / outer_diameter, 0.25)
            )
            heat_transfer = radiation + convection
    return core_temp


def _transformer_heating(
    model: CircuitModel, air: float, load_factor: list[float]
) -> tuple[list[float], list[float], float]:
    loss_ratio = model.transformer.pk_kw / max(model.transformer.px_kw, TINY)
    constant = DRY_TIME_CONSTANT_S if model.transformer.is_dry() else OIL_TIME_CONSTANT_S
    decay = math.exp(-STEP_S / constant)
    rise = 0.0
    oil = [0.0] * HALF_HOURS
    winding = [0.0] * HALF_HOURS
    for _ in range(2):
        for slot in range(HALF_HOURS):
            relative_losses = (1 + loss_ratio * power(load_factor[slot], 2)) / (1 + loss_ratio)
            steady = OIL_RISE_RATED * power(relative_losses, OIL_EXPONENT)
            rise = steady + (rise - steady) * decay
            oil[slot] = air + rise
            winding[slot] = oil[slot] + WINDING_GRADIENT_RATED * power(load_factor[slot], WINDING_EXPONENT)
    wear = sum(power(2.0, (value - WEAR_REFERENCE_TEMP) / WEAR_DOUBLING_STEP) for value in winding)
    return oil, winding, (24 / HALF_HOURS) * wear


def _hottest(temperatures: list[float]) -> int:
    best = 0
    for index, value in enumerate(temperatures):
        if value > temperatures[best] + TIE:
            best = index
    return best


def _lowest(model: CircuitModel, phase_voltages: list[Phases]) -> tuple[float, int, int]:
    voltage = 400.0
    consumer_index = 0
    phase_index = 0
    for index, consumer in enumerate(model.consumers):
        phases = range(3) if consumer.phase_mode == PhaseMode.THREE_PHASE else [consumer.phase_no - 1]
        for phase in phases:
            value = phase_voltages[index][phase]
            if value < voltage - TIE:
                voltage, consumer_index, phase_index = value, index, phase
    if model.consumers and model.consumers[consumer_index].phase_mode == PhaseMode.SINGLE_PHASE:
        phase_index = model.consumers[consumer_index].phase_no - 1
    return voltage, consumer_index, phase_index


def _load_shape(
    model: CircuitModel, settings: CalculationSettings, season: int, consumer_p: list[float], load_w: float
) -> list[float]:
    electric_w = sum(
        consumer_p[index]
        for index, consumer in enumerate(model.consumers)
        if consumer.category == ConsumerCategory.HOUSEHOLD_WITH_CIE
    )
    share = electric_w / load_w if load_w else 0.0
    if not 0 <= share <= 1:
        share = 0.0
    if season == 0:
        home, home_peak = settings.home_summer_curve, settings.home_summer_kw
        electric, electric_peak = settings.electric_home_summer_curve, settings.electric_home_summer_kw
    else:
        home, home_peak = settings.home_winter_curve, settings.home_winter_kw
        electric, electric_peak = settings.electric_home_winter_curve, settings.electric_home_winter_kw
    return [(1 - share) * home[slot] / home_peak + share * electric[slot] / electric_peak for slot in range(HALF_HOURS)]


def _season(
    model: CircuitModel,
    settings: CalculationSettings,
    season: int,
    potentials: np.ndarray,
    branch_voltages: np.ndarray,
    phase_voltages: list[Phases],
    wire_currents: np.ndarray,
    consumer_p: list[float],
    consumer_q: list[float],
    impedances: list[tuple[float, float]],
    extra_w: float,
    air: float,
    transformer_air: float,
    layout: Layout,
) -> SeasonResult:
    temperatures = [
        _wire_temperature(line, abs(wire_currents[layout.wire_offsets[index] - 3]), air)
        for index, line in enumerate(model.lines)
    ]
    hottest = _hottest(temperatures)
    feeder_currents: list[complex] = []
    for index, line in enumerate(model.lines):
        if line.line_type == LineType.OUTGOING:
            start = layout.wire_offsets[index] - 3
            feeder_currents.extend(wire_currents[start : start + 4].tolist())
    bus = (potentials[0], potentials[1], potentials[2])
    lowest_voltage, lowest_consumer, lowest_phase = _lowest(model, phase_voltages)
    reference = abs(bus[lowest_phase]) or TINY
    voltage_loss = (reference - lowest_voltage) * 100 / reference if model.consumers else 0.0
    phase_p = [0.0, 0.0, 0.0]
    phase_q = [0.0, 0.0, 0.0]
    total = 0j
    feeders = model.outgoing_count
    for feeder in range(feeders):
        for phase in range(3):
            position = 4 * feeder + phase
            if position >= len(feeder_currents):
                break
            flow = bus[phase] * np.conjugate(feeder_currents[position])
            phase_p[phase] += flow.real
            phase_q[phase] += flow.imag
            total += flow
    bus_p = total.real or NEGLIGIBLE_KW
    bus_q = total.imag or NEGLIGIBLE_KW
    line_loss_kw = (bus_p - sum(consumer_p)) / 1000.0
    line_loss_percent = line_loss_kw * 100 / (bus_p / 1000.0) if bus_p > QUIET_POWER_W else 0.0
    load_w = bus_p - extra_w
    shape = _load_shape(model, settings, season, consumer_p, load_w)
    peak = max(shape) or TINY
    load_va = math.sqrt(load_w**2 + bus_q**2)
    curve = [load_va * value / peak for value in shape]
    load_factor = [value / max(model.transformer.sn_kva * 1000.0, TINY) for value in curve]
    oil, winding, wear = _transformer_heating(model, transformer_air, load_factor)
    if bus_p > QUIET_POWER_W:
        shares = tuple(max(phase_p[phase] * 100 / bus_p, 0.0) for phase in range(3))
    else:
        shares = (0.0, 0.0, 0.0)
    return SeasonResult(
        potentials=potentials,
        branch_voltages=branch_voltages,
        wire_currents=wire_currents,
        phase_voltages=phase_voltages,
        consumer_p=consumer_p,
        consumer_q=consumer_q,
        wire_temperatures=temperatures,
        oil_peak=max(oil),
        winding_peak=max(winding),
        voltage_loss_percent=voltage_loss,
        lowest_voltage=lowest_voltage if model.consumers else 220.0,
        lowest_consumer=lowest_consumer,
        hottest_temperature=temperatures[hottest] if temperatures else 0.0,
        hottest_line=hottest,
        bus_p=bus_p,
        bus_q=bus_q,
        phase_p=tuple(phase_p),
        phase_q=tuple(phase_q),
        extra_load_w=extra_w,
        load_va=load_va,
        load_curve_va=curve,
        load_factor=load_factor,
        wear_hours=wear,
        winding_temps=winding,
        oil_temps=oil,
        bus_voltages=bus,
        feeder_currents=feeder_currents,
        line_loss_kw=line_loss_kw,
        line_loss_percent=line_loss_percent,
        phase_shares=shares,
        load_impedances=impedances,
    )


def _air(settings: CalculationSettings, season: int) -> tuple[float, float]:
    if season == 0:
        return settings.line_air_summer, settings.transformer_air_summer
    return settings.line_air_winter, settings.transformer_air_winter


def calculate(
    model: CircuitModel, settings: CalculationSettings, period: int = 2, min_load: bool = True
) -> CalculationResults:
    has_typical = any(c.load_type == ConsumerLoadType.TYPICAL for c in model.consumers)
    layout = Layout(model)
    targets = [extra_load_targets(model, phase + 1) for phase in range(3)]
    by_branch = _connect(model, layout).by_branch()
    emf = _sources(model, settings, layout)
    results = CalculationResults(
        has_typical=has_typical,
        min_load_requested=min_load,
        extra_load_targets=targets,
        wire_offsets=[offset - 3 for offset in layout.wire_offsets],
    )
    for season in seasons_for(period):
        air, transformer_air = _air(settings, season)
        admittance, impedances, extra_w = _admittances(
            model, settings, layout, season, air, has_typical, min_load, targets
        )
        potentials = _solve(by_branch, admittance, emf, layout.nodes)
        branch_voltages, phase_voltages = _inlet_voltages(model, potentials, layout)
        wire_currents = _wire_currents(model, potentials, by_branch, layout, settings, air)
        consumer_p, consumer_q = _consumer_powers(model, branch_voltages, impedances)
        results.seasons[season] = _season(
            model,
            settings,
            season,
            potentials,
            branch_voltages,
            phase_voltages,
            wire_currents,
            consumer_p,
            consumer_q,
            impedances,
            extra_w,
            air,
            transformer_air,
            layout,
        )
        results.season_order.append(season)
    if has_typical and min_load and model.consumers:
        admittance, _, _ = _admittances(
            model, settings, layout, MINIMAL_SEASON, settings.transformer_air_summer, has_typical, min_load, targets
        )
        potentials = _solve(by_branch, admittance, emf, layout.nodes)
        _, results.min_load_voltages = _inlet_voltages(model, potentials, layout)
        peak = 0.0
        peak_consumer = 0
        for index, phases in enumerate(results.min_load_voltages):
            consumer = model.consumers[index]
            value = max(phases) if consumer.phase_mode == PhaseMode.THREE_PHASE else phases[consumer.phase_no - 1]
            if value > peak + TIE:
                peak, peak_consumer = value, index
        results.min_load_peak = peak
        results.min_load_peak_consumer = peak_consumer
    return results

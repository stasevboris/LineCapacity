from __future__ import annotations

from datetime import datetime

from linecapacity.settings import CalculationSettings
from linecapacity.solver import calculate

from ..exchange.docx import COLORS, package, paragraph, table
from ..scheme.model import Scheme
from .bridge import to_model
from .compare import gost_quality
from .losses import annual_losses
from .results import check_scheme, run
from .settings import FIELDS
from .text import fixed

SEASONS = {"0": "лето", "1": "зима"}
LOADS = {0: "типовая", 1: "индивидуальная"}
PHASES = {0: "3 фазы"}


def number(value, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def source_part(scheme: Scheme, changed: dict) -> list[str]:
    t = scheme.transformer
    parts = [paragraph("1. Исходные данные", "Heading1"), table(
        ["Трансформатор", "Sн, кВА", "Uвн, кВ", "Uнн, кВ", "Pхх, кВт", "Pкз, кВт", "Uк, %", "Ступень ПБВ"],
        [[t.type_name, number(t.sn_kva, 0), number(t.uvn_kv, 1), number(t.unn_kv, 2), number(t.px_kw, 2),
          number(t.pk_kw, 2), number(t.uk_percent, 1), str(t.pbv_step)]],
        [2000, 1000, 1000, 1000, 1100, 1100, 900, 1300])]
    parts.append(paragraph(f"Отходящих линий: {scheme.outgoing_count}; ЛЭП: {len(scheme.lines)}; "
                           f"опор: {len(scheme.poles)}; потребителей: {len(scheme.consumers)}."))
    labels = {item.key: item for item in FIELDS}
    if changed:
        parts.append(paragraph("Настройки расчёта, отличные от справочника типовых нагрузок:"))
        rows = []
        for key, value in changed.items():
            item = labels.get(key)
            if item is None:
                continue
            shown = ("да" if value else "нет") if isinstance(value, bool) else number(value, 3).rstrip("0").rstrip(",")
            rows.append([item.label, f"{shown} {item.unit}".strip()])
        parts.append(table(["Величина", "Значение"], rows, [6400, 2700]))
    else:
        parts.append(paragraph("Настройки расчёта — по справочнику типовых нагрузок."))
    return parts


def consumers_part(scheme: Scheme, result: dict, quality: dict) -> list[str]:
    rows = []
    numbers = sorted(result["seasons"])
    for index, consumer in enumerate(scheme.consumers):
        phase = PHASES.get(consumer.phase_mode, f"фаза {consumer.phase_no}")
        voltages = []
        for season in numbers:
            values = result["seasons"][season]["consumer_voltages"][index]
            voltages.append(" / ".join(number(value) for value in values))
        check = quality["consumers"][index]
        verdict = "в норме" if check["ok"] else "вне нормы"
        rows.append([str(index + 1), consumer.address or consumer.label, phase, LOADS.get(consumer.load_type, ""),
                     *voltages, f"{number(check['low_percent'])} … +{number(check['high_percent'])} %, {verdict}"])
    head = ["№", "Адрес", "Фазность", "Нагрузка", *[f"U {SEASONS[season]}, В" for season in numbers],
            "Отклонение по ГОСТ 32144"]
    widths = [500, 2400, 1000, 1300] + [1500] * len(numbers) + [2000]
    return [paragraph("3. Напряжение у потребителей", "Heading1"),
            paragraph(f"Номинальное напряжение {number(quality['nominal'], 0)} В, допустимое установившееся "
                      "отклонение — ±10 % (ГОСТ 32144-2013)."), table(head, rows, widths)]


def lines_part(scheme: Scheme, result: dict) -> list[str]:
    numbers = sorted(result["seasons"])
    rows = []
    for index, line in enumerate(scheme.lines):
        temperatures = [number(result["seasons"][season]["line_temperatures"][index]) for season in numbers]
        rows.append([line.label, line.type_name, number(line.length_m, 1), *temperatures])
    head = ["ЛЭП", "Марка", "Длина, м", *[f"T {SEASONS[season]}, °C" for season in numbers]]
    return [paragraph("4. ЛЭП", "Heading1"), table(head, rows, [1400, 3200, 1200] + [1500] * len(numbers))]


def transformer_part(result: dict) -> list[str]:
    rows = []
    for season in sorted(result["seasons"]):
        data = result["seasons"][season]["transformer"]
        rows.append([SEASONS[season], number(data["load_kva"], 2), number(data["load_factor"], 2),
                     number(data["oil"]), number(data["winding"]), number(data["wear_hours"], 2), data["state"]])
    return [paragraph("5. Трансформатор", "Heading1"),
            table(["Сезон", "Нагрузка, кВА", "Загрузка", "Масло, °C", "Обмотки, °C", "Износ, ч", "Состояние"], rows,
                  [900, 1300, 1000, 1000, 1100, 1000, 3200])]


def losses_part(losses: dict) -> list[str]:
    rows = [["Время использования наибольшей нагрузки Tmax, ч", number(losses["use_hours"], 0)],
            ["Время наибольших потерь τ, ч", number(losses["loss_hours"], 0)],
            ["Потери в ЛЭП, кВт·ч", number(losses["lines_kwh"], 0)],
            ["Потери холостого хода трансформатора, кВт·ч", number(losses["transformer_idle_kwh"], 0)],
            ["Нагрузочные потери трансформатора, кВт·ч", number(losses["transformer_load_kwh"], 0)],
            ["Потери энергии за год, кВт·ч", number(losses["total_kwh"], 0)],
            ["Стоимость электроэнергии, $/кВт·ч", number(losses["price_usd"], 3)],
            ["Стоимость потерь за год, $", number(losses["cost_usd"], 2)]]
    return [paragraph("6. Годовые потери энергии", "Heading1"), table(["Величина", "Значение"], rows, [6400, 2700])]


def calculation_report(scheme: Scheme, name: str, author: str, settings: CalculationSettings, changed: dict,
                       period: int, min_load: bool, price_usd: float | None) -> bytes:
    check_scheme(scheme)
    result = run(scheme, period, min_load, settings)
    model = to_model(scheme)
    results = calculate(model, settings, period, min_load)
    quality = gost_quality(model, results, settings)
    parts = [paragraph("Отчёт о расчёте режима сети 0,4 кВ", "Title"),
             paragraph(f"Схема: {name}"), paragraph(f"Дата: {datetime.now():%d.%m.%Y}"),
             paragraph(f"Подготовил: {author}"), *source_part(scheme, changed),
             paragraph("2. Основные результаты расчётов", "Heading1")]
    for row in result["report"]:
        parts.append(paragraph(row["text"], bold=row["tone"] in ("title", "alert", "good"),
                               color=COLORS.get(row["tone"])))
    parts += consumers_part(scheme, result, quality) + lines_part(scheme, result) + transformer_part(result)
    if price_usd is not None:
        parts += losses_part(annual_losses(model, calculate(model, settings, 2, False), price_usd))
    worst = min(result["seasons"].values(), key=lambda data: data["min_voltage"])
    parts += [paragraph("Заключение", "Heading1"),
              paragraph("Пропускная способность сети " + ("достаточна." if result["good"] else "недостаточна."),
                        bold=True),
              paragraph(f"Наименьшее напряжение у потребителя — {fixed(worst['min_voltage'], 4, 1)} В; напряжение "
                        + ("у всех потребителей в пределах ±10 % номинального." if quality["ok"] else
                           f"вне пределов ±10 % у {quality['outside']} из {quality['total']} потребителей."))]
    return package(parts, f"Отчёт о расчёте: {name}", author)

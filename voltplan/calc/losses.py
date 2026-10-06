from __future__ import annotations

from linecapacity.model import CircuitModel
from linecapacity.solver import CalculationResults

from ..scheme.editor import EditError

HOURS_PER_YEAR = 8760.0
FALLBACK_USE_HOURS = 3000.0
DEFAULT_PRICE_USD = 0.08


def loss_hours(use_hours: float) -> float:
    return (0.124 + use_hours / 1e4) ** 2 * HOURS_PER_YEAR


def annual_losses(model: CircuitModel, results: CalculationResults, price_usd: float) -> dict:
    seasons = [results.seasons[number] for number in results.season_order]
    peak_kw = max(((season.bus_p - season.extra_load_w) / 1000.0 for season in seasons), default=0.0)
    if peak_kw <= 0:
        raise EditError("Годовые потери не рассчитываются: наибольшая нагрузка сети получилась не больше нуля. "
                        "Проверьте настройки расчёта, например линейное напряжение на стороне ВН.")
    consumed_kwh = sum(max(consumer.annual_kwh, 0.0) for consumer in model.consumers)
    if consumed_kwh > 0 and peak_kw > 0:
        use_hours = min(HOURS_PER_YEAR, consumed_kwh / peak_kw)
    else:
        use_hours = FALLBACK_USE_HOURS
    hours = loss_hours(use_hours)
    line_peak_kw = max((max(season.line_loss_kw, 0.0) for season in seasons), default=0.0)
    load_factor = max((max(season.load_factor) for season in seasons), default=0.0)
    transformer = model.transformer
    lines_kwh = line_peak_kw * hours
    idle_kwh = transformer.px_kw * HOURS_PER_YEAR
    load_kwh = transformer.pk_kw * load_factor ** 2 * hours
    total_kwh = lines_kwh + idle_kwh + load_kwh
    return {
        "peak_kw": peak_kw,
        "consumed_kwh": consumed_kwh,
        "use_hours": use_hours,
        "loss_hours": hours,
        "lines_kwh": lines_kwh,
        "transformer_idle_kwh": idle_kwh,
        "transformer_load_kwh": load_kwh,
        "total_kwh": total_kwh,
        "share_percent": total_kwh * 100.0 / consumed_kwh if consumed_kwh > 0 else None,
        "price_usd": price_usd,
        "cost_usd": total_kwh * price_usd,
    }

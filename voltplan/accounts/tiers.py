from __future__ import annotations

import time
from dataclasses import dataclass, field

from .security import Refused
from .users import User


@dataclass(frozen=True)
class Tier:
    code: str
    title: str
    price_usd: float
    projects: int
    variants: int
    compared: int
    scenarios: int
    poles: int
    consumers: int
    features: frozenset[str] = field(default_factory=frozenset)


FEATURE_NAMES = {
    "own_marks": "Свои марки ЛЭП и трансформаторов",
    "docx": "Отчёт в формате DOCX",
    "epure": "Эпюра напряжения вдоль линии",
    "annual_losses": "Годовые потери энергии и их стоимость",
    "teams": "Создание команд",
}
TIERS = {
    "demo": Tier("demo", "Демо", 0.0, 2, 2, 2, 2, 40, 40),
    "pro": Tier("pro", "Профессионал", 19.0, 50, 10, 4, 10, 299, 598, frozenset({"own_marks", "docx"})),
    "max": Tier("max", "Максимум", 39.0, 1000, 30, 8, 20, 299, 598,
                frozenset({"own_marks", "docx", "epure", "annual_losses", "teams"})),
}
ORDER = ("demo", "pro", "max")
PERIOD_DAYS = 30


def effective(user: User, now: float | None = None) -> Tier:
    moment = time.time() if now is None else now
    if user.tier in TIERS and user.tier != "demo" and (user.tier_until is None or user.tier_until > moment):
        return TIERS[user.tier]
    return TIERS["demo"]


def lowest_with(feature: str) -> Tier:
    return next(TIERS[code] for code in ORDER if feature in TIERS[code].features)


def require(user: User, feature: str) -> None:
    if feature not in effective(user).features:
        needed = lowest_with(feature)
        raise Refused(f"«{FEATURE_NAMES[feature]}» — в тарифе «{needed.title}» и выше. Сменить тариф можно в "
                      "личном кабинете, раздел «Тариф».", 403)


def check_size(user: User, poles: int, consumers: int) -> None:
    tier = effective(user)
    if poles > tier.poles or consumers > tier.consumers:
        raise Refused(f"В тарифе «{tier.title}» схема может содержать не больше {tier.poles} опор и "
                      f"{tier.consumers} потребителей. В этой схеме опор: {poles}, потребителей: {consumers}.", 403)


def describe(tier: Tier) -> dict:
    return {"code": tier.code, "title": tier.title, "price_usd": tier.price_usd, "projects": tier.projects,
            "variants": tier.variants, "compared": tier.compared, "scenarios": tier.scenarios, "poles": tier.poles,
            "consumers": tier.consumers, "features": sorted(tier.features)}

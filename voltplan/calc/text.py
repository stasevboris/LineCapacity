from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

EXTENDED_DIGITS = 18
SMALLEST_PLAIN = -5


def decimal_of(value: float) -> Decimal:
    number = Decimal(float(value))
    if number.is_zero():
        return Decimal(0)
    step = Decimal(1).scaleb(number.adjusted() - EXTENDED_DIGITS + 1)
    return number.quantize(step, rounding=ROUND_HALF_EVEN)


def special(value: float) -> str | None:
    number = float(value)
    if math.isnan(number):
        return "NAN"
    if math.isinf(number):
        return "INF" if number > 0 else "-INF"
    return None


def significant(number: Decimal, precision: int) -> Decimal:
    return number.quantize(Decimal(1).scaleb(number.adjusted() - precision + 1), rounding=ROUND_HALF_UP)


def scientific(number: Decimal, precision: int) -> str:
    rounded = significant(number, precision)
    exponent = rounded.adjusted()
    mantissa = f"{rounded.scaleb(-exponent).normalize():f}"
    return f"{mantissa}E{exponent}".replace(".", ",")


def fixed(value: float, precision: int, digits: int) -> str:
    text = special(value)
    if text:
        return text
    number = decimal_of(value)
    if not number.is_zero():
        if significant(number, precision).adjusted() + 1 > precision:
            return scientific(number, precision)
        step = max(number.adjusted() - precision + 1, -digits)
        number = number.quantize(Decimal(1).scaleb(step), rounding=ROUND_HALF_UP)
    if number.is_zero():
        number = Decimal(0)
    return f"{number:.{digits}f}".replace(".", ",")


def general(value: float, precision: int) -> str:
    text = special(value)
    if text:
        return text
    number = decimal_of(value)
    if number.is_zero():
        return "0"
    rounded = significant(number, precision)
    if rounded.adjusted() + 1 > precision or rounded.adjusted() < SMALLEST_PLAIN + 1:
        return scientific(number, precision)
    text = f"{rounded.normalize():f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")

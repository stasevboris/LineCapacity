from __future__ import annotations

from linecapacity.model import (
    CircuitModel,
    ConnectionPoint,
    Consumer,
    ConsumerCategory,
    ConsumerLoadType,
    Line,
    LineType,
    PhaseMode,
    Pole,
    Transformer,
)

from ..scheme.model import Scheme


def category(value: float) -> ConsumerCategory | float:
    number = float(value)
    if number.is_integer() and 0 <= number <= 3:
        return ConsumerCategory(int(number))
    return number


def to_model(scheme: Scheme) -> CircuitModel:
    t = scheme.transformer
    model = CircuitModel(transformer=Transformer(**t.model_dump()), outgoing_count=scheme.outgoing_count)
    for line in scheme.lines:
        data = line.model_dump()
        data["line_type"] = LineType(line.line_type)
        data["phase_mode"] = PhaseMode(line.phase_mode)
        model.lines.append(Line(**data))
    for pole in scheme.poles:
        model.poles.append(Pole(**pole.model_dump()))
    for consumer in scheme.consumers:
        data = consumer.model_dump()
        data["phase_mode"] = PhaseMode(consumer.phase_mode)
        data["load_type"] = ConsumerLoadType(consumer.load_type)
        data["category"] = category(consumer.category)
        model.consumers.append(Consumer(**data))
    for point in scheme.connection_points:
        model.connection_points.append(ConnectionPoint(**point.model_dump()))
    return model

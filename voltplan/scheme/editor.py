from __future__ import annotations

import math

from pydantic import ValidationError

from ..errors import describe
from .actions import Action, ConsumerInput, LineInput, PoleInput, TransformerInput
from .model import (
    MAX_BRANCHES,
    MAX_CONSUMERS,
    MAX_LINES,
    MAX_OUTGOING,
    MAX_POINTS,
    MAX_POLES,
    ConnectionPoint,
    Consumer,
    Line,
    Pole,
    Scheme,
    Transformer,
)

WIRE_LENGTH = 40
BRANCH_STEP = 30
ROW_STEP = 30
TEXT_HEIGHT = 14
CONSUMER_SIZE = 10
FIELD_WIDTH = 100000

OUTGOING = 1
POLE = 2
SPAN = 3
BRANCH_LINE = 4
BRANCH_CONSUMER = 6

LINE_TYPE_BY_POINT_KIND = {OUTGOING: 0, SPAN: 1, BRANCH_LINE: 2, BRANCH_CONSUMER: 3}

TYPICAL_CIE_KWH = 8507.0

ACTION_TITLES = {
    "outgoing": "Отходящая от ТП ЛЭП",
    "span": "Пролёт между опорами",
    "branch_line": "Ответвление к другой линии",
    "branch_consumer": "Ответвление к потребителю",
    "pole": "Промежуточная опора",
    "consumer": "Потребитель",
}


class EditError(ValueError):
    pass


def transformer_equivalent(t: Transformer) -> None:
    t.r_ohm = t.pk_kw * 1e3 * math.pow(t.unn_kv * 1e3, 2) / math.pow(t.sn_kva * 1e3, 2)
    z = t.uk_percent * math.pow(t.unn_kv * 1e3, 2) / (100.0 * t.sn_kva * 1e3)
    t.x_ohm = math.sqrt(max(z * z - t.r_ohm * t.r_ohm, 0.0))
    t.kt = (t.uvn_kv / t.unn_kv) * (1 + t.pbv_step * t.pbv_percent / 100.0)


def apply_transformer(t: Transformer, data: TransformerInput) -> None:
    t.type_name = data.type_name
    t.label = data.label
    t.sn_kva = data.sn_kva
    t.px_kw = data.px_kw
    t.pk_kw = data.pk_kw
    t.unn_kv = data.unn_kv
    t.uvn_kv = data.uvn_kv
    t.uk_percent = data.uk_percent
    t.pbv_steps = data.pbv_steps
    t.pbv_step = data.pbv_step
    t.pbv_percent = data.pbv_percent
    transformer_equivalent(t)


def apply_line(line: Line, data: LineInput) -> None:
    line.type_name = data.type_name
    line.label = data.label
    line.phase_mode = data.phase_mode
    line.length_m = data.length_m
    if data.phase_mode == 0:
        line.r_phase_ohm_per_km = data.r_phase_ohm_per_km
        line.r_neutral_ohm_per_km = data.r_neutral_ohm_per_km
        line.r_phase_ohm = line.r_phase_ohm_per_km * line.length_m / 1e3
        line.r_neutral_ohm = line.r_neutral_ohm_per_km * line.length_m / 1e3
    else:
        line.r_single_phase_ohm_per_km = data.r_single_phase_ohm_per_km
        line.phase_no = data.phase_no
        line.r_phase_ohm = line.r_single_phase_ohm_per_km * line.length_m / 1e3
        line.r_neutral_ohm = line.r_phase_ohm


def default_type_text(phase_mode: int) -> str:
    return "мощность по ТУ: 3,5 кВт" if phase_mode == 1 else "мощность по ТУ: 12 кВт"


def apply_consumer(consumer: Consumer, data: ConsumerInput) -> None:
    consumer.type_text = data.type_text if data.type_text is not None else default_type_text(consumer.phase_mode)
    consumer.label = data.label
    consumer.address = data.address
    consumer.load_type = data.load_type
    consumer.p_kw = data.p_kw if data.p_kw != 0 else 1e-15
    consumer.cos_phi = data.cos_phi
    consumer.annual_kwh = data.annual_kwh
    if data.category is None:
        household_with_cie = consumer.phase_mode == 0 or consumer.annual_kwh >= TYPICAL_CIE_KWH
        consumer.category = 1.0 if household_with_cie else 0.0
    else:
        consumer.category = float(data.category)


def known_category(value: float) -> bool:
    return float(value) in (0.0, 1.0, 2.0, 3.0)


FRESH = {"lines": Line, "poles": Pole, "consumers": Consumer}


def slot(scheme: Scheme | None, name: str):
    spare = getattr(scheme.spare, name) if scheme else []
    return spare[0].model_copy(deep=True) if spare else FRESH[name]()


def restore(current: Scheme, block: Scheme) -> Scheme:
    restored = block.model_copy(deep=True)
    for name in FRESH:
        memory = getattr(current, name) + getattr(current.spare, name)
        kept = len(getattr(block, name))
        setattr(restored.spare, name, [item.model_copy(deep=True) for item in memory[kept:]])
    return restored


class Editor:
    def __init__(self, scheme: Scheme, field_width: int = FIELD_WIDTH) -> None:
        self.s = scheme.model_copy(deep=True)
        self.field_width = field_width
        self.current: tuple[int, int] | None = None
        self.snapshots: list[Scheme] = []

    def record(self) -> None:
        self.snapshots.append(self.s.model_copy(deep=True))

    def take(self, name: str):
        spare = getattr(self.s.spare, name)
        return spare.pop(0) if spare else FRESH[name]()

    def release(self, name: str, index: int) -> None:
        items = getattr(self.s, name)
        last = items[-1].model_copy(deep=True)
        del items[index]
        getattr(self.s.spare, name).insert(0, last)

    def point_index(self, x: int, y: int) -> int | None:
        for index, point in enumerate(self.s.connection_points):
            if point.x == x and point.y == y:
                return index
        return None

    def point_feeder(self, x: int, y: int) -> int:
        index = self.point_index(x, y)
        return self.s.connection_points[index].feeder_no if index is not None else 0

    def activate(self, x: int, y: int, point_kind: int, branch_no: int, feeder: int) -> None:
        if len(self.s.connection_points) >= MAX_POINTS:
            raise EditError("Достигнуто максимально допустимое количество присоединений на схеме!")
        self.s.connection_points.append(ConnectionPoint(
            x=x, y=y, active=True, point_kind=point_kind, object_no=0,
            branch_no=branch_no, feeder_no=feeder))

    def deactivate(self, x: int, y: int) -> None:
        index = self.point_index(x, y)
        if index is not None:
            self.s.connection_points[index].active = False

    def delete_point(self, x: int, y: int) -> None:
        index = self.point_index(x, y)
        if index is not None:
            del self.s.connection_points[index]

    def pole_at(self, x: int, y: int) -> int:
        for index, pole in enumerate(self.s.poles):
            if (pole.x == x and pole.y == y) or (pole.end_x == x and pole.end_y == y):
                return index
            for branch in range(pole.branch_count):
                if pole.x + (branch + 1) * BRANCH_STEP == x and pole.y == y:
                    return index
        return 0

    def lowest_end_right_of(self, x: int, feeder: int) -> int:
        result = 0
        for line in self.s.lines:
            if line.end_y > result and line.end_x >= x and line.feeder_no == feeder:
                result = line.end_y
        return result

    def lowest_end_under_pole(self, pole_index: int) -> int:
        pole = self.s.poles[pole_index]
        result = 0
        for branch in range(pole.branch_count):
            x = pole.x + (branch + 1) * BRANCH_STEP
            for line in self.s.lines:
                if line.x == x and line.y == pole.y:
                    result = max(result, line.end_y)
                    break
        searching = True
        guard = 0
        while searching and guard <= len(self.s.lines):
            guard += 1
            for line in self.s.lines:
                if line.y == result:
                    result = line.end_y
                    break
                searching = False
        return result

    def push_feeder_down(self, shift: int, feeder: int) -> None:
        for line in self.s.lines:
            if line.feeder_no > feeder:
                line.y += shift
                line.end_y += shift
        for pole in self.s.poles:
            if pole.feeder_no > feeder:
                pole.y += shift
                pole.end_y += shift
        for consumer in self.s.consumers:
            if consumer.feeder_no > feeder:
                consumer.y += shift
        for point in self.s.connection_points:
            if point.feeder_no > feeder:
                point.y += shift

    def push_lower_feeders(self, y: int, feeder: int) -> None:
        if feeder >= self.s.outgoing_count:
            return
        crossing = False
        shift = 0
        for line in self.s.lines:
            if y >= line.y and line.feeder_no > feeder:
                crossing = True
                shift = max(shift, y - line.y)
        if crossing:
            for number in range(feeder, self.s.outgoing_count):
                self.push_feeder_down(shift + CONSUMER_SIZE + TEXT_HEIGHT, number)

    def push_right(self, x: int, y: int, right_edge: int, bottom_edge: int, shift: int, keep_pole: int) -> None:
        for line in self.s.lines:
            if line.x > x and line.end_x < right_edge and line.y >= y and line.end_y < bottom_edge:
                line.x += shift
                line.end_x += shift
        for index, pole in enumerate(self.s.poles):
            inside = pole.x > x and pole.end_x < right_edge and pole.y >= y and pole.end_y < bottom_edge
            if inside and index != keep_pole:
                pole.x += shift
                pole.end_x += shift
        for consumer in self.s.consumers:
            if x < consumer.x < right_edge and y <= consumer.y < bottom_edge:
                consumer.x += shift
        for point in self.s.connection_points:
            if x < point.x < right_edge and y <= point.y < bottom_edge:
                point.x += shift

    def attach_line(self, point_kind: int, x: int, y: int, data: LineInput,
                    pole_index: int | None = None, to_single: bool = False) -> tuple[int, int]:
        if len(self.s.lines) >= MAX_LINES:
            raise EditError("Достигнуто максимальное количество линий!")
        line = self.take("lines")
        apply_line(line, data)
        feeder = self.s.outgoing_count if point_kind == OUTGOING else self.point_feeder(x, y)
        line.feeder_no = feeder
        line.line_type = LINE_TYPE_BY_POINT_KIND[point_kind]
        if point_kind in (BRANCH_LINE, BRANCH_CONSUMER):
            pole = self.s.poles[pole_index]
            offset = (pole.branch_count - pole.current_branch_no) * ROW_STEP
            if point_kind == BRANCH_CONSUMER:
                length = WIRE_LENGTH + offset
            else:
                lowest = self.lowest_end_right_of(x, feeder)
                if lowest <= y:
                    length = WIRE_LENGTH + offset + 2 * TEXT_HEIGHT
                else:
                    if to_single:
                        lowest = self.lowest_end_under_pole(pole_index)
                        if lowest == 0:
                            lowest = y
                    length = lowest - y + WIRE_LENGTH + CONSUMER_SIZE + 2 * TEXT_HEIGHT + 2
            line.vertical = 1
        else:
            length = 2 * WIRE_LENGTH if point_kind == OUTGOING else WIRE_LENGTH
            line.vertical = 0
        if point_kind != OUTGOING:
            self.deactivate(x, y)
        line.canvas_length = length
        line.x, line.y = x, y
        if line.vertical == 0:
            line.end_x, line.end_y = x + length, y
        else:
            line.end_x, line.end_y = x, y + length
            self.push_lower_feeders(line.end_y + CONSUMER_SIZE + TEXT_HEIGHT, feeder)
        self.s.lines.append(line)
        self.activate(line.end_x, line.end_y, point_kind, 0, feeder)
        if point_kind == OUTGOING:
            self.s.outgoing_count += 1
        self.current = (line.end_x, line.end_y)
        self.record()
        return line.end_x, line.end_y

    def attach_pole(self, x: int, y: int, data: PoleInput) -> tuple[int, int]:
        if len(self.s.poles) >= MAX_POLES:
            raise EditError("Достигнуто максимальное количество опор!")
        feeder = self.point_feeder(x, y)
        self.deactivate(x, y)
        length = BRANCH_STEP + BRANCH_STEP * data.branch_count
        pole = self.take("poles")
        pole.label, pole.branch_count, pole.feeder_no = data.label, data.branch_count, feeder
        pole.x, pole.y, pole.end_x, pole.end_y, pole.canvas_length = x, y, x + length, y, length
        for branch in range(data.branch_count):
            self.activate(x + (branch + 1) * BRANCH_STEP, y, POLE, branch + 1, feeder)
        self.s.poles.append(pole)
        self.activate(pole.end_x, pole.end_y, POLE, 0, feeder)
        self.current = (pole.end_x, pole.end_y)
        self.record()
        return pole.end_x, pole.end_y

    def attach_consumer(self, x: int, y: int, data: ConsumerInput) -> None:
        if len(self.s.consumers) >= MAX_CONSUMERS:
            raise EditError("Достигнуто максимальное количество потребителей!")
        feeder = self.point_feeder(x, y)
        self.deactivate(x, y)
        consumer = self.take("consumers")
        consumer.x, consumer.y, consumer.feeder_no = x, y, feeder
        for line in self.s.lines:
            if line.end_x == x and line.end_y == y:
                consumer.phase_mode = line.phase_mode
                consumer.phase_no = line.phase_no
                break
        apply_consumer(consumer, data)
        self.s.consumers.append(consumer)
        self.current = (x, y)
        self.record()

    def point_kind_at(self, x: int, y: int) -> int:
        index = self.point_index(x, y)
        if index is None or not self.s.connection_points[index].active:
            return 0
        return self.s.connection_points[index].point_kind

    def click_point(self, x: int, y: int) -> None:
        index = self.point_index(x, y)
        if index is None:
            return
        point = self.s.connection_points[index]
        if point.active and point.point_kind == POLE and self.s.poles:
            self.s.poles[self.pole_at(x, y)].current_branch_no = point.branch_no

    def menu(self, x: int, y: int) -> list[str]:
        actions = ["outgoing"]
        point_kind = self.point_kind_at(x, y)
        if point_kind in (OUTGOING, SPAN, BRANCH_LINE):
            actions.append("pole")
        elif point_kind == POLE:
            point = self.s.connection_points[self.point_index(x, y)]
            pole = self.s.poles[self.pole_at(x, y)] if self.s.poles else None
            if pole is not None and pole.branch_count > 0 and point.branch_no > 0:
                actions += ["branch_line", "branch_consumer"]
            else:
                actions.append("span")
        elif point_kind == BRANCH_CONSUMER:
            actions.append("consumer")
        return actions

    def require(self, action: Action, kind: str) -> tuple[int, int]:
        if action.point is None:
            raise EditError("Не выбрана точка присоединения")
        x, y = action.point.x, action.point.y
        if kind not in self.menu(x, y):
            raise EditError(f"Действие «{ACTION_TITLES[kind]}» недоступно в выбранной точке")
        return x, y

    def select_pole_point(self, x: int, y: int) -> int:
        pole_index = self.pole_at(x, y)
        point = self.s.connection_points[self.point_index(x, y)]
        self.s.poles[pole_index].current_branch_no = point.branch_no
        return pole_index

    def new(self, action: Action) -> None:
        self.s = Scheme(transformer=Transformer())
        self.snapshots = []
        apply_transformer(self.s.transformer, action.transformer or TransformerInput())
        self.outgoing(action)

    def outgoing(self, action: Action) -> None:
        if self.s.outgoing_count >= MAX_OUTGOING:
            raise EditError("Достигнуто максимальное количество отходящих от ТП ЛЭП!")
        t = self.s.transformer
        x, y = t.x + 3, t.y + ROW_STEP
        if self.s.outgoing_count > 0:
            y = self.lowest_end_right_of(x, self.s.outgoing_count - 1) + 2 * ROW_STEP
        end = self.attach_line(OUTGOING, x, y, action.line or LineInput())
        self.attach_pole(*end, action.pole or PoleInput())

    def span(self, action: Action) -> None:
        x, y = self.require(action, "span")
        self.select_pole_point(x, y)
        end = self.attach_line(SPAN, x, y, action.line or LineInput())
        self.attach_pole(*end, action.pole or PoleInput())

    def branch_line(self, action: Action) -> None:
        x, y = self.require(action, "branch_line")
        pole_index = self.select_pole_point(x, y)
        end = self.attach_line(BRANCH_LINE, x, y, action.line or LineInput(),
                               pole_index=pole_index, to_single=action.to_single)
        self.attach_pole(*end, action.pole or PoleInput())

    def branch_consumer(self, action: Action) -> None:
        x, y = self.require(action, "branch_consumer")
        pole_index = self.select_pole_point(x, y)
        end = self.attach_line(BRANCH_CONSUMER, x, y, action.line or LineInput(), pole_index=pole_index)
        self.attach_consumer(*end, action.consumer or ConsumerInput())

    def pole(self, action: Action) -> None:
        x, y = self.require(action, "pole")
        self.attach_pole(x, y, action.pole or PoleInput())

    def consumer(self, action: Action) -> None:
        x, y = self.require(action, "consumer")
        self.attach_consumer(x, y, action.consumer or ConsumerInput())

    def add_branch(self, action: Action) -> None:
        index = self.checked_index(action, self.s.poles, "опора")
        pole = self.s.poles[index]
        if pole.branch_count >= MAX_BRANCHES:
            raise EditError(f"У опоры не может быть больше {MAX_BRANCHES} ответвлений")
        pole.branch_count += 1
        pole.current_branch_no = 1
        pole.canvas_length += BRANCH_STEP
        pole.end_x += BRANCH_STEP
        x, y = pole.x, pole.y
        right_edge, bottom_edge = self.field_width, self.s.transformer.h
        for line in self.s.lines:
            if line.vertical == 0 and line.y > y and line.x <= x and line.end_x >= x:
                bottom_edge = min(bottom_edge, line.y)
        for other in self.s.poles:
            if other.y > y and other.x <= x and other.end_x >= x:
                bottom_edge = min(bottom_edge, other.y)
        for line in self.s.lines:
            if line.vertical == 1 and line.x > pole.end_x and line.y < y and line.end_y + CONSUMER_SIZE >= y:
                right_edge = min(right_edge, line.x)
        self.push_right(x, y, right_edge, bottom_edge, BRANCH_STEP, index)
        for point in self.s.connection_points:
            if point.point_kind == POLE and point.branch_no > 0 and self.pole_at(point.x, point.y) == index:
                point.branch_no += 1
        self.activate(pole.x + BRANCH_STEP, pole.y, POLE, 1, pole.feeder_no)
        self.current = (pole.x + BRANCH_STEP, pole.y)

    def checked_index(self, action: Action, items: list, name: str) -> int:
        if action.index is None or not 0 <= action.index < len(items):
            raise EditError(f"Не найден объект: {name}")
        return action.index

    def delete(self, action: Action) -> None:
        if action.target == "line":
            self.remove_line(self.checked_index(action, self.s.lines, "ЛЭП"))
        elif action.target == "pole":
            self.remove_pole(self.checked_index(action, self.s.poles, "опора"))
        elif action.target == "consumer":
            self.remove_consumer(self.checked_index(action, self.s.consumers, "потребитель"))
        elif action.target == "transformer":
            raise EditError("Трансформатор удалить нельзя — создайте новую схему")
        else:
            raise EditError("Не указан объект для удаления")

    def remove_line(self, index: int) -> None:
        line = self.s.lines[index]
        if any(c.x == line.end_x and c.y == line.end_y for c in self.s.consumers):
            raise EditError("К ЛЭП присоединён потребитель! ЛЭП не удалена!")
        if any(p.x == line.end_x and p.y == line.end_y for p in self.s.poles):
            raise EditError("К ЛЭП присоединена опора! ЛЭП не удалена!")
        start = self.point_index(line.x, line.y)
        end = self.point_index(line.end_x, line.end_y)
        if end is not None:
            del self.s.connection_points[end]
            if start is not None and end < start:
                start -= 1
        self.release("lines", index)
        if line.line_type == 0 and self.s.outgoing_count > 0:
            self.s.outgoing_count -= 1
        elif start is not None:
            self.s.connection_points[start].active = True
            self.current = (line.x, line.y)

    def remove_consumer(self, index: int) -> None:
        consumer = self.s.consumers[index]
        point = self.point_index(consumer.x, consumer.y)
        if point is not None:
            self.s.connection_points[point].active = True
        self.release("consumers", index)
        self.current = (consumer.x, consumer.y)

    def remove_pole(self, index: int) -> None:
        pole = self.s.poles[index]
        for line in self.s.lines:
            if line.x == pole.end_x and line.y == pole.end_y:
                raise EditError("К опоре присоединена ЛЭП! Опора не удалена!")
            for branch in range(pole.branch_count):
                if pole.x + (branch + 1) * BRANCH_STEP == line.x and pole.y == line.y:
                    raise EditError("К опоре присоединена ЛЭП! Опора не удалена!")
        start = self.point_index(pole.x, pole.y)
        if start is not None:
            self.s.connection_points[start].active = True
        self.delete_point(pole.end_x, pole.end_y)
        for branch in range(pole.branch_count):
            self.delete_point(pole.x + (branch + 1) * BRANCH_STEP, pole.y)
        self.release("poles", index)
        self.current = (pole.x, pole.y)

    def update(self, action: Action) -> None:
        fields = action.fields or {}
        try:
            if action.target == "transformer":
                t = self.s.transformer
                data = TransformerInput(**{**t.model_dump(), **fields})
                apply_transformer(t, data)
            elif action.target == "line":
                line = self.s.lines[self.checked_index(action, self.s.lines, "ЛЭП")]
                data = LineInput(**{**line.model_dump(), **fields})
                self.update_line(line, data)
            elif action.target == "pole":
                pole = self.s.poles[self.checked_index(action, self.s.poles, "опора")]
                pole.label = PoleInput(label=fields.get("label", pole.label), branch_count=0).label
            elif action.target == "consumer":
                consumer = self.s.consumers[self.checked_index(action, self.s.consumers, "потребитель")]
                current = consumer.model_dump()
                if not known_category(current["category"]):
                    current["category"] = None
                data = ConsumerInput(**{**current, **fields})
                if data.type_text is None:
                    data.type_text = consumer.type_text
                apply_consumer(consumer, data)
            else:
                raise EditError("Не указан объект для изменения")
        except ValidationError as exc:
            raise EditError(first_error(exc)) from exc

    def update_line(self, line: Line, data: LineInput) -> None:
        apply_line(line, data)
        for consumer in self.s.consumers:
            if consumer.x == line.end_x and consumer.y == line.end_y:
                if consumer.phase_mode != line.phase_mode:
                    consumer.type_text = default_type_text(line.phase_mode)
                consumer.phase_mode = line.phase_mode
                consumer.phase_no = line.phase_no
                break

    def apply(self, action: Action) -> Scheme:
        handler = {
            "new": self.new, "outgoing": self.outgoing, "span": self.span,
            "branch_line": self.branch_line, "branch_consumer": self.branch_consumer,
            "pole": self.pole, "consumer": self.consumer, "add_branch": self.add_branch,
            "update": self.update, "delete": self.delete,
        }[action.kind]
        handler(action)
        return self.s


def first_error(exc: ValidationError) -> str:
    return describe(exc.errors())

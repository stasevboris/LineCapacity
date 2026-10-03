from __future__ import annotations

from ..scheme.model import ConnectionPoint, Consumer, Line, Pole, Scheme, Transformer

ENCODING = "cp1251"
NEWLINE = "\r\n"


class CirFormatError(ValueError):
    pass


def parse_number(text: str) -> float:
    value = text.strip().replace(",", ".")
    if not value:
        raise CirFormatError("пустое числовое поле")
    try:
        return float(value)
    except ValueError as exc:
        raise CirFormatError(f"не число: «{text.strip()}»") from exc


def parse_int(text: str) -> int:
    value = parse_number(text)
    if not value.is_integer():
        raise CirFormatError(f"ожидалось целое число: «{text.strip()}»")
    return int(value)


def format_number(value: float) -> str:
    number = float(value)
    if number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    text = format(number, ".15g")
    if "e" in text:
        mantissa, exponent = text.split("e")
        text = f"{mantissa}E{int(exponent)}"
    return text.replace(".", ",")


class Reader:
    def __init__(self, text: str) -> None:
        self.rows = text.splitlines()
        self.position = 0

    def text(self) -> str:
        if self.position >= len(self.rows):
            raise CirFormatError("файл закончился раньше ожидаемого")
        value = self.rows[self.position]
        self.position += 1
        return value

    def integer(self) -> int:
        return parse_int(self.text())

    def number(self) -> float:
        return parse_number(self.text())


def decode(raw: bytes) -> str:
    for encoding in ("utf-8", ENCODING):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        return text.lstrip(chr(0xFEFF))
    raise CirFormatError("неизвестная кодировка файла")


def loads(text: str) -> Scheme:
    r = Reader(text)
    count_lines = r.integer()
    count_poles = r.integer()
    count_consumers = r.integer()
    count_points = r.integer()
    outgoing = r.integer()
    if min(count_lines, count_poles, count_consumers, count_points, outgoing) < 0:
        raise CirFormatError("отрицательное количество объектов в заголовке")
    transformer = Transformer(
        type_name=r.text(), label=r.text(),
        x=r.integer(), y=r.integer(), h=r.integer(),
        sn_kva=r.number(), px_kw=r.number(), pk_kw=r.number(),
        unn_kv=r.number(), uvn_kv=r.number(), uk_percent=r.number(),
        pbv_step=r.integer(), pbv_steps=r.integer(), pbv_percent=r.number(),
        r_ohm=r.number(), x_ohm=r.number(), kt=r.number(),
    )
    lines = [Line(
        type_name=r.text(), label=r.text(),
        x=r.integer(), y=r.integer(), end_x=r.integer(), end_y=r.integer(),
        vertical=r.integer(), line_type=r.integer(), phase_mode=r.integer(),
        length_m=r.number(), canvas_length=r.integer(),
        r_phase_ohm_per_km=r.number(), r_neutral_ohm_per_km=r.number(),
        r_single_phase_ohm_per_km=r.number(), phase_no=r.integer(),
        r_phase_ohm=r.number(), r_neutral_ohm=r.number(),
        feeder_no=r.integer(),
    ) for _ in range(count_lines)]
    poles = [Pole(
        label=r.text(),
        x=r.integer(), y=r.integer(), end_x=r.integer(), end_y=r.integer(),
        canvas_length=r.integer(), branch_count=r.integer(),
        current_branch_no=r.integer(), feeder_no=r.integer(),
    ) for _ in range(count_poles)]
    consumers = [Consumer(
        type_text=r.text(), label=r.text(), address=r.text(),
        x=r.integer(), y=r.integer(),
        p_kw=r.number(), cos_phi=r.number(),
        phase_mode=r.integer(), phase_no=r.integer(),
        load_type=r.integer(), annual_kwh=r.number(),
        category=r.number(), feeder_no=r.integer(),
    ) for _ in range(count_consumers)]
    points = [ConnectionPoint(
        x=r.integer(), y=r.integer(), active=bool(r.integer()),
        point_kind=r.integer(), object_no=r.integer(),
        branch_no=r.integer(), feeder_no=r.integer(),
    ) for _ in range(count_points)]
    return Scheme(transformer=transformer, lines=lines, poles=poles,
                  consumers=consumers, connection_points=points,
                  outgoing_count=outgoing)


def rows(scheme: Scheme) -> list[str]:
    t = scheme.transformer
    out = [
        str(len(scheme.lines)), str(len(scheme.poles)),
        str(len(scheme.consumers)), str(len(scheme.connection_points)),
        str(scheme.outgoing_count),
        t.type_name, t.label, str(t.x), str(t.y), str(t.h),
        format_number(t.sn_kva), format_number(t.px_kw), format_number(t.pk_kw),
        format_number(t.unn_kv), format_number(t.uvn_kv),
        format_number(t.uk_percent),
        str(t.pbv_step), str(t.pbv_steps), format_number(t.pbv_percent),
        format_number(t.r_ohm), format_number(t.x_ohm), format_number(t.kt),
    ]
    for wire in scheme.lines:
        out += [
            wire.type_name, wire.label,
            str(wire.x), str(wire.y), str(wire.end_x), str(wire.end_y),
            str(wire.vertical), str(wire.line_type), str(wire.phase_mode),
            format_number(wire.length_m), str(wire.canvas_length),
            format_number(wire.r_phase_ohm_per_km),
            format_number(wire.r_neutral_ohm_per_km),
            format_number(wire.r_single_phase_ohm_per_km),
            str(wire.phase_no),
            format_number(wire.r_phase_ohm), format_number(wire.r_neutral_ohm),
            str(wire.feeder_no),
        ]
    for pole in scheme.poles:
        out += [
            pole.label, str(pole.x), str(pole.y), str(pole.end_x), str(pole.end_y),
            str(pole.canvas_length), str(pole.branch_count),
            str(pole.current_branch_no), str(pole.feeder_no),
        ]
    for cn in scheme.consumers:
        out += [
            cn.type_text, cn.label, cn.address, str(cn.x), str(cn.y),
            format_number(cn.p_kw), format_number(cn.cos_phi),
            str(cn.phase_mode), str(cn.phase_no), str(cn.load_type),
            format_number(cn.annual_kwh), format_number(cn.category), str(cn.feeder_no),
        ]
    for cp in scheme.connection_points:
        out += [
            str(cp.x), str(cp.y), str(int(cp.active)), str(cp.point_kind),
            str(cp.object_no), str(cp.branch_no), str(cp.feeder_no),
        ]
    return out


def dumps(scheme: Scheme) -> str:
    return "".join(row + NEWLINE for row in rows(scheme))


def load_bytes(raw: bytes) -> Scheme:
    return loads(decode(raw))


def dump_bytes(scheme: Scheme) -> bytes:
    return dumps(scheme).encode(ENCODING)

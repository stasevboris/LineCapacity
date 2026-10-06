from __future__ import annotations

FIELDS = {
    "type_name": "марка", "label": "надпись", "length_m": "длина", "phase_mode": "фазность",
    "r_phase_ohm_per_km": "Rф", "r_neutral_ohm_per_km": "R0", "r_single_phase_ohm_per_km": "R проводов",
    "phase_no": "фаза", "sn_kva": "Sн", "px_kw": "Pхх", "pk_kw": "Pкз", "unn_kv": "Uнн", "uvn_kv": "Uвн",
    "uk_percent": "Uк", "pbv_steps": "число ступеней ПБВ", "pbv_step": "ступень ПБВ",
    "pbv_percent": "шаг ступени ПБВ", "branch_count": "количество ответвлений", "address": "адрес",
    "type_text": "дополнительные данные", "p_kw": "мощность", "cos_phi": "cos φ",
    "annual_kwh": "годовое потребление", "category": "тип потребителя", "load_type": "вид нагрузки",
    "name": "название", "kind": "действие", "x": "координата x", "y": "координата y", "h": "высота шины",
    "target": "объект", "index": "номер объекта", "point": "точка присоединения", "fields": "параметры",
    "scheme": "схема", "action": "действие", "file": "файл", "outgoing_count": "число отходящих линий",
    "current_branch_no": "текущее ответвление", "feeder_no": "номер отходящей линии",
    "canvas_length": "длина на схеме", "vertical": "направление", "line_type": "вид ЛЭП",
    "end_x": "конец x", "end_y": "конец y", "point_kind": "тип точки", "object_no": "номер объекта точки",
    "branch_no": "номер ответвления", "active": "активность", "spare": "резерв удалённых объектов",
    "block": "состояние для отмены",
    "email": "почта", "password": "пароль", "current": "текущий пароль", "new": "новый пароль",
    "language": "язык", "archived": "архив", "source": "исходный вариант", "variant": "вариант",
    "team": "команда", "role": "роль", "accept": "ответ", "ids": "уведомления", "to_user": "получатель",
    "user_id": "собеседник",
}
LISTS = {"lines": "ЛЭП", "poles": "опора", "consumers": "потребитель", "connection_points": "присоединение"}
SECTIONS = {"transformer": "трансформатор", "line": "ЛЭП", "pole": "опора", "consumer": "потребитель"}
SKIP = {"body", "query", "path", "action", "scheme"}


def place(location) -> str:
    parts = []
    items = list(location)
    i = 0
    while i < len(items):
        item = items[i]
        if isinstance(item, str) and item in LISTS and i + 1 < len(items) and isinstance(items[i + 1], int):
            parts.append(f"{LISTS[item]} № {items[i + 1] + 1}")
            i += 2
            continue
        if isinstance(item, str) and item in SECTIONS:
            parts.append(SECTIONS[item])
        elif isinstance(item, str) and item not in SKIP:
            parts.append(FIELDS.get(item, item))
        i += 1
    return ", ".join(parts)


def reason(error: dict) -> str:
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    if kind == "missing":
        return "не указано"
    if kind in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
        sign = {"greater_than": "больше", "greater_than_equal": "не меньше",
                "less_than": "меньше", "less_than_equal": "не больше"}[kind]
        limit = next(iter(v for k, v in ctx.items() if k in ("gt", "ge", "lt", "le")), "")
        if isinstance(limit, float) and limit.is_integer():
            limit = int(limit)
        return f"должно быть {sign} {str(limit).replace('.', ',')}"
    if kind == "string_too_long":
        return f"слишком длинное значение (не более {ctx.get('max_length')} символов)"
    if kind == "string_too_short":
        return "не может быть пустым"
    if kind == "too_long":
        return f"слишком много элементов (не более {ctx.get('max_length')})"
    if kind in ("float_parsing", "float_type", "int_parsing", "int_type"):
        return "должно быть числом"
    if kind == "int_from_float":
        return "должно быть целым числом"
    if kind == "finite_number":
        return "должно быть конечным числом"
    if kind in ("literal_error", "enum"):
        return "недопустимое значение"
    if kind in ("bool_parsing", "bool_type"):
        return "должно быть «да» или «нет»"
    if kind in ("string_type", "dict_type", "list_type", "model_type", "model_attributes_type"):
        return "неверный формат"
    if kind == "value_error":
        message = str(ctx.get("error") or error.get("msg", ""))
        return message.removeprefix("Value error, ")
    return "недопустимое значение"


def describe(errors: list[dict]) -> str:
    if not errors:
        return "Некорректные данные"
    error = errors[0]
    where = place(error.get("loc", ()))
    text = reason(error)
    return f"{where[:1].upper() + where[1:]}: {text}" if where else text[:1].upper() + text[1:]

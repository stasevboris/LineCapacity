"""
Общие хелперы и декораторы прав для всех представлений.

Содержит:
    * require_methods — универсальный декоратор ограничения HTTP-методов
    * staff_required  — декоратор «только админ или суперюзер»
    * superuser_required — декоратор «только суперюзер»
    * json_error / json_ok — единообразные JSON-ответы
    * get_val — безопасное извлечение значения из Django-модели
    * CrudView — базовый класс для CRUD-ресурсов справочников (ООП-слой)
"""

from functools import wraps
import json

from django.http import JsonResponse


# ------------------------------------------------------------------ #
# Унифицированные JSON-ответы
# ------------------------------------------------------------------ #
def json_ok(message: str = '', **extra):
    """Успешный JSON-ответ. Любые keyword-поля попадают в тело."""
    payload = {'status': 'success'}
    if message:
        payload['message'] = message
    payload.update(extra)
    return JsonResponse(payload)


def json_error(message: str, status: int = 400, **extra):
    """Ошибочный JSON-ответ с корректным HTTP-кодом."""
    payload = {'status': 'error', 'message': message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


# ------------------------------------------------------------------ #
# Декораторы проверки прав
# ------------------------------------------------------------------ #
def require_methods(*methods):
    """Разрешает доступ только указанным HTTP-методам."""
    methods = tuple(m.upper() for m in methods)

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return json_error('Метод не поддерживается', status=405)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def staff_required(func):
    """Только администраторы или суперюзеры (is_staff / is_superuser)."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return json_error('Доступ запрещен', status=403)
        return func(request, *args, **kwargs)
    return wrapper


def superuser_required(func):
    """Только суперюзер."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return json_error('Только суперюзер имеет доступ', status=403)
        return func(request, *args, **kwargs)
    return wrapper


# ------------------------------------------------------------------ #
# Утилиты
# ------------------------------------------------------------------ #
def get_val(obj, field_name):
    """Безопасно возвращает строковое значение поля, либо «—»."""
    val = getattr(obj, field_name, None)
    if val is None or str(val).strip() == '':
        return '—'
    return str(val)


def parse_json_body(request):
    """Парсит JSON-тело запроса. Возвращает dict или пустой dict."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except ValueError:
        return {}


def to_float(value, default=None):
    """Аккуратное приведение к float с учётом пустых строк."""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=None):
    """Аккуратное приведение к int с учётом пустых строк."""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------------ #
# Базовый CRUD-класс
# ------------------------------------------------------------------ #
class CrudView:
    """
    Базовый OOP-слой для CRUD справочников (ТП, ЛЭП, Потребители, ...).

    Наследник задаёт:
        model           — Django-модель
        order_by        — поле для сортировки списка
        fields_read     — {json_key: model_attr} для чтения
        fields_write    — {json_key: (model_attr, parser)} для записи

    Методы list/create/update/delete — тонкие обёртки с единой обработкой
    ошибок, правами доступа и JSON-ответами.
    """

    model = None
    order_by = 'id'
    fields_read: dict = {}
    fields_write: dict = {}

    # -------- сериализация -------- #
    @classmethod
    def serialize(cls, obj) -> dict:
        data = {'id': obj.id}
        for key, attr in cls.fields_read.items():
            val = getattr(obj, attr, None)
            data[key] = '' if val is None else str(val) if not isinstance(val, str) else val
        return data

    # -------- read -------- #
    @classmethod
    def list(cls, request):
        qs = cls.model.objects.all().order_by(cls.order_by)
        return json_ok(data=[cls.serialize(o) for o in qs])

    # -------- create -------- #
    @classmethod
    def create(cls, request):
        data = parse_json_body(request)
        kwargs = cls._apply_fields({}, data, for_create=True)
        obj = cls.model.objects.create(**kwargs)
        return json_ok(f'{cls.model.__name__} создан', id=obj.id)

    # -------- update -------- #
    @classmethod
    def update(cls, request, obj_id):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(cls.model, id=obj_id)
        data = parse_json_body(request)
        for key, (attr, parser) in cls.fields_write.items():
            if key in data:
                setattr(obj, attr, parser(data[key]))
        obj.save()
        return json_ok(f'{cls.model.__name__} обновлён')

    # -------- delete -------- #
    @classmethod
    def delete(cls, request, obj_id):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(cls.model, id=obj_id)
        obj.delete()
        return json_ok(f'{cls.model.__name__} удалён')

    # -------- internal -------- #
    @classmethod
    def _apply_fields(cls, target: dict, data: dict, for_create: bool) -> dict:
        for key, (attr, parser) in cls.fields_write.items():
            if for_create or key in data:
                target[attr] = parser(data.get(key))
        return target

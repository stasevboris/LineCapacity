"""
API для каталогов и деталей справочных объектов.

    * get_catalog_nodes — пагинированный список объектов (ТП/ЛЭП/Абонент)
      с поиском, для модального окна «Каталог» в редакторе схем.
    * get_node_details — полные свойства одного объекта справочника,
      запрашивается, когда пользователь кликает на элемент схемы.
"""

from django.core.paginator import Paginator
from django.http import JsonResponse

from ..models import RefTransformer, RefLine, RefConsumerType
from .base import get_val


# --------------------------------------------------------------------- #
# Наборы полей для детального показа — выносим наружу, чтобы не дублировать.
# --------------------------------------------------------------------- #
TRANSFORMER_DETAILS = {
    'Тип трансформатора': 'type_name',
    'Номинальная мощность, кВА': 'nominal_power',
    'Потери ХХ, кВт': 'losses_no_load',
    'Потери КЗ, кВт': 'losses_short_circuit',
    'Номинальное напряжение ВН, кВ': 'voltage_hv',
    'Номинальное напряжение НН, кВ': 'voltage_lv',
    'Напряжение КЗ, %': 'voltage_short_circuit_pct',
    'Количество ступеней ПБВ': 'pbv_stages_count',
    'Шаг одной ступени ПБВ, %': 'pbv_step_pct',
}

LINE_DETAILS = {
    'Марка ЛЭП': 'mark',
    'Материал провода': 'material',
    'Материал изоляции': 'insulation',
    'Количество жил': 'cores_count',
    'Сечение фазного провода, мм²': 'cross_section',
    'Сопротивление фазного, Ом/км': 'r_phase_ohm_km',
    'Сопротивление нулевого, Ом/км': 'r_null_ohm_km',
    'Сопротивление доп. провода, Ом/км': 'r_add_ohm_km',
}

CONSUMER_DETAILS = {
    'Тип потребителя': 'name',
    'Характер электропотребления': 'usage_character',
    'Адрес потребителя': 'address',
    'Дополнительные данные': 'additional_data',
    'Питание потребителя': 'supply_type',
    'Номер фазы': 'phase_number',
    'Параметры электропотребления (тип)': 'calc_method',
    'Годовое потребление, кВт*ч': 'yearly_consumption_kwh',
    'Расчётная активная мощность, кВт': 'calculated_active_power_kw',
    'Коэффициент мощности (косинус фи)': 'cos_phi',
}


def _build_details(obj, mapping: dict) -> dict:
    """Применяет {label: attr} к объекту, пропуская пустые значения через «—»."""
    return {label: get_val(obj, attr) for label, attr in mapping.items()}


# --------------------------------------------------------------------- #
# Каталог: пагинированный список с поиском
# --------------------------------------------------------------------- #
_CATALOG_CONFIG = {
    'ТП': {
        'model': RefTransformer,
        'order_by': 'type_name',
        'search_field': 'type_name__icontains',
        'details_map': TRANSFORMER_DETAILS,
    },
    'ЛЭП': {
        'model': RefLine,
        'order_by': 'mark',
        'search_field': 'mark__icontains',
        'details_map': LINE_DETAILS,
    },
    'Абонент': {
        'model': RefConsumerType,
        'order_by': 'name',
        'search_field': 'name__icontains',
        'details_map': CONSUMER_DETAILS,
    },
}


def _item_name(category, obj):
    if category == 'ТП':
        return obj.type_name
    if category == 'ЛЭП':
        return obj.mark
    return obj.name


def _item_power(category, obj):
    if category == 'ТП' and obj.nominal_power:
        return str(obj.nominal_power)
    return ''


def get_catalog_nodes(request):
    """Отдаёт таблицу объектов для модального каталога."""
    category = request.GET.get('category')
    page_num = int(request.GET.get('page', 1))
    search_q = request.GET.get('search', '').strip()

    cfg = _CATALOG_CONFIG.get(category)
    if not cfg:
        return JsonResponse({'error': 'Invalid category'}, status=400)

    qs = cfg['model'].objects.all().order_by(cfg['order_by'])
    if search_q:
        qs = qs.filter(**{cfg['search_field']: search_q})

    paginator = Paginator(qs, 50)
    try:
        page_obj = paginator.page(page_num)
    except Exception:
        page_obj = paginator.page(1)

    items = []
    for obj in page_obj:
        items.append({
            'id': obj.id,
            'name': _item_name(category, obj),
            'type': category,
            'power': _item_power(category, obj),
            'details': _build_details(obj, cfg['details_map']),
        })

    return JsonResponse({
        'items': items,
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


# --------------------------------------------------------------------- #
# Полные свойства одного объекта
# --------------------------------------------------------------------- #
_DETAILS_CONFIG = {
    'ТП': (RefTransformer, TRANSFORMER_DETAILS),
    'ЛЭП': (RefLine, LINE_DETAILS),
    'Абонент': (RefConsumerType, CONSUMER_DETAILS),
}


def get_node_details(request):
    """Возвращает словарь «русское название → значение» для одного объекта."""
    db_id = request.GET.get('db_id')
    obj_type = request.GET.get('type')

    if not db_id or not obj_type or obj_type not in _DETAILS_CONFIG:
        return JsonResponse({'details': {}})

    model, mapping = _DETAILS_CONFIG[obj_type]
    try:
        obj = model.objects.get(id=db_id)
    except model.DoesNotExist:
        return JsonResponse({'details': {}})

    return JsonResponse({'details': _build_details(obj, mapping)})

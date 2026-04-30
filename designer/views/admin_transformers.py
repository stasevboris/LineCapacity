"""CRUD справочника трансформаторов (ТП)."""

from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from ..models import RefTransformer
from .base import (
    CrudView, json_ok, json_error, parse_json_body,
    staff_required, superuser_required, require_methods,
    to_float, to_int,
)


class TransformerCrud(CrudView):
    model = RefTransformer
    order_by = 'type_name'

    # При чтении всё возвращаем как строки (фронт ожидает строки).
    fields_read = {
        'type_name': 'type_name',
        'nominal_power': 'nominal_power',
        'losses_no_load': 'losses_no_load',
        'losses_short_circuit': 'losses_short_circuit',
        'voltage_hv': 'voltage_hv',
        'voltage_lv': 'voltage_lv',
        'voltage_short_circuit_pct': 'voltage_short_circuit_pct',
        'pbv_stages_count': 'pbv_stages_count',
        'pbv_step_pct': 'pbv_step_pct',
    }

    fields_write = {
        'type_name': ('type_name', lambda v: v or ''),
        'nominal_power': ('nominal_power', to_float),
        'losses_no_load': ('losses_no_load', to_float),
        'losses_short_circuit': ('losses_short_circuit', to_float),
        'voltage_hv': ('voltage_hv', to_float),
        'voltage_lv': ('voltage_lv', to_float),
        'voltage_short_circuit_pct': ('voltage_short_circuit_pct', to_float),
        'pbv_stages_count': ('pbv_stages_count', to_int),
        'pbv_step_pct': ('pbv_step_pct', to_float),
    }


# ------------------------- view-функции для urls.py ------------------------- #
@csrf_exempt
@staff_required
def api_transformers_list(request):
    return TransformerCrud.list(request)


@csrf_exempt
@require_methods('POST')
@staff_required
def api_transformer_create(request):
    try:
        return TransformerCrud.create(request)
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('PUT')
@staff_required
def api_transformer_update(request, obj_id):
    try:
        return TransformerCrud.update(request, obj_id)
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('DELETE')
@superuser_required
def api_transformer_delete(request, obj_id):
    try:
        return TransformerCrud.delete(request, obj_id)
    except Exception as e:
        return json_error(str(e))

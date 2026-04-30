"""CRUD справочника ЛЭП (RefLine)."""

from django.views.decorators.csrf import csrf_exempt

from ..models import RefLine
from .base import (
    CrudView, json_error, staff_required, superuser_required,
    require_methods, to_float, to_int,
)


class LineCrud(CrudView):
    model = RefLine
    order_by = 'mark'

    fields_read = {
        'mark': 'mark',
        'material': 'material',
        'insulation': 'insulation',
        'cores_count': 'cores_count',
        'cross_section': 'cross_section',
        'r_phase_ohm_km': 'r_phase_ohm_km',
        'r_null_ohm_km': 'r_null_ohm_km',
        'r_add_ohm_km': 'r_add_ohm_km',
    }

    fields_write = {
        'mark': ('mark', lambda v: v or ''),
        'material': ('material', lambda v: v or ''),
        'insulation': ('insulation', lambda v: v or ''),
        'cores_count': ('cores_count', to_int),
        'cross_section': ('cross_section', to_float),
        'r_phase_ohm_km': ('r_phase_ohm_km', to_float),
        'r_null_ohm_km': ('r_null_ohm_km', to_float),
        'r_add_ohm_km': ('r_add_ohm_km', to_float),
    }


@csrf_exempt
@staff_required
def api_lines_list(request):
    return LineCrud.list(request)


@csrf_exempt
@require_methods('POST')
@staff_required
def api_line_create(request):
    try:
        return LineCrud.create(request)
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('PUT')
@staff_required
def api_line_update(request, obj_id):
    try:
        return LineCrud.update(request, obj_id)
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('DELETE')
@superuser_required
def api_line_delete(request, obj_id):
    try:
        return LineCrud.delete(request, obj_id)
    except Exception as e:
        return json_error(str(e))

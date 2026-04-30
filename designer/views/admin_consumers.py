"""CRUD справочника потребителей (RefConsumerType)."""

from django.views.decorators.csrf import csrf_exempt

from ..models import RefConsumerType
from .base import (
    CrudView, json_error, staff_required, superuser_required,
    require_methods, to_float, to_int,
)


class ConsumerCrud(CrudView):
    model = RefConsumerType
    order_by = 'name'

    fields_read = {
        'name': 'name',
        'usage_character': 'usage_character',
        'address': 'address',
        'additional_data': 'additional_data',
        'supply_type': 'supply_type',
        'phase_number': 'phase_number',
        'calc_method': 'calc_method',
        'yearly_consumption_kwh': 'yearly_consumption_kwh',
        'calculated_active_power_kw': 'calculated_active_power_kw',
        'cos_phi': 'cos_phi',
    }

    fields_write = {
        'name': ('name', lambda v: v or ''),
        'usage_character': ('usage_character', lambda v: v or ''),
        'address': ('address', lambda v: v or ''),
        'additional_data': ('additional_data', lambda v: v or ''),
        'supply_type': ('supply_type', lambda v: v or ''),
        'phase_number': ('phase_number', to_int),
        'calc_method': ('calc_method', lambda v: v or ''),
        'yearly_consumption_kwh': ('yearly_consumption_kwh', to_float),
        'calculated_active_power_kw': ('calculated_active_power_kw', to_float),
        'cos_phi': ('cos_phi', to_float),
    }


@csrf_exempt
@staff_required
def api_consumers_list(request):
    return ConsumerCrud.list(request)


@csrf_exempt
@require_methods('POST')
@staff_required
def api_consumer_create(request):
    try:
        return ConsumerCrud.create(request)
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('PUT')
@staff_required
def api_consumer_update(request, obj_id):
    try:
        return ConsumerCrud.update(request, obj_id)
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('DELETE')
@superuser_required
def api_consumer_delete(request, obj_id):
    try:
        return ConsumerCrud.delete(request, obj_id)
    except Exception as e:
        return json_error(str(e))

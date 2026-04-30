"""CRUD организаций + создание новой организации (суперюзер)."""

from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from ..models import Organization
from .base import (
    json_ok, json_error, parse_json_body,
    staff_required, superuser_required, require_methods,
)


def _serialize(org):
    return {
        'id': org.id,
        'name': org.name or '',
        'address': org.address or '',
        'phone': org.phone or '',
        'fax': org.fax or '',
    }


@csrf_exempt
@staff_required
def api_organizations_list(request):
    """Суперюзер видит все организации, админ — только свою."""
    if request.user.is_superuser:
        orgs = Organization.objects.all()
    else:
        user_org = request.user.profile.organization if hasattr(request.user, 'profile') else None
        orgs = (
            Organization.objects.filter(id=user_org.id) if user_org
            else Organization.objects.none()
        )
    return json_ok(data=[_serialize(o) for o in orgs])


@csrf_exempt
@require_methods('POST')
@superuser_required
def api_create_organization(request):
    """Создание новой организации. Доступно только суперюзеру."""
    try:
        data = parse_json_body(request)
        org = Organization.objects.create(
            name=data.get('name'),
            address=data.get('region', ''),
            phone=data.get('phone', ''),
            fax=data.get('fax', ''),
        )
        return json_ok(f'Организация "{org.name}" успешно создана!')
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('PUT')
@staff_required
def api_organization_update(request, obj_id):
    """Локальный админ может редактировать только свою организацию."""
    try:
        org = get_object_or_404(Organization, id=obj_id)
        data = parse_json_body(request)

        if not request.user.is_superuser:
            admin_org = request.user.profile.organization if hasattr(request.user, 'profile') else None
            if not admin_org or admin_org.id != org.id:
                return json_error('Можно редактировать только свою организацию', status=403)

        for key in ('name', 'address', 'phone', 'fax'):
            if key in data:
                setattr(org, key, data.get(key, ''))

        org.save()
        return json_ok('Организация обновлена')
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('DELETE')
@superuser_required
def api_organization_delete(request, obj_id):
    try:
        org = get_object_or_404(Organization, id=obj_id)
        org.delete()
        return json_ok('Организация удалена')
    except Exception as e:
        return json_error(str(e))

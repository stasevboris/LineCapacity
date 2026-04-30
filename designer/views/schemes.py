from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import SchemeRevision, Scheme, Folder, Organization
from .base import (
    json_ok, json_error, require_methods, staff_required, parse_json_body,
)


def _user_organization(user):
    if not user.is_authenticated:
        return None
    if hasattr(user, 'profile'):
        return user.profile.organization
    return None


def _resolve_target_organization(request, requested_org_id):
    if request.user.is_superuser:
        if requested_org_id in (None, '', 'null'):
            return None, None
        org = Organization.objects.filter(id=requested_org_id).first()
        if not org:
            return None, 'Организация не найдена'
        return org, None

    user_org = _user_organization(request.user)
    if not user_org:
        return None, 'У пользователя не задана организация'

    if requested_org_id not in (None, '', 'null') and str(requested_org_id) != str(user_org.id):
        return None, 'Можно сохранять только в свою организацию'

    return user_org, None


def _visible_folders_qs(user):
    if user.is_authenticated and user.is_superuser:
        return Folder.objects.all()
    user_org = _user_organization(user)
    if user_org:
        return Folder.objects.filter(Q(org__isnull=True) | Q(org=user_org))
    return Folder.objects.filter(org__isnull=True)


def _visible_schemes_qs(user):
    if user.is_authenticated and user.is_superuser:
        return Scheme.objects.all()
    user_org = _user_organization(user)
    if user_org:
        return Scheme.objects.filter(Q(organization__isnull=True) | Q(organization=user_org))
    return Scheme.objects.filter(organization__isnull=True)


def _can_user_use_folder(user, folder):
    if user.is_superuser:
        return True
    if folder.org_id is None:
        return True
    user_org = _user_organization(user)
    return bool(user_org and folder.org_id == user_org.id)


@csrf_exempt
@require_methods('POST')
def save_scheme_api(request):
    if not request.user.is_authenticated:
        return json_error('Требуется авторизация', status=401)

    try:
        data = parse_json_body(request)
        scheme_name = data.get('name', 'Новая схема')
        folder_id = data.get('folder_id')
        requested_org_id = data.get('organization_id')

        organization, err = _resolve_target_organization(request, requested_org_id)
        if err:
            return json_error(err, status=403)

        if folder_id:
            folder = get_object_or_404(Folder, id=folder_id)
            if not _can_user_use_folder(request.user, folder):
                return json_error('Нет доступа к выбранной папке', status=403)
        else:
            folder, _ = Folder.objects.get_or_create(
                name='Рабочие схемы', org=organization,
            )

        topology = {
            'nodes': data.get('nodes', []),
            'lines': data.get('lines', []),
        }

        scheme, _ = Scheme.objects.get_or_create(
            name=scheme_name,
            folder=folder,
            defaults={'organization': organization},
        )
        if scheme.organization_id is None and organization is not None:
            scheme.organization = organization
            scheme.save(update_fields=['organization'])

        revision = SchemeRevision.objects.create(
            scheme=scheme,
            label=f"Версия от {timezone.now().strftime('%d.%m.%Y %H:%M')}",
            topology_data=topology,
            created_by=request.user,
        )
        return json_ok(id=revision.id)
    except Exception as e:
        return json_error(str(e))


def list_revisions_api(request):
    schemes = _visible_schemes_qs(request.user)
    revisions = (
        SchemeRevision.objects.filter(scheme__in=schemes)
        .order_by('-created_at')
        .values('id', 'label', 'created_at')
    )
    return json_ok(revisions=list(revisions))


def load_scheme_api(request, rev_id):
    revision = get_object_or_404(SchemeRevision, id=rev_id)
    if not _visible_schemes_qs(request.user).filter(id=revision.scheme_id).exists():
        return json_error('Нет доступа к этой схеме', status=403)
    return json_ok(topology_data=revision.topology_data, label=revision.label)


def load_scheme_by_id_api(request, scheme_id):
    if not _visible_schemes_qs(request.user).filter(id=scheme_id).exists():
        return json_error('Нет доступа к этой схеме', status=403)

    scheme = get_object_or_404(Scheme, id=scheme_id)
    last_revision = scheme.revisions.order_by('-created_at').first()

    if not last_revision:
        return json_error('У схемы нет сохранений', status=404)

    return json_ok(
        name=scheme.name,
        topology_data=last_revision.topology_data,
    )


def api_get_registry(request):
    folders_qs = _visible_folders_qs(request.user)
    schemes_qs = _visible_schemes_qs(request.user)

    folders = list(folders_qs.values('id', 'name', 'parent_id', 'org_id'))
    schemes = list(schemes_qs.values('id', 'name', 'folder_id', 'organization_id'))

    organizations = []
    if request.user.is_authenticated:
        if request.user.is_superuser:
            organizations = list(Organization.objects.values('id', 'name'))
        else:
            user_org = _user_organization(request.user)
            if user_org:
                organizations = [{'id': user_org.id, 'name': user_org.name}]

    return json_ok(
        folders=folders,
        schemes=schemes,
        organizations=organizations,
        is_superuser=bool(request.user.is_authenticated and request.user.is_superuser),
        current_org_id=(_user_organization(request.user).id
                        if _user_organization(request.user) else None),
    )


@csrf_exempt
@require_methods('POST')
@staff_required
def api_create_folder(request):
    data = parse_json_body(request)
    name = data.get('name')
    parent_id = data.get('parent_id')
    requested_org_id = data.get('organization_id')

    if not name:
        return json_error('Имя папки обязательно')

    organization, err = _resolve_target_organization(request, requested_org_id)
    if err:
        return json_error(err, status=403)

    parent = None
    if parent_id:
        parent = Folder.objects.filter(id=parent_id).first()
        if parent and not _can_user_use_folder(request.user, parent):
            return json_error('Нет доступа к родительской папке', status=403)

    Folder.objects.create(name=name, parent=parent, org=organization)
    return json_ok('Папка успешно создана')


@csrf_exempt
@require_methods('PUT')
@staff_required
def api_edit_folder(request, folder_id):
    try:
        folder = get_object_or_404(Folder, id=folder_id)
        if not _can_user_use_folder(request.user, folder):
            return json_error('Нет доступа к папке', status=403)

        data = parse_json_body(request)
        folder.name = data.get('name', folder.name)
        if 'parent_id' in data:
            parent_id = data.get('parent_id')
            new_parent = (
                Folder.objects.filter(id=parent_id).first() if parent_id else None
            )
            if new_parent and not _can_user_use_folder(request.user, new_parent):
                return json_error('Нет доступа к новой родительской папке', status=403)
            folder.parent = new_parent

        if request.user.is_superuser and 'organization_id' in data:
            org_id = data.get('organization_id')
            folder.org = (
                Organization.objects.filter(id=org_id).first() if org_id else None
            )

        folder.save()
        return json_ok('Папка обновлена')
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('DELETE')
@staff_required
def api_delete_folder(request, folder_id):
    try:
        folder = get_object_or_404(Folder, id=folder_id)
        if not _can_user_use_folder(request.user, folder):
            return json_error('Нет доступа к папке', status=403)
        if folder.org_id is None and not request.user.is_superuser:
            return json_error('Общую папку может удалить только суперпользователь', status=403)
        folder.delete()
        return json_ok('Папка удалена')
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('DELETE')
@staff_required
def api_delete_scheme(request, scheme_id):
    try:
        scheme = get_object_or_404(Scheme, id=scheme_id)
        if not _visible_schemes_qs(request.user).filter(id=scheme.id).exists():
            return json_error('Нет доступа к этой схеме', status=403)
        scheme.delete()
        return json_ok('Схема удалена')
    except Exception as e:
        return json_error(str(e))

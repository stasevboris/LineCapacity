"""CRUD пользователей и связанных с ними профилей."""

from django.apps import apps
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType

from ..models import Organization, UserProfile, Role
from .base import (
    json_ok, json_error, parse_json_body,
    staff_required, superuser_required, require_methods,
)


# Русскоязычные подписи для штатных Django-приложений (auth, admin, ...).
APP_VERBOSE_RU = {
    'auth': 'Пользователи и группы',
    'admin': 'Администрирование',
    'contenttypes': 'Типы содержимого',
    'sessions': 'Сессии',
    'designer': 'Конструктор схем',
}


def _permission_label_ru(perm):
    """Возвращает понятное русское имя права. Стандартные Django-права типа
    'Can add log entry' автоматически переводятся в 'Может добавлять <verbose>'."""
    name = perm.name or perm.codename
    code = perm.codename
    model = perm.content_type.model_class()
    verbose = (
        getattr(model._meta, 'verbose_name', perm.content_type.model)
        if model else perm.content_type.model
    )
    base_map = {
        'add': f"Может добавлять: {verbose}",
        'change': f"Может изменять: {verbose}",
        'delete': f"Может удалять: {verbose}",
        'view': f"Может просматривать: {verbose}",
    }
    for prefix, ru in base_map.items():
        if code.startswith(prefix + '_'):
            # если name уже на кириллице — оставляем как есть.
            if any('а' <= ch.lower() <= 'я' for ch in name):
                return name
            return ru
    return name


def _serialize(u):
    org_name = ''
    if hasattr(u, 'profile') and u.profile.organization:
        org_name = u.profile.organization.name
    return {
        'id': u.id,
        'username': u.username or '',
        'email': u.email or '',
        'first_name': u.first_name or '',
        'last_name': u.last_name or '',
        'is_staff': u.is_staff,
        'is_superuser': u.is_superuser,
        'is_active': u.is_active,
        'organization': org_name,
        'phone': u.profile.phone if hasattr(u, 'profile') else '',
        'patronymic': u.profile.patronymic if hasattr(u, 'profile') else '',
        'group_ids': list(u.groups.values_list('id', flat=True)),
        'permission_ids': list(u.user_permissions.values_list('id', flat=True)),
    }


@csrf_exempt
@staff_required
def api_users_list(request):
    """Суперюзер видит всех, локальный админ — только свою организацию."""
    if request.user.is_superuser:
        users = User.objects.all().order_by('username')
    else:
        admin_org = request.user.profile.organization if hasattr(request.user, 'profile') else None
        users = (
            User.objects.filter(profile__organization=admin_org).order_by('username')
            if admin_org else User.objects.none()
        )
    return json_ok(data=[_serialize(u) for u in users])


def _build_permission_tree():
    """Группирует все Permission по: app -> model -> [perms]."""
    perms_qs = (
        Permission.objects
        .select_related('content_type')
        .order_by('content_type__app_label', 'content_type__model', 'codename')
    )
    tree = {}
    for p in perms_qs:
        ct = p.content_type
        app_key = ct.app_label
        model_key = ct.model
        app_node = tree.setdefault(app_key, {
            'app_label': app_key,
            'app_verbose': APP_VERBOSE_RU.get(app_key, app_key),
            'models': {},
        })
        try:
            model_cls = apps.get_model(app_key, model_key)
            model_verbose = str(model_cls._meta.verbose_name)
        except LookupError:
            model_verbose = model_key
        model_node = app_node['models'].setdefault(model_key, {
            'model': model_key,
            'model_verbose': model_verbose,
            'perms': [],
        })
        model_node['perms'].append({
            'id': p.id,
            'codename': p.codename,
            'name': _permission_label_ru(p),
        })

    # сериализуем dict -> list, заодно сортируем для стабильности.
    out = []
    for app in sorted(tree.values(), key=lambda a: a['app_verbose'].lower()):
        models_list = sorted(app['models'].values(), key=lambda m: m['model_verbose'].lower())
        out.append({
            'app_label': app['app_label'],
            'app_verbose': app['app_verbose'],
            'models': models_list,
        })
    return out


def _role_presets():
    """Возвращает {role: [permission_id, ...]} для пресетов ролей."""
    all_perms = list(
        Permission.objects.select_related('content_type')
        .values('id', 'codename', 'content_type__app_label', 'content_type__model')
    )

    def ids_where(predicate):
        return [p['id'] for p in all_perms if predicate(p)]

    DESIGNER = 'designer'
    SCHEME_MODELS = {'folder', 'scheme', 'schemerevision', 'scenario', 'run'}
    REF_MODELS = {'reftransformer', 'refline', 'refconsumertype'}

    superuser = [p['id'] for p in all_perms]

    # Администратор (ТЗ §2.1): управление пользователями, ролями, справочниками,
    # шаблонами сценариев — плюс вся работа со схемами/расчётами для совместимости
    # с текущим функционалом.
    # Не имеет глобально-чувствительных прав (purge_auditlog, impersonate_user)
    # и не может трогать contenttypes/sessions.
    sensitive = {'purge_auditlog', 'impersonate_user'}
    admin_ids = ids_where(lambda p: (
        p['codename'] not in sensitive
        and (
            # все designer-права, кроме чувствительных
            (p['content_type__app_label'] == DESIGNER and (
                p['content_type__model'] in SCHEME_MODELS
                or p['content_type__model'] in REF_MODELS  # справочники: полный CRUD
                or p['content_type__model'] in {'organization', 'userprofile', 'role', 'auditlog'}
            ))
            # стандартные auth: управление пользователями и группами
            or (p['content_type__app_label'] == 'auth')
        )
    ))

    # Инженер: полная работа со схемами + просмотр справочников.
    engineer_ids = ids_where(lambda p: (
        p['content_type__app_label'] == DESIGNER
        and (
            p['content_type__model'] in SCHEME_MODELS
            or (p['content_type__model'] in REF_MODELS and p['codename'].startswith('view_'))
            or (p['content_type__model'] == 'organization' and p['codename'].startswith('view_'))
        )
    ))

    # Пользователь (ТЗ §2.1): просмотр схем/результатов/отчётов без редактирования.
    viewer_extra = {'view_run_results'}
    viewer_ids = ids_where(lambda p: (
        p['content_type__app_label'] == DESIGNER
        and p['content_type__model'] in (SCHEME_MODELS | REF_MODELS | {'organization'})
        and (p['codename'].startswith('view_') or p['codename'] in viewer_extra)
    ))

    return {
        'superuser': superuser,
        'admin': admin_ids,
        'engineer': engineer_ids,
        'viewer': viewer_ids,
    }


@csrf_exempt
@staff_required
def api_permissions_list(request):
    """Список доступных прав/групп для назначения + пресеты ролей.

    Структура ответа:
        permissions: [
            {app_label, app_verbose, models: [{model, model_verbose, perms: [...]}]},
            ...
        ]
        groups: [{id, name}, ...]
        presets: {role: [perm_id, ...], ...}
    """
    return json_ok(
        permissions=_build_permission_tree(),
        groups=[{'id': g.id, 'name': g.name} for g in Group.objects.order_by('name')],
        presets=_role_presets(),
    )


def _apply_access_fields(request, user, data, *, creating: bool):
    """
    Применяет к пользователю поля доступа: is_active / is_staff / is_superuser /
    groups / user_permissions. Управлять этим может только суперюзер;
    локальный админ (is_staff) меняет только is_staff в рамках своей организации.
    """
    if request.user.is_superuser:
        if 'is_active' in data:
            user.is_active = bool(data.get('is_active', True))
        if 'is_staff' in data:
            user.is_staff = bool(data.get('is_staff', False))
        if 'is_superuser' in data:
            user.is_superuser = bool(data.get('is_superuser', False))
        elif creating:
            # роль superuser приходит из старого поля role
            if data.get('role') == 'superuser':
                user.is_superuser = True
                user.is_staff = True
        user.save()

        if 'group_ids' in data:
            ids = [int(i) for i in data.get('group_ids') or []]
            user.groups.set(Group.objects.filter(id__in=ids))
        if 'permission_ids' in data:
            ids = [int(i) for i in data.get('permission_ids') or []]
            user.user_permissions.set(Permission.objects.filter(id__in=ids))
        return

    # Локальный админ: ему позволено только переключить is_staff внутри своей
    # организации; повышать до суперюзера / выдавать произвольные права нельзя.
    if 'is_staff' in data:
        user.is_staff = bool(data.get('is_staff', False))
        user.save()


@csrf_exempt
@require_methods('POST')
@staff_required
def api_create_user(request):
    """Создание нового пользователя + профиля."""
    try:
        data = parse_json_body(request)
        login = data.get('login')
        email = data.get('email')
        password = data.get('password')
        role_name = data.get('role')
        org_id = data.get('organization_id')

        # Локальный админ не имеет права создавать пользователей в чужой организации.
        if not request.user.is_superuser:
            admin_org = request.user.profile.organization if hasattr(request.user, 'profile') else None
            if not admin_org or str(admin_org.id) != str(org_id):
                return json_error(
                    'Вы можете создавать пользователей только внутри своей организации!',
                    status=403,
                )
            # Не-суперюзер не может создавать суперпользователя.
            if role_name == 'superuser' or data.get('is_superuser'):
                return json_error(
                    'Только суперпользователь может создавать других суперпользователей.',
                    status=403,
                )

        user, created = User.objects.get_or_create(
            username=login,
            defaults={
                'email': email,
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
            },
        )
        if not created:
            return json_error(f'Пользователь {login} уже существует.')

        user.set_password(password)
        # Базовая трактовка поля role для совместимости с предыдущей формой.
        if role_name == 'admin':
            user.is_staff = True
        elif role_name == 'superuser':
            # фактическое выставление флага сделает _apply_access_fields,
            # но is_staff нужен сразу для целостности.
            user.is_staff = True
        user.save()

        org = Organization.objects.filter(id=org_id).first() if org_id else None
        UserProfile.objects.create(
            user=user,
            patronymic=data.get('patronymic', ''),
            phone=data.get('phone', ''),
            organization=org,
        )

        _apply_access_fields(request, user, data, creating=True)

        Role.objects.get_or_create(name=role_name or 'engineer')
        return json_ok(f'Пользователь {login} успешно создан!')
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('PUT')
@staff_required
def api_user_update(request, obj_id):
    try:
        user = get_object_or_404(User, id=obj_id)
        data = parse_json_body(request)

        if not request.user.is_superuser:
            admin_org = request.user.profile.organization if hasattr(request.user, 'profile') else None
            user_org = user.profile.organization if hasattr(user, 'profile') else None
            if not admin_org or admin_org.id != (user_org.id if user_org else None):
                return json_error(
                    'Можно редактировать только пользователей своей организации',
                    status=403,
                )
            # Не-суперюзер не может редактировать суперпользователя.
            if user.is_superuser:
                return json_error(
                    'Только суперпользователь может редактировать другого суперпользователя.',
                    status=403,
                )

        for key in ('username', 'email', 'first_name', 'last_name'):
            if key in data:
                setattr(user, key, data.get(key, ''))

        new_password = data.get('password')
        if new_password and request.user.is_superuser:
            user.set_password(new_password)

        user.save()

        _apply_access_fields(request, user, data, creating=False)

        if hasattr(user, 'profile'):
            profile = user.profile
            if 'phone' in data:
                profile.phone = data.get('phone', '')
            if 'patronymic' in data:
                profile.patronymic = data.get('patronymic', '')
            profile.save()

        return json_ok('Пользователь обновлён')
    except Exception as e:
        return json_error(str(e))


@csrf_exempt
@require_methods('DELETE')
@superuser_required
def api_user_delete(request, obj_id):
    try:
        user = get_object_or_404(User, id=obj_id)
        user.delete()
        return json_ok('Пользователь удалён')
    except Exception as e:
        return json_error(str(e))

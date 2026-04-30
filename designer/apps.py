from django.apps import AppConfig
from django.db.models.signals import post_migrate


class DesignerConfig(AppConfig):
    name = 'designer'
    verbose_name = "Конструктор схем"

    def ready(self):
        # Создаём/синхронизируем стандартные группы пользователей по ролям
        # каждый раз после миграций. Идемпотентно: если группа уже есть,
        # её права просто обновляются под актуальный пресет.
        post_migrate.connect(_sync_default_groups, sender=self)


def _sync_default_groups(sender, **kwargs):
    from django.contrib.auth.models import Permission, Group
    from .views.admin_users import _role_presets

    # Соответствие: Имя группы (видимое в UI) -> ключ пресета
    role_groups = {
        'Суперпользователи': 'superuser',
        'Администраторы': 'admin',
        'Инженеры': 'engineer',
        'Просмотр': 'viewer',
    }

    presets = _role_presets()
    for group_name, role in role_groups.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        ids = presets.get(role, [])
        perms = list(Permission.objects.filter(id__in=ids))
        group.permissions.set(perms)

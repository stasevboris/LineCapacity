from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import (
    SchemeRevision, RefTransformer, RefConsumerType, RefLine,
    Organization, Role, Scheme, Folder, UserProfile,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = 'user'
    verbose_name = "Профиль пользователя"
    verbose_name_plural = "Профиль пользователя"
    fields = ('patronymic', 'phone', 'organization')


class CustomUserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline,)

    list_display = ('username', 'email', 'first_name', 'last_name',
                    'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

    add_fieldsets = (
        ("Учётные данные", {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ("Личные данные", {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ("Права доступа", {
            'classes': ('wide',),
            'description': "Назначьте статусы и права новому пользователю прямо при создании.",
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            for f in ('is_superuser', 'user_permissions', 'groups'):
                if f not in readonly:
                    readonly.append(f)
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and 'is_superuser' in form.base_fields:
            form.base_fields['is_superuser'].disabled = True
        return form


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


admin.site.register(RefTransformer)
admin.site.register(RefConsumerType)
admin.site.register(RefLine)

admin.site.register(SchemeRevision)
admin.site.register(Organization)
admin.site.register(Role)
admin.site.register(Scheme)
admin.site.register(Folder)

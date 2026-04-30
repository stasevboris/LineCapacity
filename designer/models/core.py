from django.db import models
from django.contrib.auth.models import User

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название роли")

    class Meta:
        db_table = 'Roles'
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        permissions = [
            ("assign_role", "Может назначать роли пользователям"),
            ("revoke_role", "Может снимать роли с пользователей"),
        ]


class Organization(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название организации")
    address = models.TextField(blank=True, null=True, verbose_name="Адрес")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Номер телефона")
    fax = models.CharField(max_length=50, blank=True, null=True, verbose_name="Факс")

    class Meta:
        db_table = 'Organizations'
        verbose_name = "Организация"
        verbose_name_plural = "Организации"
        permissions = [
            ("manage_organization_members", "Может управлять сотрудниками организации"),
            ("view_organization_reports", "Может просматривать отчёты по организации"),
        ]


# ДОБАВИТЬ В САМЫЙ КОНЕЦ ФАЙЛА designer/models.py:

class UserProfile(models.Model):
    # Связь 1-к-1 со стандартным пользователем Django (он хранит логин, пароль, email, имя, фамилию)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Наши новые кастомные поля
    patronymic = models.CharField(max_length=150, blank=True, null=True, verbose_name="Отчество")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Номер телефона")
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='employees', verbose_name="Организация")

    class Meta:
        db_table = 'User_Profiles'
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        permissions = [
            ("change_user_organization", "Может менять организацию пользователя"),
            ("reset_user_password", "Может сбрасывать пароль пользователя"),
            ("impersonate_user", "Может входить под другим пользователем"),
        ]

class AuditLog(models.Model):
    action_type = models.CharField(max_length=100, verbose_name="Тип действия")
    entity_type = models.CharField(max_length=50, verbose_name="Тип объекта")
    entity_id = models.IntegerField(verbose_name="ID объекта")
    details = models.TextField(blank=True, null=True, verbose_name="Детали")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время действия")

    class Meta:
        db_table = 'Audit_Logs'
        verbose_name = "Запись аудита"
        verbose_name_plural = "Журнал аудита"
        permissions = [
            ("export_auditlog", "Может выгружать журнал аудита"),
            ("purge_auditlog", "Может очищать журнал аудита"),
        ]
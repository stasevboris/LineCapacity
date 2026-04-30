from django.db import models
from django.contrib.auth.models import User  # <-- Импортируем стандартного юзера Django
from .core import Organization


class Folder(models.Model):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders',
                               verbose_name="Родительская папка")
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='folders',
        verbose_name="Организация",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255, verbose_name="Имя папки")

    class Meta:
        db_table = 'Folders'
        verbose_name = "Папка"
        verbose_name_plural = "Папки"
        permissions = [
            ("move_folder", "Может перемещать папки"),
            ("manage_folder_access", "Может управлять доступом к папке"),
        ]


class Scheme(models.Model):
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='schemes', verbose_name="Папка")
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='schemes',
        verbose_name="Организация",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255, verbose_name="Название схемы")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    # Меняем AppUser на User
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_schemes', verbose_name="Создатель схемы")

    class Meta:
        db_table = 'Schemes'
        verbose_name = "Схема"
        verbose_name_plural = "Схемы"
        permissions = [
            ("publish_scheme", "Может публиковать схему"),
            ("export_scheme", "Может экспортировать схему"),
            ("share_scheme", "Может делиться схемой с другими пользователями"),
            ("clone_scheme", "Может клонировать схему"),
        ]


class SchemeRevision(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='revisions', verbose_name="Схема")
    label = models.CharField(max_length=50, verbose_name="Версия (Метка)")
    topology_data = models.JSONField(verbose_name="Топология (JSON)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    # Меняем AppUser на User
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_revisions', verbose_name="Создатель версии")

    class Meta:
        db_table = 'Scheme_Revisions'
        verbose_name = "Версия схемы"
        verbose_name_plural = "Версии схем"
        permissions = [
            ("approve_revision", "Может утверждать версию схемы"),
            ("revert_revision", "Может откатывать версию схемы"),
            ("compare_revisions", "Может сравнивать версии схемы"),
        ]
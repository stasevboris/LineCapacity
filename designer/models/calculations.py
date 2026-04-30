from django.db import models
from django.contrib.auth.models import User
from .schemes import SchemeRevision


class Scenario(models.Model):
    SEASON_CHOICES = [('Зима', 'Зима'), ('Лето', 'Лето'), ('Оба', 'Оба')]
    revision = models.ForeignKey(SchemeRevision, on_delete=models.CASCADE, related_name='scenarios')
    name = models.CharField(max_length=255, verbose_name="Название сценария")
    season = models.CharField(max_length=10, choices=SEASON_CHOICES, default='Зима', verbose_name="Сезонность")
    load_config = models.JSONField(blank=True, null=True, verbose_name="Настройки нагрузок (JSON)")
    is_template = models.BooleanField(default=False, verbose_name="Шаблон")

    class Meta:
        db_table = 'Scenarios'
        verbose_name = "Сценарий"
        verbose_name_plural = "Сценарии"
        permissions = [
            ("save_scenario_template", "Может сохранять сценарий как шаблон"),
            ("use_scenario_template", "Может использовать шаблоны сценариев"),
            ("duplicate_scenario", "Может дублировать сценарий"),
        ]


class Run(models.Model):
    STATUS_CHOICES = [('В очереди', 'В очереди'), ('Расчет', 'Расчет'), ('Завершен', 'Завершен'), ('Ошибка', 'Ошибка')]
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='runs')

    # --- ИСПРАВЛЕНО ЗДЕСЬ: AppUser заменен на User ---
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='runs', verbose_name="Пользователь")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='В очереди', verbose_name="Статус")
    results_data = models.JSONField(blank=True, null=True, verbose_name="Результаты (JSON)")
    report_path = models.CharField(max_length=512, blank=True, null=True, verbose_name="Путь к отчету")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время запуска")

    class Meta:
        db_table = 'Runs'
        verbose_name = "Расчет (Запуск)"
        verbose_name_plural = "Расчеты"
        permissions = [
            ("execute_run", "Может запускать расчёт"),
            ("cancel_run", "Может отменять расчёт"),
            ("view_run_results", "Может просматривать результаты расчёта"),
            ("export_run_report", "Может выгружать отчёт по расчёту"),
            ("rerun_run", "Может перезапускать расчёт"),
        ]
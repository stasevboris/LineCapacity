from django.db import models


class RefTransformer(models.Model):
    type_name = models.CharField(max_length=100, verbose_name="Тип трансформатора")
    nominal_power = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        verbose_name="Номинальная мощность, кВА")
    losses_no_load = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                                         verbose_name="Потери ХХ, кВт")
    losses_short_circuit = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                                               verbose_name="Потери КЗ, кВт")
    voltage_hv = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name="Номинальное напряжение ВН, кВ")
    voltage_lv = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name="Номинальное напряжение НН, кВ")
    voltage_short_circuit_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                                    verbose_name="Напряжение КЗ, %")
    pbv_stages_count = models.IntegerField(null=True, blank=True, verbose_name="Количество ступеней ПБВ")
    pbv_step_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                       verbose_name="Шаг одной ступени ПБВ")

    class Meta:
        db_table = 'Ref_Transformers'
        verbose_name = "Справочник: Трансформатор"
        verbose_name_plural = "Справочник: Трансформаторы"
        permissions = [
            ("import_reftransformer", "Может импортировать трансформаторы"),
            ("export_reftransformer", "Может экспортировать трансформаторы"),
        ]

    def __str__(self):
        return self.type_name


class RefLine(models.Model):
    # Оставили ровно те 8 эталонных полей, как на скриншоте 2
    mark = models.CharField(max_length=100, verbose_name="Марка ЛЭП")
    material = models.CharField(max_length=50, blank=True, null=True, verbose_name="Материал провода")
    insulation = models.CharField(max_length=50, blank=True, null=True, verbose_name="Материал изоляции")
    cores_count = models.IntegerField(null=True, blank=True, verbose_name="Количество жил")
    cross_section = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        verbose_name="Сечение фазного провода, мм^2")
    r_phase_ohm_km = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                         verbose_name="Сопротивление фазного провода, Ом/км")
    r_null_ohm_km = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                        verbose_name="Сопротивление нулевого провода, Ом/км")
    r_add_ohm_km = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                       verbose_name="Сопротивление доп. провода, Ом/км")

    class Meta:
        db_table = 'Ref_Lines'
        verbose_name = "Справочник: Линия"
        verbose_name_plural = "Справочник: Линии"
        permissions = [
            ("import_refline", "Может импортировать линии"),
            ("export_refline", "Может экспортировать линии"),
        ]

    def __str__(self):
        return self.mark


class RefConsumerType(models.Model):
    SUPPLY_CHOICES = [('Однофазный', 'Однофазный'), ('Трёхфазный', 'Трёхфазный')]
    CALC_CHOICES = [('Типовые', 'Типовые'), ('Индивидуальные', 'Индивидуальные')]

    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Тип потребителя")
    usage_character = models.CharField(max_length=255, blank=True, null=True,
                                       verbose_name="Характер электропотребления")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адрес потребителя")
    additional_data = models.CharField(max_length=255, blank=True, null=True,
                                       verbose_name="Дополнительные данные потребителя")

    # Поле label_on_scheme (Надпись на схеме) УДАЛЕНО!

    supply_type = models.CharField(max_length=20, choices=SUPPLY_CHOICES, blank=True, null=True,
                                   verbose_name="Питание потребителя")
    phase_number = models.IntegerField(null=True, blank=True, verbose_name="Номер фазы")
    calc_method = models.CharField(max_length=20, choices=CALC_CHOICES, blank=True, null=True,
                                   verbose_name="Параметры электропотребления (тип)")
    yearly_consumption_kwh = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                                 verbose_name="Годовое потребление, кВт*ч")
    calculated_active_power_kw = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                                     verbose_name="Расчётная активная мощность, кВт")
    cos_phi = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True,
                                  verbose_name="Коэффициент мощности (косинус фи)")

    class Meta:
        db_table = 'Ref_Consumer_Types'
        verbose_name = "Справочник: Типовой потребитель"
        verbose_name_plural = "Справочник: Типовые потребители"
        permissions = [
            ("import_refconsumertype", "Может импортировать типовых потребителей"),
            ("export_refconsumertype", "Может экспортировать типовых потребителей"),
        ]

    def __str__(self):
        return self.name or "Неизвестный потребитель"
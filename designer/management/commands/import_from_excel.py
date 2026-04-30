import pandas as pd
import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from designer.models import RefLine, RefTransformer


class Command(BaseCommand):
    help = 'Импорт данных из Excel файлов в справочники'

    def add_arguments(self, parser):
        parser.add_argument('--lines', type=str, required=True,
                            help='Путь к файлу Lines_VL+KL.xlsx')
        parser.add_argument('--transformers', type=str, required=True,
                            help='Путь к файлу Transformers.xlsx')

    def handle(self, *args, **options):
        self.stdout.write('Начинаем импорт справочников...')

        # Импортируем линии
        self.stdout.write('\n' + '=' * 50)
        self.import_lines(options['lines'])

        # Импортируем трансформаторы
        self.stdout.write('\n' + '=' * 50)
        self.import_transformers(options['transformers'])

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Импорт успешно завершен!'))

    # = ИМПОРТ ЛИНИЙ
    def import_lines(self, file_path):
        """Импорт справочника линий из Excel"""
        self.stdout.write(f'Загрузка линий из {file_path}...')

        try:
            df = pd.read_excel(file_path, sheet_name=0, header=0)
            self.stdout.write(f'Найдено строк в Excel: {len(df)}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка чтения файла: {e}'))
            return

        count = 0
        errors = 0

        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Получаем тип линии (первая колонка)
                    line_type = str(row.iloc[0]).strip()
                    if not line_type or line_type == 'nan':
                        continue

                    # Получаем сопротивления (остальные колонки)
                    r_phase = self.safe_decimal(row.iloc[1]) if len(row) > 1 else None
                    r_null = self.safe_decimal(row.iloc[2]) if len(row) > 2 else None
                    r_add = self.safe_decimal(row.iloc[3]) if len(row) > 3 else None

                    # Определяем все параметры линии по ее типу
                    params = self.parse_line_parameters(line_type)

                    # Создаем или обновляем запись
                    obj, created = RefLine.objects.update_or_create(
                        mark=line_type,
                        defaults={
                            'mark': line_type,
                            'material': params['material'],
                            'insulation': params['insulation'],
                            'cores_count': params['cores_count'],
                            'cross_section': params['cross_section'],
                            'r_phase_ohm_km': r_phase,
                            'r_null_ohm_km': r_null,
                            'r_add_ohm_km': r_add,
                        }
                    )
                    count += 1

                    if count % 200 == 0:
                        self.stdout.write(f'  Обработано {count} линий...')

                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.WARNING(f'  Ошибка в строке {index + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Импортировано линий: {count} (ошибок: {errors})'))

    def parse_line_parameters(self, line_type):
        """Парсит тип линии и определяет все параметры"""
        params = {
            'material': None,
            'insulation': None,
            'cores_count': None,
            'cross_section': None,
        }

        if not isinstance(line_type, str):
            return params

        line_type_clean = line_type.strip()
        line_type_upper = line_type_clean.upper()
        line_type_lower = line_type_clean.lower()

        #  МАТЕРИАЛ
        # Алюминий: начинается с А/АА/АС/САП/САСП/СИП и др.
        if re.match(r'^[АA]', line_type_upper) or \
           line_type_upper.startswith('СИП') or \
           any(line_type_upper.startswith(prefix) for prefix in ['САП', 'САСП', 'АА', 'АС']):
            params['material'] = 'Алюминий'
        elif any(ind in line_type_upper for ind in ['ВВГ', 'ПВ', 'КГ', 'СБ', 'ВБ', 'КРПТ', 'АПВ']):
            params['material'] = 'Медь'
        else:
            params['material'] = 'Алюминий'  # по умолчанию

        # ИЗОЛЯЦИЯ
        if 'СШ' in line_type_upper:
            params['insulation'] = 'Сшитый полиэтилен'
        elif 'НГ' in line_type_lower:
            params['insulation'] = 'ПВХ (негорючий)'
        elif 'Т' in line_type_upper and any(p in line_type_upper for p in ['САПТ', 'САСПТ', 'СИПТ']):
            params['insulation'] = 'Термопласт'
        elif 'В' in line_type_upper and any(p in line_type_upper for p in ['ВВГ', 'АВВГ', 'АВБ']):
            params['insulation'] = 'ПВХ'
        elif 'П' in line_type_upper and any(p in line_type_upper for p in ['ПВ', 'АПВ']):
            params['insulation'] = 'ПВХ'
        elif any(p in line_type_upper for p in ['КГ', 'КРПТ']):
            params['insulation'] = 'Резина'
        elif any(p in line_type_upper for p in ['ААБ', 'АСБ']):
            params['insulation'] = 'Бумажная пропитанная'
        elif re.match(r'^[АA]\s*$', line_type_upper) or \
             (re.match(r'^[АA][СC]?\s*$', line_type_upper) and not any(x in line_type_upper for x in ['АВ', 'ААБ', 'АСБ'])):
            params['insulation'] = 'Голый провод'
        else:
            # Fallback: как в C++
            if 'В' in line_type_upper:
                params['insulation'] = 'ПВХ'
            elif 'П' in line_type_upper:
                params['insulation'] = 'Сшитый полиэтилен'
            else:
                params['insulation'] = 'Не определена'

        # ЖИЛЫ И СЕЧЕНИЕ
        # Шаблон: цифра + (х|x|×) + число (с , или .), возможно с `+` дальше
        # Пример: "3х120", "3x120", "3×120", "3х120+1х25"
        pattern = r'(\d+)\s*[хx×]\s*(\d+[,.]?\d*)'
        matches = re.findall(pattern, line_type_clean)

        if matches:
            # Берём первую группу — это фазные жилы
            cores_str, section_str = matches[0]
            try:
                params['cores_count'] = int(cores_str)
                # Очищаем section_str от возможных символов после числа (например, "+")
                section_clean = re.match(r'^[\d,.]+', section_str)
                if section_clean:
                    section_val = section_clean.group().replace(',', '.')
                    params['cross_section'] = Decimal(section_val)
            except Exception:
                pass  # оставляем None
        else:
            # Попытка: "А 16", "АС 25"
            simple_match = re.search(r'[АA][СC]?\s+(\d+[,.]?\d*)', line_type_clean)
            if simple_match:
                try:
                    section_val = simple_match.group(1).replace(',', '.')
                    params['cross_section'] = Decimal(section_val)
                    params['cores_count'] = 1
                except:
                    pass

        return params

    # ИМПОРТ ТРАНСФОРМАТОРОВ
    def import_transformers(self, file_path):
        """Импорт справочника трансформаторов из Excel"""
        self.stdout.write(f'Загрузка трансформаторов из {file_path}...')

        try:
            df = pd.read_excel(file_path, sheet_name=0, header=0)
            self.stdout.write(f'Найдено строк в Excel: {len(df)}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка чтения файла: {e}'))
            return

        count = 0
        errors = 0

        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Проверяем, что строка не пустая
                    if pd.isna(row.iloc[0]):
                        continue

                    type_name = str(row.iloc[0]).strip()

                    # Создаем или обновляем запись
                    obj, created = RefTransformer.objects.update_or_create(
                        type_name=type_name,
                        defaults={
                            'type_name': type_name,
                            'nominal_power': self.safe_decimal(row.iloc[1]),  # S, кВА
                            'losses_no_load': self.safe_decimal(row.iloc[2]),  # Pxx, кВт
                            'losses_short_circuit': self.safe_decimal(row.iloc[3]),  # Ркз, кВт
                            'voltage_hv': self.safe_decimal(row.iloc[4]),  # Uвн, кВ
                            'voltage_lv': self.safe_decimal(row.iloc[5]),  # Uнн, кВ
                            'voltage_short_circuit_pct': self.safe_decimal(row.iloc[6]),  # Uк, %
                            'pbv_stages_count': self.safe_int(row.iloc[7]),  # Кол-во ступеней ПБВ
                            'pbv_step_pct': self.safe_decimal(row.iloc[8]),  # Шаг ступени ПБВ, %
                        }
                    )
                    count += 1

                    if count % 50 == 0:
                        self.stdout.write(f'  Обработано {count} трансформаторов...')

                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.WARNING(f'  Ошибка в строке {index + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Импортировано трансформаторов: {count} (ошибок: {errors})'))

    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    def safe_decimal(self, value):
        """Безопасное преобразование в Decimal"""
        if pd.isna(value):
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
                if not value:
                    return None
            return Decimal(str(value))
        except Exception:
            return None

    def safe_int(self, value):
        """Безопасное преобразование в int"""
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except Exception:
            return None

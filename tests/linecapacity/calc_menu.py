from __future__ import annotations

import time
from pathlib import Path

LOADS = "Нагрузки"
USE = "Потребление"
AIR = "Температуры"
VOLTAGES = "Напряжения"
EXTRA = "Дополнительно"
HOMES = "Типовые параметры нагрузки бытовых потребителей"
LIGHTS = "Типовые параметры нагрузки наружного освещения"
YEAR_HOMES = "Типовые параметры годового электропотребления бытовых потребителей"
YEAR_LIGHTS = "Типовые параметры годового электропотребления наружного освещения"
WITHOUT = "Потребители без КИЭ"
WITH = "Потребители с КИЭ"
COLD = "Зимний период"
WARM = "Летний период"
MINIMAL = "Минимальные нагрузки"

SETTINGS_FIELDS = {
    "home_winter_kw": (LOADS, (HOMES, COLD, WITHOUT), 0),
    "home_winter_cos": (LOADS, (HOMES, COLD, WITHOUT), 1),
    "electric_home_winter_kw": (LOADS, (HOMES, COLD, WITH), 0),
    "electric_home_winter_cos": (LOADS, (HOMES, COLD, WITH), 1),
    "home_summer_kw": (LOADS, (HOMES, WARM, WITHOUT), 0),
    "home_summer_cos": (LOADS, (HOMES, WARM, WITHOUT), 1),
    "electric_home_summer_kw": (LOADS, (HOMES, WARM, WITH), 0),
    "electric_home_summer_cos": (LOADS, (HOMES, WARM, WITH), 1),
    "home_minimal_kw": (LOADS, (HOMES, MINIMAL, WITHOUT), 0),
    "electric_home_minimal_kw": (LOADS, (HOMES, MINIMAL, WITH), 0),
    "extra_load_kw": (LOADS, ("Утяжеление типовой нагрузки ",), 0),
    "street_light_winter_kw": (LOADS, (LIGHTS, COLD), 0),
    "street_light_winter_cos": (LOADS, (LIGHTS, COLD), 1),
    "street_light_summer_kw": (LOADS, (LIGHTS, WARM), 0),
    "street_light_summer_cos": (LOADS, (LIGHTS, WARM), 1),
    "home_annual_kwh": (USE, (YEAR_HOMES, WITHOUT), 0),
    "electric_home_annual_kwh": (USE, (YEAR_HOMES, WITH), 0),
    "street_light_annual_kwh": (USE, (YEAR_LIGHTS,), 0),
    "line_air_summer": (AIR, ("Максимальные значения температуры  воздуха",), 0),
    "line_air_winter": (AIR, ("Максимальные значения температуры  воздуха",), 1),
    "transformer_air_summer": (AIR, ("Средние значения температуры  воздуха",), 0),
    "transformer_air_winter": (AIR, ("Средние значения температуры  воздуха",), 1),
    "voltage_rated": (VOLTAGES, ("Напряжение на потребителе",), 0),
    "voltage_max": (VOLTAGES, ("Напряжение на потребителе",), 1),
    "voltage_min": (VOLTAGES, ("Напряжение на потребителе",), 2),
    "high_voltage_kv": (VOLTAGES, (), 0),
    "voltage_loss_limit": (VOLTAGES, (), 1),
    "contact_resistance_ohm": (EXTRA, (), 0),
}
MIRRORS = {"home_summer_cos": ((LOADS, (HOMES, MINIMAL, WITHOUT), 1),),
           "electric_home_summer_cos": ((LOADS, (HOMES, MINIMAL, WITH), 1),)}
FLAGS = {"extra_load_enabled": (0, "Включить утяжеление"),
         "scale_by_annual": (1, "Разрешить корректировать типовые нагрузки по текущим значениям годового потребления")}
MENU_TYPICAL = "Расчёт->Присвоить всем потребителям типовые значения нагрузки (F6)"
MENU_INDIVIDUAL = "Расчёт->Присвоить всем потребителям индивидуальные значения нагрузки"
MENU_EXCEL = "Расчёт->Импорт индивидуальных нагрузок потребителей из файла Excel"
MENU_METER = "Расчёт->Распределение нагрузок потребителей по данным с балансного прибора"
MENU_SETTINGS = "Расчёт->Настройки"
ALLOWED_BUTTON = "Рассчитать допустимую мощность потребителя"


def own_children(parent, cls: str):
    return [item for item in parent.children() if item.class_name() == cls and item.parent().handle == parent.handle]


def child(parent, cls: str, text: str):
    found = [item for item in own_children(parent, cls) if item.window_text() == text]
    if not found:
        raise LookupError(f"{cls} «{text}» не найден")
    return found[0]


def edit_in(win, tab: str, groups: tuple[str, ...], index: int):
    holder = [item for item in win.descendants() if item.class_name() == "TTabSheet" and item.window_text() == tab][0]
    for caption in groups:
        holder = child(holder, "TGroupBox", caption)
    edits = sorted(own_children(holder, "TEdit"), key=lambda item: (item.rectangle().top, item.rectangle().left))
    return edits[index]


def read_message(program) -> str:
    deadline = time.time() + 15
    while time.time() < deadline:
        for found in program.app.windows():
            if found.is_visible() and found.class_name() == "TMessageForm":
                time.sleep(0.3)
                text = program.message_text(found)
                found.close()
                time.sleep(0.5)
                return text
        time.sleep(0.3)
    return ""


def load_kind(program, typical: bool) -> str:
    program.menu(MENU_TYPICAL if typical else MENU_INDIVIDUAL)
    program.confirm()
    return read_message(program)


def tabs_of(win):
    from pywinauto.controls.common_controls import TabControlWrapper
    page = [item for item in win.descendants() if item.class_name() == "TPageControl"][0]
    return TabControlWrapper(page.handle)


def open_every_tab(win) -> None:
    tabs = tabs_of(win)
    for index in [*range(1, tabs.tab_count()), 0]:
        tabs.select(index)
        time.sleep(0.4)


def settings(program, values: dict) -> None:
    program.menu(MENU_SETTINGS)
    win = program.window("TFormCalcSett")
    open_every_tab(win)
    for key, value in values.items():
        if key in FLAGS:
            tab, caption = FLAGS[key]
            tabs_of(win).select(tab)
            time.sleep(0.4)
            box = [item for item in win.descendants() if item.class_name() == "TCheckBox"
                   and item.window_text() == caption][0]
            if bool(box.get_check_state()) != value:
                box.click_input()
                time.sleep(0.3)
            continue
        text = number(value)
        program.set_text(edit_in(win, *SETTINGS_FIELDS[key]), text)
        for mirror in MIRRORS.get(key, ()):
            program.set_text(edit_in(win, *mirror), text)
    [item for item in win.children() if item.window_text() == "Сохранить"][0].click_input()
    time.sleep(0.8)
    program.confirm()
    time.sleep(0.6)


def number(value) -> str:
    text = format(float(value), ".15g")
    return text.replace(".", ",")


def meter(program, p_kw: float, q_kvar: float, month: int, by_annual: bool) -> str:
    program.menu(MENU_METER)
    win = program.window("TFormBalans")
    group = child(win, "TGroupBox", "Мощность по балансному прибору учёта")
    edits = sorted((item for item in group.children() if item.class_name() == "TEdit"),
                   key=lambda item: item.rectangle().left)
    program.set_text(edits[0], number(p_kw))
    program.set_text(edits[1], number(q_kvar))
    months = [item for item in group.children() if item.class_name() == "TComboBox"][0]
    program.choose(months, month - 1)
    box = [item for item in win.children() if item.class_name() == "TCheckBox"][0]
    if bool(box.get_check_state()) != by_annual:
        box.click()
        time.sleep(0.2)
    [item for item in win.children() if item.window_text() == "Распределить и сохранить нагрузки"][0].click_input()
    time.sleep(0.8)
    return read_message(program)


def excel(program, path: Path, cos_phi: float, air: float, timeout: float = 90) -> str:
    import pywinauto.keyboard as keyboard
    program.menu(MENU_EXCEL)
    win = program.window("TFormExcelImport")
    [item for item in win.children() if item.window_text() == "Выбрать файл Excel"][0].click_input()
    time.sleep(1.2)
    dialog = program.app.window(title_re=".*[Оо]ткр.*")
    dialog.wait("visible", timeout=10)
    dialog.child_window(class_name="Edit", found_index=0).set_edit_text(str(path))
    time.sleep(0.4)
    dialog.set_focus()
    keyboard.send_keys("{ENTER}")
    time.sleep(1.5)
    [item for item in win.children() if item.window_text() == "Загрузить данные из файла"][0].click_input()
    save = [item for item in win.children() if item.window_text() == "Сохранить выбранные нагрузки"][0]
    deadline = time.time() + timeout
    while time.time() < deadline and not save.is_enabled():
        time.sleep(0.5)
    time.sleep(1.0)
    edits = sorted((item for item in win.children() if item.class_name() == "TEdit"),
                   key=lambda item: item.rectangle().top)
    program.set_text(edits[0], number(cos_phi))
    program.set_text(edits[1], number(air))
    save.click_input()
    time.sleep(1.0)
    return "\n".join(read_messages(program))


def read_messages(program, timeout: float = 20) -> list[str]:
    texts: list[str] = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        for found in program.app.windows():
            if not found.is_visible():
                continue
            if found.class_name() == "#32770":
                time.sleep(0.3)
                texts.append(" ".join(item.window_text() for item in found.children()
                                      if item.class_name() == "Static" and item.window_text()))
                [item for item in found.children() if item.class_name() == "Button"][0].click()
                time.sleep(0.5)
                break
            if found.class_name() == "TMessageForm":
                time.sleep(0.3)
                texts.append(program.message_text(found))
                found.close()
                time.sleep(0.5)
                return texts
        else:
            time.sleep(0.3)
    return texts


def allowed(program, consumer, timeout: float = 120) -> tuple[list[str], list[str]]:
    from tests.linecapacity.driver import report_rows
    win = program.window(program.open_object("consumer", consumer))
    time.sleep(0.4)
    [item for item in win.children() if item.window_text() == ALLOWED_BUTTON][0].click_input()
    deadline = time.time() + timeout
    rows: list[str] = []
    while time.time() < deadline:
        found = [item for item in program.app.windows() if item.is_visible() and item.class_name() == "TFormRes"]
        if found:
            time.sleep(0.6)
            rows = report_rows(found[0])
            found[0].close()
            time.sleep(0.5)
            break
        messages = [item for item in program.app.windows() if item.is_visible()
                    and item.class_name() == "TMessageForm"]
        if messages:
            rows = ["ошибка: " + program.message_text(messages[0])]
            messages[0].close()
            break
        time.sleep(0.5)
    memo = [item for item in win.descendants() if item.class_name() == "TMemo" and item.is_visible()]
    text = memo[0].window_text() if memo else ""
    win.close()
    time.sleep(0.8)
    lines = text.replace("\r\n", "\n").split("\n")
    return rows, lines[:-1] if lines and lines[-1] == "" else lines

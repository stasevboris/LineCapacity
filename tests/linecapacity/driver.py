from __future__ import annotations

import os
import subprocess
import time
import warnings
from pathlib import Path

from voltplan.exchange.cir import format_number

MENU_ITEMS = {
    "outgoing": "Отходящую от ТП ЛЭП",
    "span": "ЛЭП между опорами",
    "branch_line": "ЛЭП между опорами",
    "branch_consumer": "ЛЭП к потребителю",
}
CATEGORY_TO_DIALOG = {0: (0, 0), 1: (0, 1), 2: (1, None), 3: (2, None)}
PERIODS = {0: "Летний период", 1: "Зимний период", 2: "Зимний и летний периоды"}
SEASON_BUTTONS = ("Летний период", "Зимний период")
REPORT_ITEM = "Основные результаты последнего расчёта"
DIVIDER = "---------------------------"
COPY_ATTEMPTS = 4
KEY_C = 0x43


def find_exe() -> Path | None:
    value = os.environ.get("LINECAPACITY_EXE", "").strip()
    if value and Path(value).is_file():
        return Path(value)
    return None


def number(value: float) -> str:
    return format_number(value)


class CalcRefused(Exception):
    def __init__(self, image, text: str) -> None:
        super().__init__(text)
        self.image = image
        self.text = text


def press_copy() -> None:
    import win32api
    import win32con
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(KEY_C, 0, 0, 0)
    win32api.keybd_event(KEY_C, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


def report_rows(window) -> list[str]:
    text = [c for c in window.descendants() if c.class_name() == "TRichEdit"][0].window_text()
    rows = text.replace("\r\n", "\n").split("\n")
    return rows[:-1] if rows and rows[-1] == "" else rows


class LineCapacity:
    def __init__(self, exe: Path) -> None:
        self.exe = Path(exe)
        self.app = None
        self.main = None

    def __enter__(self) -> LineCapacity:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def kill(self) -> None:
        subprocess.run(["taskkill", "/F", "/IM", self.exe.name], capture_output=True)
        time.sleep(0.6)

    def start(self) -> None:
        warnings.filterwarnings("ignore")
        from pywinauto.application import Application
        self.kill()
        self.app = Application(backend="win32").start(str(self.exe), work_dir=str(self.exe.parent))
        time.sleep(3.5)
        self.main = self.app.window(title_re="LineCapacity v1.*")
        self.main.wait("visible ready", timeout=25)
        self.main.maximize()
        time.sleep(0.6)

    def close(self) -> None:
        try:
            if self.app is not None:
                self.app.kill()
        except Exception:
            pass
        self.kill()

    def window(self, cls: str, timeout: float = 10):
        win = self.app.window(class_name=cls)
        win.wait("visible ready", timeout=timeout)
        return win

    def controls(self, win, cls: str):
        found = [c for c in win.descendants() if c.class_name() == cls and c.is_visible()]
        return sorted(found, key=lambda c: (c.rectangle().left, c.rectangle().top))

    def rows(self, win, cls: str):
        found = [c for c in win.descendants() if c.class_name() == cls]
        return sorted(found, key=lambda c: (c.rectangle().top, c.rectangle().left))

    def press(self, cls: str, caption: str, pause: float = 1.1) -> None:
        win = self.window(cls)
        [b for b in win.children() if b.window_text() == caption][0].click_input()
        time.sleep(pause)

    def confirm(self) -> None:
        self.press("TFormDel", "Да", 1.2)

    def client_origin(self) -> tuple[int, int]:
        rect = self.main.client_area_rect()
        return rect.left, rect.top

    def click(self, x: int, y: int, pause: float = 0.9) -> None:
        import pywinauto.mouse as mouse
        left, top = self.client_origin()
        mouse.click(coords=(left + x, top + y))
        time.sleep(pause)

    def click_point(self, x: int, y: int) -> None:
        self.main.set_focus()
        self.click(x + 3, y + 6)

    def menu(self, path: str, pause: float = 1.3) -> None:
        self.main.set_focus()
        time.sleep(0.2)
        self.main.menu_select(path)
        time.sleep(pause)

    def set_text(self, control, value: str) -> None:
        import win32con
        import win32gui
        win32gui.SendMessage(control.handle, win32con.WM_SETTEXT, 0, value)
        time.sleep(0.05)

    def choose(self, control, index: int, notify: bool = False) -> None:
        import win32con
        import win32gui
        win32gui.SendMessage(control.handle, win32con.CB_SETCURSEL, index, 0)
        if notify:
            parent = win32gui.GetParent(control.handle)
            code = (win32con.CBN_SELCHANGE << 16) | (win32gui.GetDlgCtrlID(control.handle) & 0xFFFF)
            win32gui.SendMessage(parent, win32con.WM_COMMAND, code, control.handle)
        time.sleep(0.05)

    def fill_transformer(self, data: dict) -> None:
        win = self.window("TFormParamTrans")
        edits = self.controls(win, "TEdit")
        left = [e for e in edits if e.rectangle().left == edits[0].rectangle().left]
        right = [e for e in edits if e.rectangle().left != edits[0].rectangle().left]
        left.sort(key=lambda e: e.rectangle().top)
        right.sort(key=lambda e: e.rectangle().top)
        places = dict(zip(("type_name", "label", "sn_kva", "px_kw", "pk_kw"), left, strict=True))
        places.update(zip(("unn_kv", "uvn_kv", "uk_percent"), right, strict=True))
        for name, control in places.items():
            if name in data:
                self.set_text(control, data[name] if name in ("type_name", "label") else number(data[name]))
        if "pbv_step" in data:
            self.choose(self.rows(win, "TComboBox")[0], data["pbv_step"] + 2)
        self.press("TFormParamTrans", "Сохранить", 1.2)

    def fill_line(self, data: dict, to_single: bool = False) -> None:
        win = self.window("TFormParamLine")
        edits = sorted(self.controls(win, "TEdit"), key=lambda e: (e.rectangle().top, e.rectangle().left))
        type_edit, label_edit, length_edit = edits[0], edits[1], edits[2]
        combos = sorted([c for c in win.descendants() if c.class_name() == "TComboBox"],
                        key=lambda c: c.rectangle().left)
        phase_combo, phase_no_combo = combos[0], combos[1]
        if "phase_mode" in data and phase_combo.is_enabled() and phase_combo.selected_index() != data["phase_mode"]:
            self.choose(phase_combo, data["phase_mode"], notify=True)
            time.sleep(0.3)
        for name, control in (("type_name", type_edit), ("label", label_edit)):
            if name in data:
                self.set_text(control, data[name])
        if "length_m" in data:
            self.set_text(length_edit, number(data["length_m"]))
        border = label_edit.rectangle().top + 60
        resist = sorted([c for c in win.descendants() if c.class_name() == "TEdit" and c.rectangle().top > border],
                        key=lambda e: e.rectangle().top)
        if phase_combo.selected_index() == 0:
            if "r_phase_ohm_per_km" in data:
                self.set_text(resist[0], number(data["r_phase_ohm_per_km"]))
            if "r_neutral_ohm_per_km" in data:
                self.set_text(resist[1], number(data["r_neutral_ohm_per_km"]))
        else:
            if "r_single_phase_ohm_per_km" in data:
                self.set_text(resist[0], number(data["r_single_phase_ohm_per_km"]))
            if "phase_no" in data:
                self.choose(phase_no_combo, data["phase_no"] - 1)
        if to_single:
            box = [c for c in win.descendants() if c.class_name() == "TCheckBox"][0]
            if box.is_visible():
                box.click_input()
                time.sleep(0.2)
        self.press("TFormParamLine", "Сохранить", 1.2)

    def fill_pole(self, data: dict) -> None:
        win = self.window("TFormParamColumn")
        if "label" in data:
            self.set_text(self.controls(win, "TEdit")[0], data["label"])
        if "branch_count" in data:
            self.choose([c for c in win.descendants() if c.class_name() == "TComboBox"][0], data["branch_count"])
        self.press("TFormParamColumn", "Сохранить", 1.2)

    def fill_consumer(self, data: dict) -> None:
        win = self.window("TFormConsummer")
        top_edits = sorted([c for c in win.children() if c.class_name() == "TEdit"], key=lambda e: e.rectangle().top)
        group = [c for c in win.children() if c.class_name() == "TGroupBox"][0]
        inner = [c for c in group.children() if c.class_name() == "TEdit"]
        middle = group.rectangle().left + 100
        small = sorted([e for e in inner if e.rectangle().left < middle], key=lambda e: e.rectangle().top)
        places = {"address": top_edits[0], "type_text": top_edits[1], "label": top_edits[2]}
        numbers = {"p_kw": small[0], "cos_phi": small[1],
                   "annual_kwh": [e for e in inner if e.rectangle().left > middle][0]}
        radios = {c.window_text(): c for c in group.children() if c.class_name() == "TRadioButton"}
        combos = sorted([c for c in group.children() if c.class_name() == "TComboBox"], key=lambda c: c.rectangle().top)
        for name, control in places.items():
            if name in data:
                self.set_text(control, data[name])
        if "load_type" in data:
            radios["индивидуальные" if data["load_type"] == 1 else "типовые"].click_input()
            time.sleep(0.3)
        for name, control in numbers.items():
            if name in data:
                self.set_text(control, number(data[name]))
        if data.get("category") is not None:
            kind, cie = CATEGORY_TO_DIALOG[int(data["category"])]
            self.choose(combos[0], kind, notify=True)
            time.sleep(0.2)
            if cie is not None:
                self.choose(combos[1], cie)
        self.press("TFormConsummer", "Сохранить", 1.3)

    def new_scheme(self, action: dict) -> None:
        self.menu("Файл->Новая схема", 1.0)
        self.confirm()
        self.fill_transformer(action.get("transformer", {}))
        self.fill_line(action.get("line", {}))
        self.fill_pole(action.get("pole", {}))

    def press_part(self, cls: str, part: str, pause: float = 1.0) -> None:
        win = self.window(cls)
        [b for b in win.children() if part in b.window_text() and b.class_name() == "TButton"][0].click_input()
        time.sleep(pause)

    def open_object(self, kind: str, obj) -> str:
        self.main.set_focus()
        if kind == "transformer":
            self.click(obj.x, obj.y + 40, 1.2)
            return "TFormParamTrans"
        if kind == "pole":
            self.click(obj.x + 5, obj.y, 1.2)
            return "TFormParamColumn"
        if kind == "consumer":
            self.click(obj.x, obj.y + 5, 1.2)
            return "TFormConsummer"
        if obj.vertical == 1:
            self.click(obj.x, (obj.y + obj.end_y) // 2, 1.2)
        else:
            self.click((obj.x + obj.end_x) // 2, obj.y, 1.2)
        return "TFormParamLine"

    def add_branch(self, pole) -> None:
        self.open_object("pole", pole)
        self.press("TFormParamColumn", "Добавить ответвление", 1.0)
        self.confirm()

    def delete(self, kind: str, obj) -> None:
        self.press_part(self.open_object(kind, obj), "Удалить", 1.0)
        self.confirm()

    def update(self, kind: str, obj, fields: dict) -> None:
        self.open_object(kind, obj)
        fill = {"transformer": self.fill_transformer, "line": self.fill_line, "pole": self.fill_pole,
                "consumer": self.fill_consumer}[kind]
        fill(fields)

    def undo(self) -> None:
        import pywinauto.keyboard as keyboard
        import pywinauto.mouse as mouse
        self.main.set_focus()
        time.sleep(0.3)
        rect = self.main.client_area_rect()
        mouse.right_click(coords=(rect.right - 60, rect.bottom - 60))
        time.sleep(1.0)
        keyboard.send_keys("{UP}")
        time.sleep(0.3)
        keyboard.send_keys("{ENTER}")
        time.sleep(1.5)

    def add_item(self, needle) -> str:
        add = [item for item in self.main.menu().items() if item.text() == "Добавить"][0]
        return next(item.text() for item in add.sub_menu().items() if needle(item.text().lower()))

    def perform(self, action: dict, before) -> None:
        kind = action["kind"]
        if kind == "new":
            self.new_scheme(action)
        elif kind == "undo":
            self.undo()
        elif kind == "click":
            self.click_point(action["point"]["x"], action["point"]["y"])
        elif kind == "add_branch":
            self.add_branch(before.poles[action["index"]])
        elif kind in ("delete", "update"):
            target = action["target"]
            obj = before.transformer if target == "transformer" else getattr(before, f"{target}s")[action["index"]]
            if kind == "delete":
                self.delete(target, obj)
            else:
                self.update(target, obj, action.get("fields", {}))
        elif kind == "pole":
            self.click_point(action["point"]["x"], action["point"]["y"])
            self.menu("Добавить->" + self.add_item(lambda text: "опор" in text and "между" not in text))
            self.fill_pole(action.get("pole", {}))
        elif kind == "consumer":
            self.click_point(action["point"]["x"], action["point"]["y"])
            self.menu("Добавить->" + self.add_item(lambda text: text.startswith("потреб")))
            self.fill_consumer(action.get("consumer", {}))
        else:
            if kind != "outgoing":
                self.click_point(action["point"]["x"], action["point"]["y"])
            self.menu("Добавить->" + MENU_ITEMS[kind])
            self.fill_line(action.get("line", {}), to_single=action.get("to_single", False))
            if kind == "branch_consumer":
                self.fill_consumer(action.get("consumer", {}))
            else:
                self.fill_pole(action.get("pole", {}))

    def message_text(self, window) -> str:
        import win32clipboard
        for attempt in range(COPY_ATTEMPTS):
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
            if attempt:
                window.click_input(coords=(12, 12))
            window.set_focus()
            time.sleep(0.3 + 0.3 * attempt)
            press_copy()
            time.sleep(0.4 + 0.3 * attempt)
            win32clipboard.OpenClipboard()
            try:
                data = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
            except TypeError:
                data = b""
            finally:
                win32clipboard.CloseClipboard()
            text = data.rstrip(b"\x00").decode("cp1251")
            parts = [part.strip() for part in text.split(DIVIDER) if part.strip()]
            if len(parts) > 2:
                return parts[1]
        return ""

    def menu_enabled(self, top: str, prefix: str) -> bool:
        for item in self.main.menu().items():
            if item.text().replace("&", "") == top:
                return any(sub.text().replace("&", "").startswith(prefix) and sub.is_enabled()
                           for sub in item.sub_menu().items())
        return False

    def calculated(self) -> bool:
        shown = [c.window_text() for c in self.main.descendants()
                 if c.class_name() == "TRadioButton" and c.is_visible() and c.is_enabled()]
        return any(text in SEASON_BUTTONS for text in shown) and self.menu_enabled("Расчёт", "Запуск расчёта")

    def show_report(self) -> tuple[str, list[str] | str | None]:
        if not self.menu_enabled("Расчёт", REPORT_ITEM):
            return "недоступно", None
        self.menu("Расчёт->" + REPORT_ITEM, 1.5)
        for found in self.app.windows():
            if found.is_visible() and found.class_name() == "TMessageForm":
                text = self.message_text(found)
                found.close()
                time.sleep(0.5)
                return "сообщение", text
            if found.is_visible() and found.class_name() == "TFormRes":
                rows = report_rows(found)
                found.close()
                time.sleep(0.5)
                return "итоги", rows
        return "нет окна", None

    def close_report(self) -> None:
        for window in self.app.windows():
            if window.is_visible() and window.class_name() == "TFormRes":
                window.close()
                time.sleep(0.5)

    def calculate(self, period: int = 2, min_load: bool = True, timeout: float = 120,
                  report: bool = True) -> list[str]:
        import pywinauto.keyboard as keyboard
        self.main.set_focus()
        keyboard.send_keys("{F7}")
        win = self.window("TFormCalcType")
        radios = {c.window_text(): c for c in win.children() if c.class_name() == "TRadioButton"}
        radios[PERIODS[period]].click_input()
        boxes = [c for c in win.children() if c.class_name() == "TCheckBox"]
        if boxes and bool(boxes[0].get_check_state()) != min_load:
            boxes[0].click_input()
        [b for b in win.children() if b.window_text() == "Запустить расчёт"][0].click_input()
        time.sleep(0.8)
        deadline = time.time() + timeout
        while time.time() < deadline:
            for found in self.app.windows():
                if found.is_visible() and found.class_name() == "TMessageForm":
                    time.sleep(0.4)
                    image = found.capture_as_image()
                    text = self.message_text(found)
                    found.close()
                    time.sleep(0.5)
                    raise CalcRefused(image, text)
                if report and found.is_visible() and found.class_name() == "TFormRes":
                    time.sleep(0.5)
                    return report_rows(found)
            if not report and self.calculated():
                time.sleep(0.5)
                return []
            time.sleep(0.5)
        raise TimeoutError("LineCapacity не закончила расчёт")

    def memo(self, kind: str, obj) -> list[str]:
        return self.memo_text(kind, obj, "период:")

    def mark_rows(self, line) -> list[str]:
        return self.memo_text("line", line, "Материал провода")

    def memo_text(self, kind: str, obj, marker: str) -> list[str]:
        win = self.window(self.open_object(kind, obj))
        time.sleep(0.4)
        texts = [c.window_text() for c in win.descendants() if c.class_name() == "TMemo" and c.is_visible()]
        text = next((item for item in texts if marker in item), "")
        win.close()
        time.sleep(0.8)
        rows = text.replace("\r\n", "\n").split("\n")
        return rows[:-1] if rows and rows[-1] == "" else rows

    def save_as(self, path: Path) -> None:
        path = Path(path)
        if path.exists():
            path.unlink()
        self.menu("Файл->Сохранить как", 1.5)
        dialog = self.app.window(title="Сохранение")
        dialog.wait("visible", timeout=10)
        dialog.child_window(class_name="Edit", found_index=0).set_edit_text(str(path))
        time.sleep(0.4)
        [b for b in dialog.children() if "хранить" in b.window_text()][0].click_input()
        time.sleep(1.5)
        for win in self.app.windows():
            if win.is_visible() and win.class_name() == "#32770" and win.window_text() != "Сохранение":
                buttons = [b for b in win.children() if b.window_text() in ("Да", "&Да", "Yes", "&Yes")]
                if buttons:
                    buttons[0].click_input()
                    time.sleep(0.6)
        deadline = time.time() + 10
        while not path.exists() and time.time() < deadline:
            time.sleep(0.3)

    def open(self, path: Path) -> list[str]:
        import pywinauto.keyboard as keyboard
        self.main.set_focus()
        keyboard.send_keys("{F3}")
        time.sleep(1.4)
        dialog = self.app.window(title_re=".*[Оо]ткр.*")
        dialog.wait("visible", timeout=10)
        dialog.child_window(class_name="Edit", found_index=0).set_edit_text(str(path))
        time.sleep(0.4)
        dialog.set_focus()
        keyboard.send_keys("{ENTER}")
        time.sleep(2.5)
        return self.messages()

    def messages(self) -> list[str]:
        texts = []
        for win in self.app.windows():
            if win.is_visible() and win.class_name() in ("#32770", "TMessageForm"):
                texts.append(" ".join(c.window_text() for c in win.children() if c.window_text()))
        return texts

    def screenshot(self, path: Path):
        self.main.set_focus()
        time.sleep(0.4)
        image = self.main.capture_as_image()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path))
        return image


def ink(image, top: int = 60, bottom: int = 40) -> int:
    from collections import Counter
    width, height = image.size
    crop = image.crop((12, top, width - 12, height - bottom)).convert("RGB")
    pixels = list(crop.getdata())
    background, _ = Counter(pixels).most_common(1)[0]
    return sum(1 for p in pixels if sum(abs(a - b) for a, b in zip(p, background, strict=True)) > 60)

from __future__ import annotations

import socket
import threading
import time

import uvicorn

from voltplan.app import create_app
from voltplan.exchange.cir import format_number


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Server:
    def __init__(self) -> None:
        self.port = free_port()
        config = uvicorn.Config(create_app(), host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def __enter__(self) -> Server:
        self.thread.start()
        deadline = time.time() + 20
        while not self.server.started and time.time() < deadline:
            time.sleep(0.1)
        return self

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


class EditorPage:
    def __init__(self, page) -> None:
        self.page = page
        self.errors: list[str] = []
        page.on("console", self.console)
        page.on("pageerror", lambda error: self.errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())

    def console(self, message) -> None:
        if message.type == "error" and "status of 409" not in message.text:
            self.errors.append(message.text)

    def fit(self) -> None:
        self.page.click("#zoom-fit")
        self.page.wait_for_timeout(150)

    def click_point(self, x: int, y: int) -> None:
        self.fit()
        self.page.locator(f'[data-point][data-x="{x}"][data-y="{y}"] .pt-hit').first.click(force=True)
        self.page.wait_for_selector("#popup:not([hidden])")

    def object_position(self, kind: str, index: int) -> list[float]:
        return self.page.evaluate("""([kind, index]) => {
            const group = document.querySelector(`[data-kind="${kind}"][data-index="${index}"]`);
            const shape = group.querySelector('.w-hit') || group.querySelector('rect');
            const matrix = shape.getScreenCTM();
            let x, y;
            if (shape.tagName === 'line') {
                const x1 = +shape.getAttribute('x1'), y1 = +shape.getAttribute('y1');
                const x2 = +shape.getAttribute('x2'), y2 = +shape.getAttribute('y2');
                const along = kind === 'pole' ? 15 : Math.min(20, Math.hypot(x2 - x1, y2 - y1) / 2);
                const length = Math.hypot(x2 - x1, y2 - y1) || 1;
                x = x1 + (x2 - x1) * along / length;
                y = y1 + (y2 - y1) * along / length;
            } else {
                x = +shape.getAttribute('x') + +shape.getAttribute('width') / 2;
                y = +shape.getAttribute('y') + +shape.getAttribute('height') / 2;
            }
            const point = new DOMPoint(x, y).matrixTransform(matrix);
            return [point.x, point.y];
        }""", [kind, index])

    def click_object(self, kind: str, index: int, zoom: int = 0) -> None:
        self.fit()
        for _ in range(zoom):
            x, y = self.object_position(kind, index)
            self.page.mouse.move(x, y)
            self.page.mouse.wheel(0, -240)
            self.page.wait_for_timeout(60)
        x, y = self.object_position(kind, index)
        self.page.mouse.click(x, y)
        self.page.wait_for_selector("#props h3")
        self.page.wait_for_timeout(150)
        assert "null" not in self.page.locator("#props").inner_text()

    def applied(self, selector: str) -> None:
        with self.page.expect_response(lambda response: "/api/scheme/apply" in response.url):
            self.page.click(selector)
        self.page.wait_for_timeout(120)

    def section(self, number: int):
        return self.page.locator(f"#modal-body fieldset:nth-of-type({number})")

    def fill(self, section, name: str, value) -> None:
        text = format_number(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
        section.locator(f'input[name="{name}"]').fill(text)

    def fill_transformer(self, section, data: dict) -> None:
        for name in ("type_name", "label", "sn_kva", "px_kw", "pk_kw", "uvn_kv", "unn_kv", "uk_percent"):
            if name in data:
                self.fill(section, name, data[name])
        for name in ("pbv_steps", "pbv_step", "pbv_percent"):
            if name in data:
                section.locator(f'select[name="{name}"]').select_option(format_number(data[name]).replace(",", "."))

    def fill_line(self, section, data: dict, to_single: bool = False) -> None:
        if "phase_mode" in data:
            section.locator("label", has_text="Однофазная" if data["phase_mode"] == 1 else "Трёхфазная").click()
        for name in ("type_name", "label", "length_m", "r_phase_ohm_per_km", "r_neutral_ohm_per_km",
                     "r_single_phase_ohm_per_km"):
            if name in data:
                self.fill(section, name, data[name])
        if "phase_no" in data:
            section.locator('select[name="phase_no"]').select_option(str(data["phase_no"]))
        box = section.locator('input[type="checkbox"]')
        if box.count() and to_single:
            box.check()

    def fill_pole(self, section, data: dict) -> None:
        if "label" in data:
            self.fill(section, "label", data["label"])
        if "branch_count" in data:
            section.locator('select[name="branch_count"]').select_option(str(data["branch_count"]))

    def fill_consumer(self, section, data: dict) -> None:
        for name in ("type_text", "label", "address"):
            if name in data:
                self.fill(section, name, data[name])
        if "load_type" in data:
            section.locator("label", has_text="Индивидуальные" if data["load_type"] == 1 else "Типовые").click()
        if "category" in data:
            section.locator('select[name="category"]').select_option(str(int(data["category"])))
        for name in ("annual_kwh", "p_kw", "cos_phi"):
            if name in data:
                self.fill(section, name, data[name])

    def submit(self) -> None:
        self.page.click("#modal-ok")
        self.page.wait_for_selector("#modal", state="hidden")
        self.page.wait_for_timeout(250)

    def update(self, target: str, index: int, fields: dict, zoom: int = 0) -> None:
        self.click_object(target, index, zoom)
        props = self.page.locator("#props fieldset")
        fill = {"transformer": self.fill_transformer, "line": self.fill_line, "pole": self.fill_pole,
                "consumer": self.fill_consumer}[target]
        fill(props, fields)
        self.applied("#props button:has-text('Применить')")

    def perform(self, action: dict, before) -> None:
        kind = action["kind"]
        if kind == "new":
            self.page.click("#btn-new")
            self.page.wait_for_selector("#modal:not([hidden])")
            self.fill_transformer(self.section(1), action.get("transformer", {}))
            self.fill_line(self.section(2), action.get("line", {}))
            self.fill_pole(self.section(3), action.get("pole", {}))
            self.submit()
            return
        if kind == "add_branch":
            self.click_object("pole", action["index"])
            self.applied("#props button:has-text('Добавить ответвление')")
            return
        if kind == "delete":
            self.click_object(action["target"], action["index"])
            self.applied("#props button:has-text('Удалить')")
            return
        if kind == "update":
            self.update(action["target"], action["index"], action.get("fields", {}))
            return
        if kind == "undo":
            with self.page.expect_response(lambda response: "/api/scheme/undo" in response.url):
                self.page.click("#btn-undo")
            self.page.wait_for_timeout(150)
            return
        if kind == "click":
            self.click_point(action["point"]["x"], action["point"]["y"])
            self.page.keyboard.press("Escape")
            return
        if kind == "outgoing":
            self.page.click('#actions [data-action="outgoing"]')
        else:
            self.click_point(action["point"]["x"], action["point"]["y"])
            self.page.click(f'#popup [data-action="{kind}"]')
        self.page.wait_for_selector("#modal:not([hidden])")
        if kind in ("outgoing", "span", "branch_line"):
            self.fill_line(self.section(1), action.get("line", {}), action.get("to_single", False))
            self.fill_pole(self.section(2), action.get("pole", {}))
        elif kind == "branch_consumer":
            self.fill_line(self.section(1), action.get("line", {}))
            self.fill_consumer(self.section(2), action.get("consumer", {}))
        elif kind == "pole":
            self.fill_pole(self.section(1), action.get("pole", {}))
        elif kind == "consumer":
            self.fill_consumer(self.section(1), action.get("consumer", {}))
        self.submit()

    def save(self) -> bytes:
        with self.page.expect_download() as info:
            self.page.click("#btn-save")
        return info.value.path().read_bytes()

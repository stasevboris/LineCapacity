from __future__ import annotations

import pytest

from tests.helpers import ROOT, SCHEMES, act
from tests.live.ui import EditorPage, Server
from tests.sequences import SEQUENCES, build
from voltplan.calc.results import run
from voltplan.catalog import mark_rows
from voltplan.exchange import cir

pytestmark = pytest.mark.live

SHOTS = ROOT / "logs" / "screens"
SAMPLE = ROOT / "schemes" / "Ботвиново ГКТП397.cir"
KAMENKA = ROOT / "schemes" / "Каменка КТП158.cir"
MIXED = ROOT / "tests" / "data" / "calc" / "разные-типы.cir"
HIGH = ROOT / "tests" / "data" / "calc" / "высокое-напряжение-1кВ.cir"
ONE_THREE_PHASE = ROOT / "tests" / "data" / "calc" / "один-трёхфазный.cir"


@pytest.fixture(scope="module")
def server():
    with Server() as running:
        yield running


@pytest.fixture(scope="module")
def browser():
    playwright_api = pytest.importorskip("playwright.sync_api")
    with playwright_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch(channel="chrome")
        except Exception:
            try:
                instance = playwright.chromium.launch()
            except Exception as error:
                pytest.skip(f"браузер недоступен: {error}")
        yield instance
        instance.close()


@pytest.fixture
def editor(server, browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    page = server.editor(context)
    page.wait_for_selector("#empty:not([hidden])")
    wrapper = EditorPage(page)
    yield wrapper
    context.close()


def shot(editor, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    editor.page.screenshot(path=str(SHOTS / f"{name}.png"))


def counts(page) -> dict:
    return page.evaluate("""() => ({
        lines: document.querySelectorAll('#layer-lines [data-kind="line"]').length,
        poles: document.querySelectorAll('#layer-poles [data-kind="pole"]').length,
        consumers: document.querySelectorAll('#layer-consumers [data-kind="consumer"]').length,
        points: document.querySelectorAll('#layer-points [data-point]').length,
        bus: document.querySelectorAll('[data-kind="transformer"] .w-bus').length,
    })""")


def test_empty_editor(editor):
    assert editor.page.title().startswith("VoltPlan")
    assert editor.page.locator("#scene").evaluate("el => el.namespaceURI") == "http://www.w3.org/2000/svg"
    shot(editor, "01-пустой-редактор")
    assert editor.errors == []


def test_new_scheme_from_dialog(editor):
    editor.page.click("#empty-new")
    editor.page.wait_for_selector("#modal:not([hidden])")
    shot(editor, "02-диалог-новой-схемы")
    editor.submit()
    assert counts(editor.page) == {"lines": 1, "poles": 1, "consumers": 0, "points": 2, "bus": 1}
    assert editor.page.locator("#st-free").inner_text() == "2"
    shot(editor, "03-новая-схема")
    assert editor.errors == []


@pytest.mark.parametrize("name", list(SEQUENCES))
def test_ui_builds_same_file_as_engine(editor, name):
    history = build(SEQUENCES[name]())
    previous = None
    for action, scheme in history:
        editor.perform(action, previous)
        previous = scheme
    final = history[-1][1]
    assert counts(editor.page)["lines"] == len(final.lines)
    assert counts(editor.page)["consumers"] == len(final.consumers)
    editor.fit()
    shot(editor, f"04-построено-{name}")
    assert editor.save() == cir.dump_bytes(final)
    assert editor.errors == []


def test_menu_popup_and_properties(editor):
    editor.page.click("#empty-new")
    editor.submit()
    editor.click_point(163, 70)
    titles = editor.page.locator("#popup .action").all_inner_texts()
    assert titles == ["Отходящая от ТП ЛЭП", "Ответвление к другой линии", "Ответвление к потребителю"]
    shot(editor, "05-меню-точки")
    editor.page.keyboard.press("Escape")
    editor.click_object("pole", 0)
    editor.page.fill('#props input[name="label"]', "7/1")
    editor.page.click("#props button:has-text('Применить')")
    editor.page.wait_for_timeout(300)
    assert editor.page.locator("#layer-labels text", has_text="7/1").count() == 1
    shot(editor, "06-свойства-опоры")
    assert editor.errors == []


def test_refusal_is_shown_and_undo_works(editor):
    editor.page.click("#empty-new")
    editor.submit()
    editor.click_point(193, 70)
    editor.page.click('#popup [data-action="span"]')
    editor.submit()
    editor.click_object("pole", 0)
    editor.page.click("#props button:has-text('Удалить')")
    editor.page.wait_for_selector("#toast:not([hidden])")
    assert "Опора не удалена" in editor.page.locator("#toast").inner_text()
    assert counts(editor.page)["poles"] == 2
    editor.click_point(163, 70)
    editor.page.click('#popup [data-action="branch_consumer"]')
    editor.page.wait_for_selector("#modal:not([hidden])")
    assert editor.page.locator("#toast").is_hidden()
    editor.page.click("#modal-cancel")
    with editor.page.expect_response(lambda response: "/api/scheme/undo" in response.url):
        editor.page.click("#btn-undo")
    editor.page.wait_for_timeout(200)
    after = counts(editor.page)
    assert (after["lines"], after["poles"], after["points"]) == (2, 1, 2)
    assert editor.errors == []


def test_catalog_picker_fills_line(editor):
    editor.page.click("#empty-new")
    editor.page.wait_for_selector("#modal:not([hidden])")
    editor.section(2).locator("button:has-text('Справочник')").click()
    editor.page.wait_for_selector("#picker:not([hidden])")
    editor.page.fill("#picker-search", "СИП-2 3х50")
    editor.page.wait_for_timeout(200)
    shot(editor, "07-справочник")
    editor.page.locator("#picker-list .picker-item").first.click()
    value = editor.section(2).locator('input[name="type_name"]').input_value()
    assert value.startswith("СИП-2 3х50")
    assert editor.section(2).locator('input[name="r_phase_ohm_per_km"]').input_value() != "1,8"
    assert editor.errors == []


@pytest.mark.parametrize("path", SCHEMES[:3], ids=[p.stem for p in SCHEMES[:3]])
def test_import_renders_file(editor, path):
    editor.page.set_input_files("#file-cir", str(path))
    editor.page.wait_for_function("document.querySelectorAll('#layer-lines [data-kind=\"line\"]').length > 0")
    scheme = cir.load_bytes(path.read_bytes())
    assert counts(editor.page)["lines"] == len(scheme.lines)
    assert counts(editor.page)["poles"] == len(scheme.poles)
    assert counts(editor.page)["consumers"] == len(scheme.consumers)
    assert counts(editor.page)["points"] == sum(1 for p in scheme.connection_points if p.active)
    assert editor.page.locator("#scheme-name").input_value() == path.stem
    shot(editor, f"08-импорт-{path.stem}")
    assert editor.save() == path.read_bytes()
    assert editor.errors == []


def test_dark_theme(editor):
    editor.page.click("#empty-new")
    editor.submit()
    editor.page.click("#btn-theme")
    assert editor.page.evaluate("document.documentElement.dataset.theme") == "dark"
    editor.page.wait_for_timeout(400)
    background = editor.page.locator(".panel-right").evaluate("el => getComputedStyle(el).backgroundColor")
    assert background == "rgb(17, 26, 46)"
    bar = editor.page.locator(".top").evaluate("el => getComputedStyle(el).backgroundColor")
    assert bar == "rgb(15, 23, 42)"
    shot(editor, "09-тёмная-тема")
    assert editor.errors == []


def open_sample(editor) -> None:
    editor.page.set_input_files("#file-cir", str(SAMPLE))
    editor.page.wait_for_function("document.querySelectorAll('#layer-lines [data-kind]').length > 100")


def test_sample_edit_keeps_everything_else(editor):
    open_sample(editor)
    editor.click_object("line", 16, zoom=8)
    props = editor.page.locator("#props")
    assert props.locator('input[type="radio"][value="1"]').is_checked()
    assert props.locator('input[name="r_single_phase_ohm_per_km"]').input_value() == "0,84"
    shot(editor, "10-однофазный-пролёт-в-свойствах")
    editor.update("line", 16, {"label": "ВЛ-3а"}, zoom=8)
    editor.click_object("consumer", 0, zoom=8)
    assert props.locator('input[name="p_kw"]').input_value() == "0,180853658536585"
    editor.update("consumer", 0, {"label": "д.22а"}, zoom=8)
    scheme = cir.load_bytes(SAMPLE.read_bytes())
    scheme = act(scheme, kind="update", target="line", index=16, fields={"label": "ВЛ-3а"})
    scheme = act(scheme, kind="update", target="consumer", index=0, fields={"label": "д.22а"})
    assert editor.save() == cir.dump_bytes(scheme)
    assert editor.errors == []


def test_every_line_offers_phase_choice(editor):
    editor.page.click("#empty-new")
    editor.page.wait_for_selector("#modal:not([hidden])")
    assert editor.section(2).locator('input[type="radio"]').count() == 2
    editor.submit()
    editor.click_point(193, 70)
    editor.page.click('#popup [data-action="span"]')
    editor.page.wait_for_selector("#modal:not([hidden])")
    editor.section(1).locator("label", has_text="Однофазная").click()
    assert editor.section(1).locator('input[name="r_single_phase_ohm_per_km"]').is_visible()
    shot(editor, "11-однофазный-пролёт-в-окне")
    editor.submit()
    editor.click_object("line", 1)
    assert editor.page.locator('#props input[type="radio"][value="1"]').is_checked()
    assert editor.errors == []


def test_narrow_window_shows_notice(browser, server):
    context = browser.new_context(viewport={"width": 390, "height": 800})
    page = server.editor(context)
    assert page.locator(".narrow").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / "12-узкое-окно.png"))
    context.close()


def calculate(editor, path) -> dict:
    lines = len(cir.load_bytes(path.read_bytes()).lines)
    editor.page.set_input_files("#file-cir", str(path))
    editor.page.wait_for_function(
        f"document.querySelectorAll('#layer-lines [data-kind=\"line\"]').length === {lines}")
    editor.page.keyboard.press("F7")
    editor.page.wait_for_selector("#modal:not([hidden])")
    with editor.page.expect_response(lambda response: "/api/calc" in response.url):
        editor.page.click("#modal-ok")
    editor.page.wait_for_timeout(300)
    return run(cir.load_bytes(path.read_bytes()))


def shown_labels(page) -> list[str]:
    return page.eval_on_selector_all("#layer-results text", "items => items.map((item) => item.textContent)")


def expected_labels(labels: dict) -> list[str]:
    texts = [item["text"] for values in labels["consumers"] for item in values]
    if "lines" in labels:
        texts += [item["text"] for item in labels["lines"]]
        texts += [item["text"] for item in labels["bus"]] + labels["sums"] + [labels["transformer"]]
    return texts


def test_calc_shows_linecapacity_results(editor):
    expected = calculate(editor, KAMENKA)
    assert editor.page.locator("#report").is_visible()
    rows = editor.page.locator("#report-body .report-row").all_inner_texts()
    assert [row.replace("\u00a0", "") for row in rows] == [row["text"] for row in expected["report"]]
    shot(editor, "13-результаты-расчёта")
    worst = expected["labels"]["1"]["min_consumer"]
    assert worst_colors(editor.page) == (css_color(editor.page, "--res-bad"),
                                         css_color(editor.page, phase_token(KAMENKA, worst)))
    scheme = cir.load_bytes(KAMENKA.read_bytes())
    consumer = scheme.consumers[worst]
    hottest = scheme.lines[expected["labels"]["1"]["max_line"]]
    assert marked_places(editor.page) == [consumer.x - 5, consumer.y, hottest.x, hottest.y]
    transformer = scheme.transformer
    sums = [[transformer.x + step, transformer.y - 20] for step in (340, 420, 500)]
    assert text_places(editor.page, "res-sum") == sums
    assert sorted(shown_labels(editor.page)) == sorted(expected_labels(expected["labels"]["1"]))
    editor.page.click("#report-close")
    editor.page.locator("#results-bar label", has_text="Лето").click()
    assert sorted(shown_labels(editor.page)) == sorted(expected_labels(expected["labels"]["0"]))
    editor.page.locator("#results-bar label", has_text="Мин. нагрузки").click()
    assert sorted(shown_labels(editor.page)) == sorted(expected_labels(expected["labels"]["2"]))
    editor.click_object("consumer", 0, zoom=6)
    lines = editor.page.locator("#props .memo .memo-line").all_inner_texts()
    assert [line.strip() for line in lines] == [line.strip() for line in expected["memo"]["consumers"][0]]
    shot(editor, "14-результаты-потребителя")
    editor.page.click("#btn-hide-results")
    assert editor.page.locator("#results-bar").is_hidden()
    assert shown_labels(editor.page) == []
    assert editor.errors == []


def test_edit_hides_results_but_keeps_report(editor):
    calculate(editor, KAMENKA)
    editor.page.click("#report-close")
    editor.update("consumer", 0, {"label": "д.8а"}, zoom=6)
    assert editor.page.locator("#results-bar").is_hidden()
    assert shown_labels(editor.page) == []
    editor.page.click("#btn-report")
    assert editor.page.locator("#report").is_visible()
    assert editor.errors == []


def test_calc_refusal_is_shown(editor):
    editor.page.click("#empty-new")
    editor.submit()
    editor.page.click("#btn-calc")
    editor.page.wait_for_selector("#modal:not([hidden])")
    editor.page.click("#modal-ok")
    editor.page.wait_for_function("document.getElementById('modal-error').textContent.length > 0")
    assert editor.page.locator("#modal-error").inner_text() == "В схеме отсутствуют потребители! Расчёт не запущен!"
    assert editor.errors == []


def css_color(page, token: str) -> str:
    return page.evaluate("""(token) => {
        const probe = document.createElement('div');
        probe.style.color = `var(${token})`;
        document.body.append(probe);
        const value = getComputedStyle(probe).color;
        probe.remove();
        return value;
    }""", token)


def phase_token(path, index: int) -> str:
    consumer = cir.load_bytes(path.read_bytes()).consumers[index]
    return f"--phase-{consumer.phase_no}" if consumer.phase_mode == 1 else "--wire"


def worst_colors(page) -> tuple[str, str]:
    return tuple(page.eval_on_selector("#layer-results rect.res-worst",
                                       "el => [getComputedStyle(el).fill, getComputedStyle(el).stroke]"))


def leave_one(editor, keep: str) -> dict:
    scheme = cir.load_bytes(MIXED.read_bytes())
    while len(scheme.consumers) > 1:
        index = next(i for i, c in enumerate(scheme.consumers) if c.address != keep)
        consumer = scheme.consumers[index]
        line = next(i for i, item in enumerate(scheme.lines) if (item.end_x, item.end_y) == (consumer.x, consumer.y))
        for action in ({"kind": "delete", "target": "consumer", "index": index},
                       {"kind": "delete", "target": "line", "index": line}):
            editor.perform(action, scheme)
            scheme = act(scheme, **action)
    return run(scheme)


def recalculate(editor) -> None:
    editor.page.keyboard.press("F7")
    editor.page.wait_for_selector("#modal:not([hidden])")
    with editor.page.expect_response(lambda response: "/api/calc" in response.url):
        editor.page.click("#modal-ok")
    editor.page.wait_for_timeout(300)


@pytest.mark.parametrize("keep, ready", [("свет", False), ("иной", True)])
def test_report_button_follows_linecapacity_rule(editor, keep, ready):
    calculate(editor, MIXED)
    assert editor.page.locator("#report").is_visible()
    editor.page.click("#report-close")
    expected = leave_one(editor, keep)
    recalculate(editor)
    assert editor.page.locator("#report").is_hidden()
    assert editor.page.locator("#btn-report").is_enabled()
    editor.page.click("#btn-report")
    if ready:
        rows = editor.page.locator("#report-body .report-row").all_inner_texts()
        assert [row.replace("\u00a0", "") for row in rows] == [row["text"] for row in expected["report"]]
    else:
        assert editor.page.locator("#report").is_hidden()
        assert editor.page.locator("#toast").inner_text() == "Недостаточно потребителей в схеме!"
    shot(editor, f"19-итоги-один-{keep}")
    assert editor.errors == []


def test_opened_file_disables_report_until_calculation(editor):
    calculate(editor, MIXED)
    editor.page.click("#report-close")
    editor.page.set_input_files("#file-cir", str(KAMENKA))
    editor.page.wait_for_function("document.querySelectorAll('#layer-lines [data-kind]').length > 50")
    assert editor.page.locator("#btn-report").is_disabled()
    expected = calculate(editor, ONE_THREE_PHASE)
    assert not expected["show_report"] and expected["report_ready"]
    assert editor.page.locator("#report").is_hidden()
    assert editor.page.locator("#btn-report").is_enabled()
    editor.page.click("#btn-report")
    rows = editor.page.locator("#report-body .report-row").all_inner_texts()
    assert [row.replace("\u00a0", "") for row in rows] == [row["text"] for row in expected["report"]]
    assert editor.errors == []


def label_styles(page) -> list[tuple[str, str, bool]]:
    return [tuple(item) for item in page.eval_on_selector_all("#layer-results text", """items => items.map((item) =>
        [item.textContent, getComputedStyle(item).fill,
         (item.getAttribute('transform') || '').startsWith('rotate(-90')])
    """)]


def expected_styles(page, scheme, labels: dict) -> list[tuple[str, str, bool]]:
    tokens = ("--res-bad", "--res-ok", "--res-temp", "--res-sum")
    red, normal, heat, total = (css_color(page, token) for token in tokens)
    found = [(item["text"], red if item["bad"] else normal, False) for values in labels["consumers"] for item in values]
    found += [(item["text"], red if item["bad"] else heat, line.vertical == 1)
              for item, line in zip(labels["lines"], scheme.lines, strict=True)]
    found += [(item["text"], red if item["bad"] else normal, False) for item in labels["bus"]]
    found += [(text, total, False) for text in labels["sums"]] + [(labels["transformer"], heat, True)]
    return found


@pytest.mark.parametrize("path", [HIGH, MIXED], ids=["красные", "в-норме"])
def test_labels_are_red_only_outside_limits(editor, path):
    expected = calculate(editor, path)
    if editor.page.locator("#report").is_visible():
        editor.page.click("#report-close")
    scheme = cir.load_bytes(path.read_bytes())
    wanted = expected_styles(editor.page, scheme, expected["labels"]["1"])
    assert sorted(label_styles(editor.page)) == sorted(wanted)
    colors = {fill for _, fill, _ in wanted}
    assert (css_color(editor.page, "--res-bad") in colors) is (path == HIGH)
    assert any(rotated for _, _, rotated in wanted[:-1])
    shot(editor, f"21-цвет-подписей-{path.stem}")
    assert editor.errors == []


def test_fit_keeps_result_labels_in_view(editor):
    calculate(editor, HIGH)
    editor.page.click("#report-close")
    editor.page.keyboard.press("F4")
    editor.page.wait_for_timeout(200)
    outside = editor.page.evaluate("""() => {
        const scene = document.getElementById('scene').getBoundingClientRect();
        return [...document.querySelectorAll('#layer-results text')].filter((item) => {
            const box = item.getBoundingClientRect();
            return box.left < scene.left || box.right > scene.right || box.top < scene.top || box.bottom > scene.bottom;
        }).map((item) => item.textContent);
    }""")
    assert outside == []
    shot(editor, "22-вся-схема-с-результатами")
    assert editor.errors == []


def test_transformer_window_draws_daily_charts(editor):
    expected = calculate(editor, KAMENKA)
    editor.page.click("#report-close")
    editor.click_object("transformer", 0)
    charts = editor.page.locator("#props .charts")
    assert charts.locator("label").all_inner_texts() == ["Летний период", "Зимний период"]
    assert charts.locator("input:checked").input_value() == "0"
    assert charts.locator("rect.chart-bar").count() == 48
    assert charts.locator("path.chart-line").count() == 2
    summer = f"00:00 — {expected['charts']['0']['load'][0]:.2f}".replace(".", ",")
    assert charts.locator("rect.chart-bar title").first.text_content() == summer
    charts.locator("label", has_text="Зимний период").click()
    winter = f"00:00 — {expected['charts']['1']['load'][0]:.2f}".replace(".", ",")
    assert charts.locator("rect.chart-bar title").first.text_content() == winter
    memo = editor.page.locator("#props .memo")
    assert memo.evaluate("el => getComputedStyle(el).whiteSpace") == "pre"
    charts.scroll_into_view_if_needed()
    assert editor.page.evaluate("document.documentElement.scrollHeight <= window.innerHeight")
    shot(editor, "20-графики-трансформатора")
    assert editor.errors == []


def marked_places(page) -> list[float]:
    return page.evaluate("""() => {
        const worst = document.querySelector('#layer-results rect.res-worst');
        const hot = document.querySelector('#layer-results line.res-hot');
        return [+worst.getAttribute('x'), +worst.getAttribute('y'), +hot.getAttribute('x1'), +hot.getAttribute('y1')];
    }""")


def text_places(page, cls: str) -> list[list[float]]:
    return page.eval_on_selector_all(f"#layer-results text.{cls}",
                                     "items => items.map((item) => [+item.getAttribute('x'), +item.getAttribute('y')])")


def test_late_mark_answer_does_not_replace_newer_one(editor):
    page = editor.page
    page.set_input_files("#file-cir", str(KAMENKA))
    page.wait_for_function("document.querySelectorAll('#layer-lines [data-kind]').length > 5")
    editor.click_object("line", 0, zoom=6)
    page.wait_for_function("document.querySelector('#props .mark-rows').textContent.length > 0")
    held = []

    def hold(route):
        if not held and "35" in route.request.url:
            held.append(route)
        else:
            route.continue_()

    page.route("**/api/catalog/mark*", hold)
    page.fill('#props input[name="type_name"]', "А 35")
    for _ in range(50):
        if held:
            break
        page.wait_for_timeout(100)
    assert held
    page.fill('#props input[name="type_name"]', "А 50")
    page.wait_for_function("document.querySelector('#props .mark-rows').textContent.includes('50 мм^2')")
    held[0].continue_()
    page.wait_for_timeout(1000)
    phase_mode = cir.load_bytes(KAMENKA.read_bytes()).lines[0].phase_mode
    assert page.locator("#props .mark-rows").inner_text().split("\n") == mark_rows("А 50", phase_mode)
    page.unroute("**/api/catalog/mark*")
    assert editor.errors == []


def test_line_window_shows_how_mark_is_read(editor):
    editor.page.set_input_files("#file-cir", str(KAMENKA))
    editor.page.wait_for_function("document.querySelectorAll('#layer-lines [data-kind]').length > 5")
    editor.click_object("line", 0, zoom=6)
    rows = editor.page.locator("#props .mark-rows")
    editor.page.wait_for_function("document.querySelector('#props .mark-rows').textContent.length > 0")
    line = cir.load_bytes(KAMENKA.read_bytes()).lines[0]
    assert rows.inner_text().split("\n") == mark_rows(line.type_name, line.phase_mode)
    editor.page.fill('#props input[name="type_name"]', "СИП 4х")
    editor.page.wait_for_function(
        "document.querySelector('#props .mark-rows').textContent.includes('не определено')")
    assert rows.inner_text().split("\n")[-1] == "Сечение фазного провода: не определено"
    editor.page.fill('#props input[name="type_name"]', "А 50")
    editor.page.locator("#props label", has_text="Трёхфазная").click()
    editor.page.wait_for_function(
        "document.querySelector('#props .mark-rows').textContent.includes('Сечение фазного провода: 50 мм^2')")
    assert rows.inner_text().split("\n") == mark_rows("А 50", 0)
    editor.page.locator("#props label", has_text="Однофазная").click()
    editor.page.wait_for_function(
        "document.querySelector('#props .mark-rows').textContent.includes('Количество жил: 2')")
    assert rows.inner_text().split("\n") == mark_rows("А 50", 1)
    assert editor.errors == []

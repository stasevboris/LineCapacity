from __future__ import annotations

import json
import re

import pytest

from tests.strings import all_strings, dictionary_path

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
CHINESE = re.compile(r"[一-鿿]")
LONG_WORD = re.compile(r"[А-Яа-яЁё]{4,}")
PLACEHOLDER = re.compile(r"\{\w+\}")
LANGUAGES = ("en", "zh")
LATIN_IN_CHINESE = {"Q={p1} квар", "Q{p1}= {p2} квар", "БЕЛКАРТ", "град.", "град. Цельсия", "квар",
                    "Q, квар"}


def words(code: str) -> dict:
    return json.loads(dictionary_path(code).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def wanted():
    return all_strings()


@pytest.mark.parametrize("code", LANGUAGES)
def test_dictionary_covers_every_interface_string(code, wanted):
    missing = sorted(wanted - set(words(code)))
    assert missing == [], f"нет перевода: {missing[:20]}"


@pytest.mark.parametrize("code", LANGUAGES)
def test_translations_keep_placeholders_and_have_no_russian(code):
    broken = [source for source, target in words(code).items()
              if CYRILLIC.search(target) or sorted(PLACEHOLDER.findall(source)) != sorted(PLACEHOLDER.findall(target))]
    assert broken == []


@pytest.mark.parametrize("code", LANGUAGES)
def test_dictionary_has_no_forgotten_strings(code, wanted):
    unused = sorted(set(words(code)) - wanted)
    assert unused == [], f"лишние строки: {unused[:20]}"


def test_chinese_dictionary_is_written_in_chinese():
    latin = [source for source, target in words("zh").items()
             if LONG_WORD.search(source) and not CHINESE.search(target) and source not in LATIN_IN_CHINESE]
    assert latin == []


def test_key_terms_are_translated_in_context():
    english, chinese = words("en"), words("zh")
    assert english["Тема"] == "Theme" and english["Счёт не найден"] == "Invoice not found"
    assert [chinese[name] for name in ("Демо", "Профессионал", "Максимум")] == ["演示版", "专业版", "旗舰版"]
    assert english["Карта"] == "Card" and english["Данные карты"] == "Card details"
    assert chinese["Карта"] == "银行卡" and "地图" not in chinese["Данные карты"]


def test_collector_sees_every_kind_of_source(wanted):
    assert "Создать аккаунт" in wanted
    assert "Присвоить всем потребителям типовые значения нагрузки" in wanted
    assert "Значение минимального напряжения: {p1} В" in wanted
    assert "В тарифе «{p1}» можно вести не больше {p2} проектов. Уберите лишние в архив или смените тариф." in wanted
    assert "Удалить проект «{name}» со всеми вариантами? Это действие нельзя отменить." in wanted

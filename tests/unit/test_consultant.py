from __future__ import annotations

import pytest

from tests.helpers import PASSWORD
from voltplan import consultant
from voltplan.accounts import Site
from voltplan.accounts.security import Refused
from voltplan.consultant import HOURLY_LIMIT, ROUTES, Consultant


@pytest.fixture
def site(tmp_path):
    instance = Site(tmp_path / "site")
    yield instance
    instance.close()


@pytest.fixture
def user(site):
    return site.users.register("ask@b.by", PASSWORD)


def test_without_key_the_consultant_says_it_is_unavailable(site, user, monkeypatch):
    monkeypatch.delenv("VOLTPLAN_CONSULTANT_KEY", raising=False)
    helper = Consultant(site.store)
    assert not helper.available()
    with pytest.raises(Refused) as problem:
        helper.ask(user, "Как построить схему?", [])
    assert problem.value.status == 503


def test_question_is_sent_with_guide_and_history_and_falls_back(site, user, monkeypatch):
    (site.store.data_dir / "consultant.key").write_text("test-key", encoding="utf-8")
    monkeypatch.delenv("VOLTPLAN_CONSULTANT_KEY", raising=False)
    helper = Consultant(site.store)
    seen = []

    def reply(key, route, messages):
        seen.append((key, route, messages))
        if route == ROUTES[0]:
            raise OSError("нет связи")
        return "Нажмите «Новая схема»."

    monkeypatch.setattr(helper, "request", reply)
    answer = helper.ask(user, "  Как   начать? ", [{"role": "user", "text": "Привет"},
                                                  {"role": "assistant", "text": "Здравствуйте"}])
    assert answer == {"answer": "Нажмите «Новая схема»."}
    assert [route for _, route, _ in seen] == list(ROUTES)
    messages = seen[-1][2]
    assert messages[0]["role"] == "system" and "VoltPlan" in messages[0]["content"]
    assert [item["role"] for item in messages[1:]] == ["user", "assistant", "user"]
    assert messages[-1]["content"] == "Как начать?" and seen[0][0] == "test-key"


def test_questions_are_limited(site, user, monkeypatch):
    monkeypatch.setenv("VOLTPLAN_CONSULTANT_KEY", "test-key")
    helper = Consultant(site.store)
    monkeypatch.setattr(helper, "request", lambda key, route, messages: "ответ")
    with pytest.raises(Refused):
        helper.ask(user, "", [])
    with pytest.raises(Refused):
        helper.ask(user, "x" * 1001, [])
    assert HOURLY_LIMIT == 30
    for _ in range(30):
        helper.ask(user, "вопрос", [])
    with pytest.raises(Refused) as problem:
        helper.ask(user, "вопрос", [])
    assert problem.value.status == 429


def test_start_message_names_where_the_key_comes_from(tmp_path, monkeypatch):
    monkeypatch.delenv(consultant.KEY_VARIABLE, raising=False)
    assert consultant.key_source(tmp_path).startswith("Консультант не подключён")
    (tmp_path / "consultant.key").write_text("ключ-из-файла", encoding="utf-8")
    assert "consultant.key" in consultant.key_source(tmp_path)
    monkeypatch.setenv(consultant.KEY_VARIABLE, "ключ-из-окружения")
    message = consultant.key_source(tmp_path)
    assert consultant.KEY_VARIABLE in message and "ключ-из-окружения" not in message
    assert consultant.consultant_key(tmp_path) == "ключ-из-окружения"


class FakeRegistry:
    HKEY_CURRENT_USER = "пользователь"
    HKEY_LOCAL_MACHINE = "система"

    def __init__(self, values):
        self.values = values

    def OpenKey(self, root, path):
        if root not in self.values:
            raise OSError("нет раздела")
        return FakeHandle(self.values[root])

    def QueryValueEx(self, handle, name):
        if name not in handle.values:
            raise OSError("нет значения")
        return handle.values[name], 1


class FakeHandle:
    def __init__(self, values):
        self.values = values

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_key_written_in_windows_is_found_without_restarting(tmp_path, monkeypatch):
    monkeypatch.delenv(consultant.KEY_VARIABLE, raising=False)
    monkeypatch.setattr(consultant, "winreg", FakeRegistry({}))
    assert consultant.consultant_key(tmp_path) == ""
    monkeypatch.setattr(consultant, "winreg", FakeRegistry({"система": {consultant.KEY_VARIABLE: " общий "}}))
    assert consultant.consultant_key(tmp_path) == "общий"
    monkeypatch.setattr(consultant, "winreg", FakeRegistry({
        "пользователь": {consultant.KEY_VARIABLE: "свой"}, "система": {consultant.KEY_VARIABLE: "общий"}}))
    assert consultant.consultant_key(tmp_path) == "свой"
    message = consultant.key_source(tmp_path)
    assert "записанной в Windows" in message and "свой" not in message
    monkeypatch.setenv(consultant.KEY_VARIABLE, "из-окна")
    assert consultant.consultant_key(tmp_path) == "из-окна"

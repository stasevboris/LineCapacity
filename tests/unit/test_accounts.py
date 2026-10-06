from __future__ import annotations

import sqlite3
import time

import pytest

from tests.helpers import PASSWORD, act
from voltplan.accounts import Site
from voltplan.accounts.security import Refused, Tokens, password_hash, password_matches
from voltplan.accounts.users import FAILURES_BEFORE_PAUSE


@pytest.fixture
def site(tmp_path):
    instance = Site(tmp_path / "site")
    yield instance
    instance.close()


def person(site: Site, email: str, name: str = "", tier: str = "demo"):
    user = site.users.register(email, PASSWORD, name)
    return site.users.set_tier(user.id, tier, None) if tier != "demo" else user


def refused(status: int, call, *args):
    with pytest.raises(Refused) as problem:
        call(*args)
    assert problem.value.status == status
    return str(problem.value)


def test_password_hash_depends_on_salt_and_is_checked_in_constant_form():
    first = password_hash("пароль123", "00" * 16)
    assert first == password_hash("пароль123", "00" * 16)
    assert first != password_hash("пароль123", "01" * 16)
    assert len(first) == 64
    assert password_matches("пароль123", "00" * 16, first)
    assert not password_matches("пароль124", "00" * 16, first)


def test_token_is_rejected_when_forged_expired_or_signed_by_other_key():
    tokens = Tokens(b"key", 60)
    token = tokens.issue(7, "stamp")
    assert tokens.read(token) == (7, "stamp")
    body, signature = token.split(".")
    assert tokens.read(f"{body}.{'0' * len(signature)}") is None
    assert tokens.read(f"{body[:-2]}xx.{signature}") is None
    assert Tokens(b"other", 60).read(token) is None
    assert Tokens(b"key", -1).read(Tokens(b"key", -1).issue(7, "stamp")) is None
    assert tokens.read("") is None and tokens.read(None) is None and tokens.read("a.b.c") is None
    assert tokens.read("ЖЖЖ.ЖЖЖ") is None


def test_credentials_are_kept_apart_from_profiles(site):
    person(site, "Anna@Example.by", "Анна")
    credentials = sqlite3.connect(site.store.data_dir / "credentials.db")
    work = sqlite3.connect(site.store.data_dir / "voltplan.db")
    try:
        tables = {row[0] for row in credentials.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert tables - {"sqlite_sequence"} == {"credentials"}
        columns = [row[1] for row in credentials.execute("PRAGMA table_info(credentials)")]
        assert columns == ["id", "email", "salt", "hash"]
        row = credentials.execute("SELECT email, hash FROM credentials").fetchone()
        assert row[0] == "anna@example.by" and PASSWORD not in row[1]
        for table in [row[0] for row in work.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]:
            names = {row[1] for row in work.execute(f"PRAGMA table_info({table})")}
            assert not names & {"hash", "salt", "password"}
    finally:
        credentials.close()
        work.close()


@pytest.mark.parametrize("email, password, message", [
    ("не-почта", PASSWORD, "Укажите адрес электронной почты, например name@example.by"),
    ("a@b.by", "корот12", "Пароль должен быть не короче 8 знаков"),
    ("a@b.by", "безцифрпароль", "Пароль должен содержать буквы и цифры"),
    ("a@b.by", "1234567890", "Пароль должен содержать буквы и цифры"),
])
def test_registration_refuses_bad_input(site, email, password, message):
    assert refused(400, site.users.register, email, password) == message


def test_registration_refuses_same_email_in_other_case(site):
    person(site, "a@b.by")
    assert refused(409, site.users.register, " A@B.BY ", PASSWORD) == \
        "Пользователь с такой почтой уже зарегистрирован"


def test_login_pauses_after_repeated_failures(site, monkeypatch):
    person(site, "a@b.by")
    assert FAILURES_BEFORE_PAUSE == 5
    for _ in range(5):
        refused(401, site.users.authenticate, "a@b.by", "неверный1")
    refused(429, site.users.authenticate, "a@b.by", PASSWORD)
    later = time.time() + 301
    monkeypatch.setattr(time, "time", lambda: later)
    assert site.users.authenticate("a@b.by", PASSWORD).email == "a@b.by"


def test_four_failures_do_not_pause_the_login(site):
    person(site, "b@b.by")
    for _ in range(4):
        refused(401, site.users.authenticate, "b@b.by", "неверный1")
    assert site.users.authenticate("b@b.by", PASSWORD).email == "b@b.by"


def test_password_change_ends_other_sessions(site):
    user = person(site, "a@b.by")
    token = site.token_for(user)
    assert site.session_user(token).id == user.id
    refused(403, site.users.change_password, user, "неверный1", "новыйпароль2")
    changed = site.users.change_password(user, PASSWORD, "новыйпароль2")
    assert site.session_user(token) is None
    assert site.session_user(site.token_for(changed)).id == user.id
    assert site.users.authenticate("a@b.by", "новыйпароль2").id == user.id


def test_profile_language_is_limited_to_three(site):
    user = person(site, "a@b.by")
    assert site.users.update_profile(user, "Анна", "zh").language == "zh"
    assert refused(400, site.users.update_profile, user, None, "de") == "Язык интерфейса: ru, en или zh"


def shared_project(site):
    owner = person(site, "owner@b.by", "Владелец", "max")
    editor = person(site, "editor@b.by", "Редактор")
    reader = person(site, "reader@b.by", "Читатель")
    stranger = person(site, "stranger@b.by", "Чужой")
    team = site.collab.create_team(owner, "Бригада")
    for member, role in ((editor, "editor"), (reader, "reader")):
        invitation = site.collab.invite(owner, member.email, team["id"], role)
        site.collab.answer(member, invitation["id"], True)
    scheme = act(None, kind="new")
    project = site.projects.create(owner, "Садовая", scheme)
    site.collab.share(owner, project["id"], team["id"])
    return owner, editor, reader, stranger, project, scheme


def test_roles_decide_what_each_user_may_do(site):
    owner, editor, reader, stranger, project, scheme = shared_project(site)
    number = project["id"]
    assert [site.projects.role(u.id, number) for u in (owner, editor, reader, stranger)] == \
        ["owner", "editor", "reader", None]
    assert site.projects.scheme(reader, number)["scheme"] == scheme.model_dump(mode="json")
    refused(404, site.projects.get, stranger, number)
    refused(404, site.projects.save, stranger, number, scheme)
    refused(403, site.projects.save, reader, number, scheme)
    site.projects.save(editor, number, scheme)
    refused(403, site.projects.rename, editor, number, "Другое")
    refused(403, site.projects.delete, editor, number)
    refused(403, site.collab.share, editor, number, 1)
    assert site.projects.rename(owner, number, "  Садовая,   5 ")["name"] == "Садовая, 5"
    assert [p["id"] for p in site.projects.listing(reader)] == [number]
    assert site.projects.listing(stranger) == []


def test_removed_member_loses_access_and_disband_closes_project(site):
    owner, editor, reader, _, project, _ = shared_project(site)
    team = site.collab.teams(owner)[0]["id"]
    site.collab.remove_member(owner, team, reader.id)
    refused(404, site.projects.get, reader, project["id"])
    site.collab.remove_member(editor, team, editor.id)
    refused(404, site.projects.get, editor, project["id"])
    refused(409, site.collab.remove_member, owner, team, owner.id)
    site.collab.disband(owner, team)
    assert site.collab.teams(owner) == []
    assert site.projects.get(owner, project["id"])["role"] == "owner"


def test_project_variants_and_archive(site):
    owner = person(site, "a@b.by")
    project = site.projects.create(owner, "Пустой")
    main = project["variants"][0]
    assert main["main"] and main["empty"]
    assert site.projects.scheme(owner, project["id"])["scheme"] is None
    scheme = act(None, kind="new")
    site.projects.save(owner, project["id"], scheme)
    copy = site.projects.add_variant(owner, project["id"], "Вариант с СИП")
    assert copy["scheme"] == scheme.model_dump(mode="json") and not copy["main"]
    refused(409, site.projects.delete_variant, owner, project["id"], main["id"])
    site.projects.rename_variant(owner, project["id"], copy["variant"], "Вариант Б")
    names = [v["name"] for v in site.projects.get(owner, project["id"])["variants"]]
    assert names == ["Основной", "Вариант Б"]
    site.projects.archive(owner, project["id"], True)
    assert site.projects.listing(owner) == []
    assert [p["id"] for p in site.projects.listing(owner, archived=True)] == [project["id"]]
    site.projects.delete(owner, project["id"])
    refused(404, site.projects.get, owner, project["id"])


def test_invitations_make_friends_once(site):
    anna = person(site, "anna@b.by", "Анна")
    boris = person(site, "boris@b.by", "Борис")
    invitation = site.collab.invite(anna, "BORIS@b.by")
    assert invitation["from"] == {"id": anna.id, "name": "Анна", "email": "anna@b.by"}
    refused(409, site.collab.invite, anna, "boris@b.by")
    refused(400, site.collab.invite, anna, "anna@b.by")
    refused(404, site.collab.answer, anna, invitation["id"], True)
    site.collab.answer(boris, invitation["id"], True)
    refused(409, site.collab.answer, boris, invitation["id"], False)
    assert site.collab.friends(anna) == [{"id": boris.id, "name": "Борис", "email": "boris@b.by"}]
    assert site.collab.friends(boris)[0]["id"] == anna.id
    refused(409, site.collab.invite, boris, "anna@b.by")
    notes = site.collab.notifications(anna)
    assert notes["unseen"] == 1 and notes["items"][0]["text"] == "Борис принял(а) ваше приглашение"


def test_only_team_owner_invites_and_changes_roles(site):
    owner = person(site, "owner@b.by", tier="max")
    member = person(site, "member@b.by")
    other = person(site, "other@b.by")
    team = site.collab.create_team(owner, "Бригада")["id"]
    invitation = site.collab.invite(owner, member.email, team, "editor")
    site.collab.answer(member, invitation["id"], True)
    refused(403, site.collab.invite, member, other.email, team, "reader")
    refused(400, site.collab.invite, owner, other.email, team, "owner")
    refused(409, site.collab.invite, owner, member.email, team, "reader")
    refused(403, site.collab.set_role, member, team, member.id, "reader")
    roles = {m["id"]: m["role"] for m in site.collab.set_role(owner, team, member.id, "reader")["members"]}
    assert roles == {owner.id: "owner", member.id: "reader"}


def test_messages_go_only_to_friends_and_team_members(site):
    anna = person(site, "anna@b.by", "Анна", "max")
    boris = person(site, "boris@b.by", "Борис")
    stranger = person(site, "x@b.by")
    refused(403, site.collab.send, anna, "Привет", boris.id)
    site.collab.answer(boris, site.collab.invite(anna, boris.email)["id"], True)
    message = site.collab.send(anna, "Привет", boris.id, None, "схема.cir", b"cir")
    assert message["file"] == "схема.cir"
    assert site.collab.file(boris, message["id"]) == ("схема.cir", b"cir")
    refused(404, site.collab.file, stranger, message["id"])
    assert [m["body"] for m in site.collab.history(boris, anna.id)] == ["Привет"]
    refused(400, site.collab.send, anna, "   ", boris.id)
    refused(400, site.collab.send, anna, "x" * 4001, boris.id)
    refused(400, site.collab.send, anna, "", boris.id, None, "run.exe", b"MZ")
    refused(413, site.collab.send, anna, "", boris.id, None, "big.bin", b"0" * (5 * 1024 * 1024 + 1))
    refused(400, site.collab.send, anna, "оба", boris.id, 1)
    team = site.collab.create_team(anna, "Бригада")["id"]
    refused(403, site.collab.send, stranger, "в команду", None, team)
    refused(403, site.collab.history, stranger, None, team)
    site.collab.send(anna, "в команду", None, team)
    assert [m["body"] for m in site.collab.history(anna, None, team)] == ["в команду"]


def test_notifications_are_marked_as_seen(site):
    anna = person(site, "anna@b.by", "Анна")
    boris = person(site, "boris@b.by", "Борис")
    site.collab.answer(boris, site.collab.invite(anna, boris.email)["id"], True)
    site.collab.send(anna, "раз", boris.id)
    site.collab.send(anna, "два", boris.id)
    notes = site.collab.notifications(boris)
    assert notes["unseen"] == 3
    first = notes["items"][0]["id"]
    assert site.collab.mark_seen(boris, [first])["unseen"] == 2
    assert site.collab.mark_seen(anna, [first])["unseen"] == 1
    assert site.collab.notifications(boris)["unseen"] == 2
    assert site.collab.mark_seen(boris)["unseen"] == 0

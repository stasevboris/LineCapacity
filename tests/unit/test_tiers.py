from __future__ import annotations

import time

import pytest

from tests.helpers import PASSWORD, ROOT, act
from voltplan.accounts import Site, tiers
from voltplan.accounts.security import Refused
from voltplan.exchange import cir

BIG = ROOT / "schemes" / "Ботвиново ГКТП397.cir"


@pytest.fixture
def site(tmp_path):
    instance = Site(tmp_path / "site")
    yield instance
    instance.close()


def user(site, tier="demo", until=None):
    created = site.users.register(f"{tier}{time.time_ns()}@b.by", PASSWORD)
    return site.users.set_tier(created.id, tier, until) if tier != "demo" else created


def refused(call, *args) -> str:
    with pytest.raises(Refused) as problem:
        call(*args)
    assert problem.value.status == 403
    return str(problem.value)


def test_three_tiers_grow_in_limits_and_price():
    demo, pro, top = (tiers.TIERS[code] for code in tiers.ORDER)
    assert (demo.price_usd, pro.price_usd, top.price_usd) == (0.0, 19.0, 39.0)
    for field in ("projects", "variants", "compared", "scenarios", "poles", "consumers"):
        assert getattr(demo, field) <= getattr(pro, field) <= getattr(top, field)
    assert demo.features < pro.features < top.features
    assert tiers.lowest_with("docx") is pro and tiers.lowest_with("epure") is top


def test_expired_tier_falls_back_to_demo(site):
    active = user(site, "pro", time.time() + 3600)
    expired = user(site, "pro", time.time() - 1)
    assert tiers.effective(active).code == "pro"
    assert expired.tier == "demo" and tiers.effective(expired).code == "demo"
    assert tiers.effective(user(site, "max")).code == "max"


def test_demo_limits_projects_variants_scenarios_and_size(site):
    demo = user(site)
    scheme = act(None, kind="new")
    first = site.projects.create(demo, "Один", scheme)
    site.projects.create(demo, "Два")
    assert "не больше 2 проектов" in refused(site.projects.create, demo, "Три")
    site.projects.add_variant(demo, first["id"], "Б")
    assert "не больше 2 вариантов" in refused(site.projects.add_variant, demo, first["id"], "В")
    site.projects.add_scenario(demo, first["id"], "С1", {}, 2, True)
    site.projects.add_scenario(demo, first["id"], "С2", {}, 2, True)
    assert "не больше 2 сценариев" in refused(site.projects.add_scenario, demo, first["id"], "С3", {}, 2, True)
    big = cir.load_bytes(BIG.read_bytes())
    message = refused(site.projects.save, demo, first["id"], big)
    assert message.startswith("В тарифе «Демо» схема может содержать не больше 40 опор")
    site.projects.archive(demo, first["id"], True)
    site.projects.create(demo, "Три")


def test_archive_does_not_bypass_the_project_limit(site):
    demo = user(site)
    first = site.projects.create(demo, "Один")
    second = site.projects.create(demo, "Два")
    site.projects.archive(demo, first["id"], True)
    site.projects.archive(demo, second["id"], True)
    site.projects.create(demo, "Три")
    site.projects.create(demo, "Четыре")
    assert "не больше 2 проектов" in refused(site.projects.archive, demo, first["id"], False)
    assert site.projects.count_own(demo) == 2
    site.projects.archive(demo, site.projects.listing(demo, False)[0]["id"], True)
    assert site.projects.archive(demo, first["id"], False)["archived"] is False
    assert site.projects.count_own(demo) == 2


def test_features_follow_the_tier(site):
    demo, pro, top = user(site), user(site, "pro"), user(site, "max")
    mark = {"type_name": "СИП-2 3х95+1х95", "r_phase_ohm_per_km": 0.32, "r_neutral_ohm_per_km": 0.32}
    assert "тарифе «Профессионал»" in refused(site.marks.add, demo, "line", mark)
    assert site.marks.add(pro, "line", mark)["lines"][0]["type_name"] == "СИП-2 3х95+1х95"
    assert "Создание команд" in refused(site.collab.create_team, pro, "Бригада")
    assert site.collab.create_team(top, "Бригада")["name"] == "Бригада"


def test_own_marks_are_checked_and_private(site):
    pro, other = user(site, "pro"), user(site, "pro")
    transformer = {"type_name": "ТМГ-160-мой", "sn_kva": 160, "px_kw": 0.44, "pk_kw": 2.6, "uvn_kv": 10,
                   "unn_kv": 0.4, "uk_percent": 4.5, "pbv_steps": 5, "pbv_percent": 2.5}
    listed = site.marks.add(pro, "transformer", transformer)
    assert listed["transformers"][0] | {"id": 0} == {**transformer, "sn_kva": 160.0, "px_kw": 0.44, "pk_kw": 2.6,
                                                     "uvn_kv": 10.0, "unn_kv": 0.4, "uk_percent": 4.5,
                                                     "pbv_percent": 2.5, "own": True, "id": 0}
    assert site.marks.listing(other) == {"lines": [], "transformers": []}
    for wrong in ({**transformer, "sn_kva": 0}, {**transformer, "pbv_steps": 12},
                  {**transformer, "type_name": "с пробелом"}, {**transformer, "type_name": "  "}):
        with pytest.raises(Refused):
            site.marks.add(pro, "transformer", wrong)
    with pytest.raises(Refused) as twice:
        site.marks.add(pro, "transformer", transformer)
    assert twice.value.status == 409
    with pytest.raises(Refused) as foreign:
        site.marks.delete(other, listed["transformers"][0]["id"])
    assert foreign.value.status == 404
    assert site.marks.delete(pro, listed["transformers"][0]["id"])["transformers"] == []

from __future__ import annotations

import time

import pytest

from tests.helpers import PASSWORD
from voltplan.accounts import Site
from voltplan.accounts.billing import PERIOD_SECONDS, card_brand, check_card, luhn, masked
from voltplan.accounts.security import Refused

FUTURE = time.strftime("%m/%y", time.localtime(time.time() + 400 * 86400))


@pytest.fixture
def site(tmp_path):
    instance = Site(tmp_path / "site")
    yield instance
    instance.close()


@pytest.fixture
def buyer(site):
    return site.users.register("buyer@b.by", PASSWORD, "Покупатель")


@pytest.mark.parametrize("number, brand", [
    ("4111111111111111", "Visa"), ("5555555555554444", "Mastercard"), ("2200000000000004", "МИР"),
    ("9112000000000006", "БЕЛКАРТ"), ("378282246310005", "American Express"), ("6200000000000005", "UnionPay"),
    ("6759649826438453", "Maestro"),
])
def test_test_cards_pass_luhn_and_are_recognised(number, brand):
    assert luhn(number)
    assert check_card(number, FUTURE, "1234" if brand == "American Express" else "123", "", time.time()).title == brand


@pytest.mark.parametrize("number, expiry, cvv, holder, message", [
    ("4111 1111 1111 1112", FUTURE, "123", "", "контрольную проверку"),
    ("4111111", FUTURE, "123", "", "длина"),
    ("7111111111111111", FUTURE, "123", "", "не поддерживается"),
    ("4111111111111111", "01/20", "123", "", "истёк"),
    ("4111111111111111", "13/30", "123", "", "Месяц"),
    ("4111111111111111", "1230", "123", "", "ММ/ГГ"),
    ("4111111111111111", FUTURE, "12", "", "CVV"),
    ("4111111111111111", FUTURE, "123", "Иван", "латиницей"),
])
def test_card_mistakes_are_explained(number, expiry, cvv, holder, message):
    with pytest.raises(Refused) as problem:
        check_card(number, expiry, cvv, holder, time.time())
    assert message in str(problem.value)


def test_mask_keeps_only_first_six_and_last_four():
    assert masked("4111111111111111") == "411111******1111"
    assert card_brand("22210000") .code == "mastercard"


def test_demo_payment_gives_tier_for_thirty_days_and_extends_it(site, buyer):
    order = site.billing.checkout(buyer, "pro", "demo", "http://x/pay")
    assert order["mode"] == "form" and order["payment"]["amount_usd"] == 19.0
    paid = site.billing.confirm(buyer, order["payment"]["id"], "4111 1111 1111 1111", FUTURE, "123", "IVAN")
    assert paid["status"] == "paid" and paid["card"] == "411111******1111"
    user = site.users.get(buyer.id)
    assert user.tier == "pro" and user.tier_until == pytest.approx(time.time() + PERIOD_SECONDS, abs=5)
    again = site.billing.checkout(user, "pro", "demo", "http://x/pay")
    site.billing.confirm(user, again["payment"]["id"], "5555555555554444", FUTURE, "123", "")
    assert site.users.get(buyer.id).tier_until == pytest.approx(user.tier_until + PERIOD_SECONDS, abs=5)
    assert [item["status"] for item in site.billing.history(buyer)] == ["paid", "paid"]
    assert site.collab.notifications(buyer)["items"][0]["text"] == "Тариф «Профессионал» оплачен"
    stored = site.store.work.execute("SELECT * FROM payments").fetchall()
    assert all("4111111111111111" not in " ".join(str(value) for value in row) for row in stored)


def test_declined_card_and_closed_invoice(site, buyer):
    order = site.billing.checkout(buyer, "max", "demo", "http://x/pay")
    with pytest.raises(Refused) as declined:
        site.billing.confirm(buyer, order["payment"]["id"], "4000000000000002", FUTURE, "123", "")
    assert declined.value.status == 402
    assert site.users.get(buyer.id).tier == "demo"
    with pytest.raises(Refused) as closed:
        site.billing.confirm(buyer, order["payment"]["id"], "4111111111111111", FUTURE, "123", "")
    assert closed.value.status == 409
    with pytest.raises(Refused):
        site.billing.checkout(buyer, "demo", "demo", "http://x/pay")


def test_foreign_invoice_is_not_found(site, buyer):
    other = site.users.register("other@b.by", PASSWORD)
    order = site.billing.checkout(buyer, "pro", "demo", "http://x/pay")
    with pytest.raises(Refused) as problem:
        site.billing.confirm(other, order["payment"]["id"], "4111111111111111", FUTURE, "123", "")
    assert problem.value.status == 404


def test_sandbox_redirect_and_poll(site, buyer, monkeypatch):
    calls = []

    def answer(method, url, payload=None):
        calls.append((method, url, payload))
        if method == "POST":
            url = "https://checkout.begateway.com/v2/checkout?token=tok1"
            return {"checkout": {"token": "tok1", "redirect_url": url}}
        return {"checkout": {"finished": True, "gateway_response": {"payment": {
            "status": "successful", "credit_card": {"brand": "visa", "first_1": "4", "last_4": "1111"}}}}}

    monkeypatch.setattr(site.billing.sandbox, "request", answer)
    order = site.billing.checkout(buyer, "max", "bepaid", "http://127.0.0.1:8000/pay")
    assert order["mode"] == "redirect" and order["url"].endswith("tok1")
    sent = calls[0][2]["checkout"]
    assert sent["test"] is True and sent["order"]["amount"] == 3900 and sent["order"]["currency"] == "USD"
    assert sent["settings"]["return_url"] == f"http://127.0.0.1:8000/pay?await={order['payment']['id']}"
    with pytest.raises(Refused):
        site.billing.confirm(buyer, order["payment"]["id"], "4111111111111111", FUTURE, "123", "")
    result = site.billing.poll(buyer, order["payment"]["id"])
    assert result["status"] == "paid" and result["card"].endswith("1111")
    assert site.users.get(buyer.id).tier == "max"
    assert site.billing.poll(buyer, order["payment"]["id"])["status"] == "paid"


def test_sandbox_unavailable_falls_back_to_card_form(site, buyer, monkeypatch):
    monkeypatch.setattr(site.billing.sandbox, "request", lambda *args, **kwargs: {})
    order = site.billing.checkout(buyer, "pro", "bepaid", "http://x/pay")
    assert order["mode"] == "form" and order["fallback"] and order["payment"]["provider"] == "demo"
    paid = site.billing.confirm(buyer, order["payment"]["id"], "2200000000000004", FUTURE, "123", "")
    assert paid["status"] == "paid"


def test_one_invoice_is_credited_once(site, buyer):
    order = site.billing.checkout(buyer, "pro", "demo", "http://x/pay")
    row = site.store.work.execute("SELECT * FROM payments WHERE id = ?", (order["payment"]["id"],)).fetchone()
    assert site.billing.finish(row, "paid", "411111******1111", "Visa", "") is True
    assert site.billing.finish(row, "paid", "411111******1111", "Visa", "") is False
    user = site.users.get(buyer.id)
    assert user.tier_until == pytest.approx(time.time() + PERIOD_SECONDS, abs=5)
    assert [item["status"] for item in site.billing.history(buyer)] == ["paid"]


def test_lower_tier_cannot_be_bought_while_higher_is_active(site, buyer):
    maximum = site.users.set_tier(buyer.id, "max", time.time() + 25 * 86400)
    with pytest.raises(Refused) as problem:
        site.billing.checkout(maximum, "pro", "demo", "http://x/pay")
    assert problem.value.status == 409 and "Максимум" in str(problem.value)
    assert site.billing.history(buyer) == []
    assert site.billing.checkout(maximum, "max", "demo", "http://x/pay")["mode"] == "form"


def test_old_lower_invoice_paid_after_upgrade_extends_the_higher_tier(site, buyer):
    old = site.billing.checkout(buyer, "pro", "demo", "http://x/pay")
    maximum = site.billing.checkout(buyer, "max", "demo", "http://x/pay")
    site.billing.confirm(buyer, maximum["payment"]["id"], "4111111111111111", FUTURE, "123", "")
    upgraded = site.users.get(buyer.id)
    assert upgraded.tier == "max"
    site.billing.confirm(upgraded, old["payment"]["id"], "4111111111111111", FUTURE, "123", "")
    after = site.users.get(buyer.id)
    assert after.tier == "max"
    assert after.tier_until == pytest.approx(upgraded.tier_until + PERIOD_SECONDS * 19 / 39, abs=5)
    assert "продлён на 15 дн." in site.collab.notifications(buyer)["items"][0]["text"]
    messages = {item["id"]: item["message"] for item in site.billing.history(buyer)}
    assert "продлён на 15 дн." in messages[old["payment"]["id"]]


def test_upgrade_counts_the_rest_of_the_lower_tier(site, buyer):
    professional = site.users.set_tier(buyer.id, "pro", time.time() + 13 * 86400)
    order = site.billing.checkout(professional, "max", "demo", "http://x/pay")
    site.billing.confirm(professional, order["payment"]["id"], "4111111111111111", FUTURE, "123", "")
    after = site.users.get(buyer.id)
    assert after.tier == "max"
    assert after.tier_until == pytest.approx(time.time() + PERIOD_SECONDS + 13 * 86400 * 19 / 39, abs=5)
    messages = [item["message"] for item in site.billing.history(buyer)]
    assert "зачтены: срок продлён на 6 дн." in messages[0]


def test_tier_without_end_is_not_sold_again(site, buyer):
    granted = site.users.set_tier(buyer.id, "pro", None)
    for tier in ("pro", "max"):
        with pytest.raises(Refused) as problem:
            site.billing.checkout(granted, tier, "demo", "http://x/pay")
        assert problem.value.status == 409 and "без срока" in str(problem.value) and "—" not in str(problem.value)
    assert site.billing.history(buyer) == []


def test_old_invoice_does_not_cut_a_tier_without_end(site, buyer):
    old = site.billing.checkout(buyer, "max", "demo", "http://x/pay")
    granted = site.users.set_tier(buyer.id, "pro", None)
    site.billing.confirm(granted, old["payment"]["id"], "4111111111111111", FUTURE, "123", "")
    after = site.users.get(buyer.id)
    assert after.tier == "pro" and after.tier_until is None
    assert "без срока" in site.billing.history(buyer)[0]["message"]

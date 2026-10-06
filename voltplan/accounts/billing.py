from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

from . import tiers
from .security import Refused
from .storage import Store
from .users import User, Users

SANDBOX_URL = "https://checkout.begateway.com/ctp/api/checkouts"
SANDBOX_SHOP = "361"
SANDBOX_KEY = "b8647b68898b084b836474ed8d61ffe117c9a01168d867f24953b776ddcb134d"
PERIOD_SECONDS = tiers.PERIOD_DAYS * 24 * 3600
DECLINED_CARD = "4000000000000002"
PENDING_SECONDS = 3600


@dataclass(frozen=True)
class Brand:
    code: str
    title: str
    ranges: tuple[tuple[str, str], ...]
    lengths: tuple[int, ...]
    cvv: int


BRANDS = (
    Brand("mir", "МИР", (("2200", "2204"),), (16, 17, 18, 19), 3),
    Brand("belkart", "БЕЛКАРТ", (("9112", "9112"),), (16,), 3),
    Brand("amex", "American Express", (("34", "34"), ("37", "37")), (15,), 4),
    Brand("unionpay", "UnionPay", (("62", "62"),), (16, 17, 18, 19), 3),
    Brand("mastercard", "Mastercard", (("51", "55"), ("2221", "2720")), (16,), 3),
    Brand("maestro", "Maestro", (("50", "50"), ("56", "69")), (16, 17, 18, 19), 3),
    Brand("visa", "Visa", (("4", "4"),), (13, 16, 19), 3),
)


def card_digits(number: str) -> str:
    return re.sub(r"[\s-]", "", number or "")


def card_brand(digits: str) -> Brand | None:
    for brand in BRANDS:
        for low, high in brand.ranges:
            head = digits[:len(low)]
            if len(head) == len(low) and head.isdigit() and int(low) <= int(head) <= int(high):
                return brand
    return None


def luhn(digits: str) -> bool:
    if not digits.isdigit() or len(digits) < 12:
        return False
    total = 0
    for position, char in enumerate(reversed(digits)):
        value = int(char)
        if position % 2:
            value = value * 2 - 9 if value * 2 > 9 else value * 2
        total += value
    return total % 10 == 0


def expiry_problem(text: str, now: float) -> str | None:
    match = re.fullmatch(r"\s*(\d{2})\s*/\s*(\d{2})\s*", text or "")
    if not match:
        return "Срок действия укажите в формате ММ/ГГ"
    month, year = int(match.group(1)), 2000 + int(match.group(2))
    if not 1 <= month <= 12:
        return "Месяц срока действия — от 01 до 12"
    today = time.localtime(now)
    if (year, month) < (today.tm_year, today.tm_mon):
        return "Срок действия карты истёк"
    if year > today.tm_year + 10:
        return "Год срока действия слишком далеко — проверьте ввод"
    return None


def check_card(number: str, expiry: str, cvv: str, holder: str, now: float) -> Brand:
    digits = card_digits(number)
    if not digits.isdigit():
        raise Refused("Номер карты должен состоять из цифр")
    brand = card_brand(digits)
    if brand is None:
        raise Refused("Платёжная система карты не поддерживается")
    if len(digits) not in brand.lengths:
        raise Refused("Неверная длина номера карты — проверьте, все ли цифры введены")
    if not luhn(digits):
        raise Refused("Номер карты не проходит контрольную проверку — проверьте цифры")
    problem = expiry_problem(expiry, now)
    if problem:
        raise Refused(problem)
    if not ((cvv or "").isdigit() and len(cvv) == brand.cvv):
        raise Refused(f"Код {'CID' if brand.code == 'amex' else 'CVV'} — {brand.cvv} цифры")
    if holder and not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,60}", holder.strip()):
        raise Refused("Имя держателя вводится латиницей, как на карте")
    return brand


def masked(digits: str) -> str:
    return digits[:6] + "*" * (len(digits) - 10) + digits[-4:]


def sandbox_credentials(data_dir: Path) -> tuple[str, str]:
    shop = os.environ.get("VOLTPLAN_BEPAID_SHOP", "").strip()
    key = os.environ.get("VOLTPLAN_BEPAID_KEY", "").strip()
    stored = data_dir / "bepaid.key"
    if not (shop and key) and stored.exists():
        lines = stored.read_text(encoding="utf-8").split()
        if len(lines) >= 2:
            shop, key = lines[0], lines[1]
    return shop or SANDBOX_SHOP, key or SANDBOX_KEY


class Sandbox:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def request(self, method: str, url: str, payload: dict | None = None) -> dict:
        shop, key = sandbox_credentials(self.data_dir)
        token = base64.b64encode(f"{shop}:{key}".encode()).decode()
        body = json.dumps(payload).encode() if payload is not None else None
        call = urllib.request.Request(url, data=body, method=method, headers={
            "Content-Type": "application/json", "Accept": "application/json", "X-API-Version": "2",
            "Authorization": f"Basic {token}"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(call, timeout=30) as response:
                    return json.loads(response.read() or b"{}")
            except urllib.error.HTTPError as error:
                try:
                    return json.loads(error.read() or b"{}")
                except ValueError:
                    return {}
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        return {}

    def start(self, payment_id: str, cents: int, description: str, back: str) -> dict:
        answer = self.request("POST", SANDBOX_URL, {"checkout": {
            "transaction_type": "payment", "test": True,
            "order": {"amount": cents, "currency": "USD", "description": description[:255],
                      "tracking_id": payment_id},
            "settings": {"return_url": back, "success_url": back, "decline_url": back, "fail_url": back,
                         "cancel_url": back, "language": "ru", "auto_return": 2,
                         "customer_fields": {"visible": []}},
        }}).get("checkout", {})
        return {"token": answer.get("token", ""), "url": answer.get("redirect_url", "")}

    def status(self, token: str) -> dict:
        checkout = self.request("GET", f"{SANDBOX_URL}/{token}").get("checkout", {})
        gateway = checkout.get("gateway_response") or {}
        payment = gateway.get("payment") or gateway.get("transaction") or checkout.get("payment") or {}
        card = payment.get("credit_card") or checkout.get("credit_card") or {}
        last = str(card.get("last_4") or "")
        first = str(card.get("first_1") or "")
        state = str(payment.get("status") or checkout.get("status") or "").lower()
        result = {"brand": str(card.get("brand") or ""), "pan": first + "*" * (15 - len(first)) + last if last
                  else "", "message": payment.get("message") or ""}
        if state in ("successful", "success", "paid", "completed"):
            return {**result, "state": "paid"}
        if state in ("failed", "error"):
            return {**result, "state": "failed"}
        if state in ("declined", "incomplete") or (checkout.get("finished") and not state):
            return {**result, "state": "declined"}
        return {**result, "state": "pending"}


class Billing:
    def __init__(self, store: Store, users: Users, notify) -> None:
        self.store = store
        self.users = users
        self.notify = notify
        self.sandbox = Sandbox(store.data_dir)

    def payment(self, user: User, payment_id: str):
        row = self.store.work.execute("SELECT * FROM payments WHERE id = ? AND user_id = ?",
                                      (payment_id, user.id)).fetchone()
        if row is None:
            raise Refused("Счёт не найден", 404)
        return row

    def view(self, row) -> dict:
        return {"id": row["id"], "tier": row["tier"], "title": tiers.TIERS[row["tier"]].title,
                "amount_usd": row["amount_cents"] / 100, "provider": row["provider"], "status": row["status"],
                "card": row["pan_masked"], "brand": row["brand"], "created": row["created"],
                "finished": row["finished"], "message": row["message"]}

    def checkout(self, user: User, tier: str, provider: str, back: str) -> dict:
        if tier not in ("pro", "max"):
            raise Refused("Оплачиваются тарифы «Профессионал» и «Максимум»")
        if provider not in ("demo", "bepaid"):
            raise Refused("Способ оплаты: demo или bepaid")
        chosen = tiers.TIERS[tier]
        current = tiers.effective(user)
        if current.code != "demo" and user.tier_until is None:
            raise Refused(f"Тариф «{current.title}» выдан администратором без срока, оплата не нужна. Чтобы сменить "
                          "тариф, обратитесь к администратору.", 409)
        if tiers.ORDER.index(current.code) > tiers.ORDER.index(tier):
            ends = time.strftime("%d.%m.%Y", time.localtime(user.tier_until))
            raise Refused(f"У вас действует тариф «{current.title}» до {ends}. Тариф «{chosen.title}» можно оплатить "
                          "после его окончания.", 409)
        payment_id = uuid.uuid4().hex
        now = time.time()
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE payments SET status = 'failed', finished = ?, message = ? "
                       "WHERE user_id = ? AND status = 'pending' AND created < ?",
                       (now, "Счёт не оплачен вовремя", user.id, now - PENDING_SECONDS))
            db.execute("INSERT INTO payments (id, user_id, tier, amount_cents, provider, status, created) "
                       "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                       (payment_id, user.id, tier, int(round(chosen.price_usd * 100)), provider, now))
        if provider == "demo":
            return {"mode": "form", "payment": self.view(self.payment(user, payment_id))}
        started = self.sandbox.start(payment_id, int(round(chosen.price_usd * 100)),
                                     f"VoltPlan — тариф «{chosen.title}», {tiers.PERIOD_DAYS} дней",
                                     f"{back}?await={payment_id}")
        if not (started["token"] and started["url"]):
            with self.store.writing(self.store.work) as db:
                db.execute("UPDATE payments SET provider = 'demo' WHERE id = ?", (payment_id,))
            return {"mode": "form", "fallback": True, "payment": self.view(self.payment(user, payment_id))}
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE payments SET ext_ref = ? WHERE id = ?", (started["token"], payment_id))
        return {"mode": "redirect", "url": started["url"], "payment": self.view(self.payment(user, payment_id))}

    def confirm(self, user: User, payment_id: str, number: str, expiry: str, cvv: str, holder: str) -> dict:
        row = self.payment(user, payment_id)
        if row["provider"] != "demo":
            raise Refused("Этот счёт оплачивается на странице bePaid", 409)
        if row["status"] == "paid":
            return self.view(row)
        if row["status"] != "pending":
            raise Refused("Счёт закрыт — создайте новый", 409)
        now = time.time()
        brand = check_card(number, expiry, cvv, holder, now)
        digits = card_digits(number)
        if digits == DECLINED_CARD:
            self.finish(row, "declined", masked(digits), brand.title, "Платёж отклонён банком")
            raise Refused("Платёж отклонён банком", 402)
        self.finish(row, "paid", masked(digits), brand.title, "")
        return self.view(self.payment(user, payment_id))

    def poll(self, user: User, payment_id: str) -> dict:
        row = self.payment(user, payment_id)
        if row["status"] != "pending" or row["provider"] != "bepaid":
            return self.view(row)
        found = self.sandbox.status(row["ext_ref"] or "")
        if found["state"] != "pending":
            self.finish(row, found["state"], found["pan"], found["brand"], found["message"])
        return self.view(self.payment(user, payment_id))

    def finish(self, row, status: str, card: str, brand: str, message: str) -> bool:
        now = time.time()
        with self.store.writing(self.store.work) as db:
            changed = db.execute("UPDATE payments SET status = ?, pan_masked = ?, brand = ?, message = ?, finished = ? "
                                 "WHERE id = ? AND status = 'pending'",
                                 (status, card, brand, message, now, row["id"])).rowcount
            if changed == 0 or status != "paid":
                return False
            profile = db.execute("SELECT tier, tier_until FROM profiles WHERE user_id = ?",
                                 (row["user_id"],)).fetchone()
            ends = profile["tier_until"]
            known = profile["tier"] in tiers.TIERS and profile["tier"] != "demo"
            active = profile["tier"] if known and (ends is None or ends > now) else "demo"
            paid = tiers.TIERS[row["tier"]]
            tier, until, note = row["tier"], now + PERIOD_SECONDS, f"Тариф «{paid.title}» оплачен"
            if active != "demo" and ends is None:
                tier, until = active, None
                note = (f"Тариф «{paid.title}» оплачен, но у вас тариф «{tiers.TIERS[active].title}» без срока: "
                        "тариф не изменился, обратитесь к администратору.")
            elif tiers.ORDER.index(active) > tiers.ORDER.index(row["tier"]):
                higher = tiers.TIERS[active]
                credit = PERIOD_SECONDS * row["amount_cents"] / round(higher.price_usd * 100)
                tier, until = active, ends + credit
                note = (f"Тариф «{paid.title}» оплачен, когда уже действовал «{higher.title}»: "
                        f"срок «{higher.title}» продлён на {credit / 86400:.0f} дн.")
            elif active == row["tier"]:
                until = ends + PERIOD_SECONDS
            elif active != "demo":
                lower = tiers.TIERS[active]
                credit = (ends - now) * round(lower.price_usd * 100) / row["amount_cents"]
                until = now + PERIOD_SECONDS + credit
                note = (f"Тариф «{paid.title}» оплачен; оставшиеся дни «{lower.title}» зачтены: "
                        f"срок продлён на {credit / 86400:.0f} дн.")
            if note != f"Тариф «{paid.title}» оплачен":
                db.execute("UPDATE payments SET message = ? WHERE id = ?", (note, row["id"]))
            db.execute("UPDATE profiles SET tier = ?, tier_until = ? WHERE user_id = ?", (tier, until, row["user_id"]))
        owner = self.users.get(row["user_id"])
        title = tiers.TIERS[row["tier"]].title
        self.store.audit(owner.id, "оплата тарифа", f"{title}, {row['amount_cents'] / 100:.2f} USD")
        self.notify(owner.id, "payment", note, "/account#payments")
        return True

    def history(self, user: User) -> list[dict]:
        rows = self.store.work.execute("SELECT * FROM payments WHERE user_id = ? ORDER BY created DESC LIMIT 50",
                                       (user.id,)).fetchall()
        return [self.view(row) for row in rows]

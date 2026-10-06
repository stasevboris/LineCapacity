import { site } from './api.js';
import { $, h } from './dom.js';
import { language, t } from './i18n.js';
import { startSite } from './site.js';

const POLL_MS = 3000;
const POLL_TIMES = 40;
const BRANDS = [
  ['МИР', [['2200', '2204']]], ['БЕЛКАРТ', [['9112', '9112']]], ['American Express', [['34', '34'], ['37', '37']]],
  ['UnionPay', [['62', '62']]], ['Mastercard', [['51', '55'], ['2221', '2720']]],
  ['Maestro', [['50', '50'], ['56', '69']]], ['Visa', [['4', '4']]],
];

const view = { tier: null, payment: null };

function brandOf(digits) {
  for (const [name, ranges] of BRANDS) {
    for (const [low, high] of ranges) {
      const head = digits.slice(0, low.length);
      if (head.length === low.length && Number(head) >= Number(low) && Number(head) <= Number(high)) return name;
    }
  }
  return '';
}

function when(seconds) {
  const code = { ru: 'ru-RU', en: 'en-GB', zh: 'zh-CN' }[language()] || 'ru-RU';
  return new Intl.DateTimeFormat(code, { dateStyle: 'long' }).format(new Date(seconds * 1000));
}

function showOrder(tier) {
  $('order').replaceChildren(
    h('div', { class: 'sum-row' }, h('span', { class: 'k' }, t('Тариф')), h('span', {}, t(tier.title))),
    h('div', { class: 'sum-row' }, h('span', { class: 'k' }, t('Срок действия')),
      h('span', {}, t('30 дней'), ' ', h('span', { class: 'k' }, t('(продлевается)')))),
    h('div', { class: 'sum-row' }, h('span', { class: 'k' }, t('К оплате')),
      h('span', { class: 'sum-total', translate: 'no' }, `$${tier.price_usd.toFixed(2)}`)));
  $('btn-pay').textContent = t('Оплатить {sum}', { sum: `$${tier.price_usd.toFixed(2)}` });
}

async function success(payment) {
  const me = await site.get('/api/auth/me');
  $('methods').hidden = true;
  $('step-pay').className = 'step-dot done';
  $('step-pay').querySelector('i').textContent = '✓';
  $('step-done').className = 'step-dot now';
  const box = $('outcome');
  box.hidden = false;
  box.className = 'pay-outcome outcome good';
  box.replaceChildren(h('div', { class: 'ic' }, '✓'), h('h3', {}, t('Оплата прошла')),
    h('p', { class: 'muted' }, t('Тариф «{tier}» действует до {date}.', { tier: t(payment.title),
      date: when(me.tier_until) })),
    payment.card ? h('p', { class: 'muted', translate: 'no' }, `${payment.brand} ${payment.card}`) : null,
    h('div', { class: 'pay-actions' }, h('a', { class: 'btn btn-primary', href: '/app' }, t('Открыть редактор')),
      h('a', { class: 'btn btn-ghost', href: '/account#payments' }, t('Личный кабинет'))));
}

function failure(message) {
  $('methods').hidden = true;
  const box = $('outcome');
  box.hidden = false;
  box.className = 'pay-outcome outcome bad';
  box.replaceChildren(h('div', { class: 'ic' }, '✕'), h('h3', {}, t('Оплата не прошла')),
    h('p', { class: 'muted' }, t(message)),
    h('div', { class: 'pay-actions' }, h('a', { class: 'btn btn-primary', href: `/pay?tier=${view.tier || 'pro'}` },
      t('Попробовать ещё раз'))));
}

async function checkout(provider) {
  const answer = await site.post('/api/billing/checkout', { tier: view.tier, provider });
  view.payment = answer.payment;
  return answer;
}

function formatNumber(input) {
  const digits = input.value.replace(/\D/g, '').slice(0, 19);
  input.value = digits.replace(/(\d{4})(?=\d)/g, '$1 ');
  $('card-brand').textContent = brandOf(digits);
  $('card-brand').classList.toggle('on', Boolean(brandOf(digits)));
}

function formatExpiry(input) {
  const digits = input.value.replace(/\D/g, '').slice(0, 4);
  input.value = digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
}

async function payByCard(event) {
  event.preventDefault();
  $('card-error').textContent = '';
  $('btn-pay').disabled = true;
  try {
    if (!view.payment || view.payment.provider !== 'demo' || view.payment.status !== 'pending') {
      await checkout('demo');
    }
    const paid = await site.post('/api/billing/confirm', {
      payment: view.payment.id, number: $('card-number').value, expiry: $('card-expiry').value,
      cvv: $('card-cvv').value, holder: $('card-holder').value,
    });
    await success(paid);
  } catch (error) {
    if (error.status === 402) failure(error.message);
    else $('card-error').textContent = error.message;
  } finally {
    $('btn-pay').disabled = false;
  }
}

async function payByGateway() {
  $('bepaid-error').textContent = '';
  $('btn-bepaid').disabled = true;
  try {
    const answer = await checkout('bepaid');
    if (answer.mode === 'redirect') {
      location.href = answer.url;
      return;
    }
    document.querySelector('input[name="method"][value="demo"]').checked = true;
    switchMethod();
    $('card-error').textContent = t('Тестовая среда bePaid сейчас недоступна — оплатите картой здесь.');
  } catch (error) {
    $('bepaid-error').textContent = error.message;
  } finally {
    $('btn-bepaid').disabled = false;
  }
}

function switchMethod() {
  const method = document.querySelector('input[name="method"]:checked').value;
  $('card-form').hidden = method !== 'demo';
  $('bepaid-box').hidden = method !== 'bepaid';
}

async function waitFor(paymentId) {
  $('methods').hidden = true;
  const box = $('outcome');
  box.hidden = false;
  box.className = 'pay-outcome outcome';
  box.replaceChildren(h('h3', {}, t('Проверяем оплату…')), h('p', { class: 'muted' },
    t('Ответ bePaid обычно приходит за несколько секунд.')));
  for (let attempt = 0; attempt < POLL_TIMES; attempt += 1) {
    let payment;
    try {
      payment = await site.get(`/api/billing/poll/${paymentId}`);
    } catch (error) {
      failure(error.message);
      return;
    }
    view.tier = payment.tier;
    if (payment.status === 'paid') {
      await success(payment);
      return;
    }
    if (payment.status !== 'pending') {
      failure(payment.message || 'Платёж отклонён');
      return;
    }
    await new Promise((resolve) => { setTimeout(resolve, POLL_MS); });
  }
  failure('Ответ от bePaid не получен. Проверьте историю платежей в личном кабинете позже.');
}

await startSite();
const params = new URLSearchParams(location.search);
const waiting = params.get('await');
if (waiting) {
  waitFor(waiting);
} else {
  view.tier = ['pro', 'max'].includes(params.get('tier')) ? params.get('tier') : 'pro';
  const { tiers } = await site.get('/api/tiers');
  showOrder(tiers.find((tier) => tier.code === view.tier));
  document.querySelectorAll('input[name="method"]').forEach((input) => input.addEventListener('change', switchMethod));
  $('card-number').addEventListener('input', (event) => formatNumber(event.target));
  $('card-expiry').addEventListener('input', (event) => formatExpiry(event.target));
  $('card-cvv').addEventListener('input', (event) => { event.target.value = event.target.value.replace(/\D/g, ''); });
  $('card-holder').addEventListener('input', (event) => {
    event.target.value = event.target.value.replace(/[^A-Za-z .'-]/g, '').toUpperCase();
  });
  $('card-form').addEventListener('submit', payByCard);
  $('btn-bepaid').addEventListener('click', payByGateway);
  switchMethod();
}

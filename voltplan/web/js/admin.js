import { site } from './api.js';
import { $, formatExact, h, parseNumber, toast } from './dom.js';
import { language, loadLanguage, t, translatePage } from './i18n.js';
import { TIERS, applyTheme, logout, session, whoAmI } from './session.js';
import { languageSwitch } from './language.js';

const PANES = ['overview', 'users', 'payments', 'journal', 'broadcast', 'reference', 'price'];
const CURVES = [
  ['home_summer_curve', 'Бытовой без КИЭ, лето'], ['home_winter_curve', 'Бытовой без КИЭ, зима'],
  ['electric_home_summer_curve', 'Бытовой с КИЭ, лето'], ['electric_home_winter_curve', 'Бытовой с КИЭ, зима'],
];
const TIER_COLORS = { demo: '#94a3b8', pro: '#2563eb', max: '#0e7490' };
const DAY = 86400;

function when(seconds) {
  if (!seconds) return '—';
  const code = { ru: 'ru-RU', en: 'en-GB', zh: 'zh-CN' }[language()] || 'ru-RU';
  return new Intl.DateTimeFormat(code, { dateStyle: 'short', timeStyle: 'short' }).format(new Date(seconds * 1000));
}

function day(seconds) {
  return seconds ? new Date(seconds * 1000).toISOString().slice(0, 10) : '';
}

function money(value) {
  return `$${value.toFixed(2)}`;
}

async function act(promise, done) {
  try {
    const result = await promise;
    if (done) toast(t(done));
    return result;
  } catch (error) {
    toast(error.message, 'bad');
    return null;
  }
}

function table(head, rows) {
  if (!rows.length) return h('p', { class: 'empty-note' }, t('Записей нет.'));
  return h('table', {}, h('thead', {}, h('tr', {}, head.map((name) => h('th', {}, t(name))))), h('tbody', {}, rows));
}

function tierTag(code) {
  return h('span', { class: `tag ${code}` }, t(TIERS[code] || code));
}

function userRow(person) {
  const tier = h('select', { 'aria-label': t('Тариф') }, Object.entries(TIERS).map(([code, name]) =>
    h('option', { value: code, selected: code === person.stored_tier }, t(name))));
  const until = h('input', { type: 'date', value: day(person.tier_until), 'aria-label': t('Срок') });
  const save = h('button', { class: 'btn sm primary', type: 'button' }, t('Сохранить'));
  save.addEventListener('click', async () => {
    const stamp = until.value ? new Date(`${until.value}T23:59:59`).getTime() / 1000 : null;
    if (await act(site.put(`/api/admin/users/${person.id}/tier`, { tier: tier.value, until: stamp }),
      'Тариф изменён')) loadUsers();
  });
  const admin = h('input', { type: 'checkbox', checked: person.is_admin, 'aria-label': t('Администратор') });
  admin.addEventListener('change', async () => {
    if (!await act(site.put(`/api/admin/users/${person.id}/admin`, { is_admin: admin.checked }), 'Права изменены')) {
      admin.checked = !admin.checked;
    }
  });
  return h('tr', { 'data-user': person.id },
    h('td', { translate: 'no' }, h('div', { class: 'who-cell' }, h('b', {}, person.name || '—'),
      h('small', {}, person.email))),
    h('td', {}, tierTag(person.tier)),
    h('td', {}, h('div', { class: 'row' }, tier, until, save)),
    h('td', {}, String(person.projects)),
    h('td', {}, when(person.created)),
    h('td', {}, when(person.last_login)),
    h('td', {}, h('label', { class: 'row' }, admin, h('span', { class: `tag ${person.is_admin ? 'admin' : 'user'}` },
      t(person.is_admin ? 'администратор' : 'пользователь')))));
}

async function loadUsers() {
  const people = await act(site.get(`/api/admin/users?query=${encodeURIComponent($('users-query').value)}`));
  if (!people) return;
  $('users').replaceChildren(table(['Пользователь', 'Тариф', 'Тариф и срок', 'Проектов', 'Регистрация',
    'Последний вход', 'Права'], people.map(userRow)));
}

function tierBars(people) {
  const counts = { demo: 0, pro: 0, max: 0 };
  people.forEach((person) => { counts[person.tier] = (counts[person.tier] || 0) + 1; });
  const top = Math.max(1, ...Object.values(counts));
  return Object.keys(TIERS).map((code) => h('div', { class: 'bar-row' }, h('span', {}, t(TIERS[code])),
    h('div', { class: 'track' }, h('i', { style: `width:${Math.round((counts[code] / top) * 100)}%;`
      + `background:${TIER_COLORS[code]}` })), h('b', {}, String(counts[code]))));
}

function registrationBars(people) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const buckets = new Array(14).fill(0);
  people.forEach((person) => {
    const date = new Date(person.created * 1000);
    date.setHours(0, 0, 0, 0);
    const ago = Math.round((today - date) / (DAY * 1000));
    if (ago >= 0 && ago < 14) buckets[13 - ago] += 1;
  });
  const top = Math.max(1, ...buckets);
  return [h('div', { class: 'reg-bars' }, buckets.map((count) => h('div', { title: String(count) },
    h('i', { style: `height:${Math.round((count / top) * 70) + 2}px` })))),
  h('div', { class: 'reg-scale' }, h('span', {}, t('14 дней назад')), h('span', {}, t('сегодня')))];
}

async function loadOverview() {
  const people = await act(site.get('/api/admin/users'));
  if (!people) return;
  $('s-users').textContent = String(people.length);
  $('s-admins').textContent = String(people.filter((person) => person.is_admin).length);
  $('s-pro').textContent = String(people.filter((person) => person.tier === 'pro').length);
  $('s-max').textContent = String(people.filter((person) => person.tier === 'max').length);
  $('tier-chart').replaceChildren(...tierBars(people));
  $('reg-chart').replaceChildren(...registrationBars(people));
}

async function loadPayments() {
  const payments = await act(site.get('/api/admin/payments'));
  if (!payments) return;
  $('all-payments').replaceChildren(table(['Дата', 'Пользователь', 'Тариф', 'Сумма', 'Способ', 'Карта', 'Состояние'],
    payments.map((item) => h('tr', {}, h('td', {}, when(item.created)), h('td', { translate: 'no' }, item.user),
      h('td', {}, tierTag(item.tier)), h('td', { translate: 'no' }, money(item.amount_usd)),
      h('td', {}, item.provider), h('td', { class: 'mono', translate: 'no' }, item.card || '—'),
      h('td', {}, item.status)))));
}

async function loadJournal() {
  const rows = await act(site.get(`/api/admin/journal?query=${encodeURIComponent($('journal-query').value)}`));
  if (!rows) return;
  $('journal').replaceChildren(table(['Время', 'Пользователь', 'Действие', 'Подробности'], rows.map((row) =>
    h('tr', {}, h('td', {}, when(row.created)), h('td', { translate: 'no' }, row.user || '—'),
      h('td', {}, t(row.action)),
      h('td', { translate: 'no' }, row.details)))));
}

async function loadBroadcast() {
  const people = await act(site.get('/api/admin/users'));
  if (!people) return;
  $('broadcast-user').replaceChildren(h('option', { value: '' }, t('Все пользователи')),
    ...people.map((person) => h('option', { value: person.id, translate: 'no' }, `${person.name} — ${person.email}`)));
}

const reference = { fields: [], values: {}, defaults: {} };

function referenceRow(item) {
  const current = reference.values[item.key];
  const control = item.kind === 'flag'
    ? h('input', { type: 'checkbox', name: item.key, checked: Boolean(current) })
    : h('input', { class: 'tf-input', name: item.key, value: formatExact(current), inputmode: 'decimal' });
  const changed = current !== reference.defaults[item.key];
  return h('div', { class: `setting-line${changed ? ' changed' : ''}` },
    h('label', {}, item.unit ? `${t(item.label)}, ${t(item.unit)}` : t(item.label)), control);
}

async function loadReference() {
  const [form, stored] = await Promise.all([act(site.get('/api/calc/settings')),
    act(site.get('/api/admin/reference'))]);
  if (!form || !stored) return;
  Object.assign(reference, { fields: form.fields, values: stored.values, defaults: form.defaults });
  const groups = new Map();
  for (const item of form.fields) {
    if (!groups.has(item.group)) groups.set(item.group, []);
    groups.get(item.group).push(item);
  }
  $('reference-fields').replaceChildren(...[...groups.entries()].map(([group, items]) =>
    h('fieldset', { class: 'fieldset' }, h('legend', {}, t(group)), items.map(referenceRow))));
  $('reference-curves').replaceChildren(...CURVES.map(([key, name]) => h('div', {},
    h('label', {}, t(name)), h('textarea', { class: 'tf-input curve', name: key, rows: 3 },
      stored.values[key].map((value) => formatExact(value)).join(' ')))));
}

function readReference() {
  const values = {};
  for (const item of reference.fields) {
    const control = document.querySelector(`#reference-fields [name="${item.key}"]`);
    values[item.key] = item.kind === 'flag' ? control.checked : parseNumber(control.value);
    if (item.kind !== 'flag' && !Number.isFinite(values[item.key])) {
      throw new Error(t('Неверное значение: {name}', { name: t(item.label) }));
    }
  }
  for (const [key, name] of CURVES) {
    const text = document.querySelector(`#reference-curves [name="${key}"]`).value.trim();
    const points = text.split(/\s+/).map(parseNumber);
    if (points.length !== 48 || points.some((value) => !Number.isFinite(value))) {
      throw new Error(t('График «{name}»: нужно 48 чисел', { name: t(name) }));
    }
    values[key] = points;
  }
  return values;
}

function showPrice(price) {
  $('price-now').textContent = formatExact(price);
  $('kpi-small').textContent = money(price * 1000);
  $('kpi-large').textContent = money(price * 10000);
}

function previewPrice() {
  const price = parseNumber($('price-value').value);
  $('price-preview').textContent = Number.isFinite(price) && price >= 0
    ? t('1 000 кВт·ч потерь обойдутся в {sum} в год', { sum: money(price * 1000) })
    : t('Введите число, например 0,08');
}

async function loadPrice() {
  const data = await act(site.get('/api/admin/options'));
  if (!data) return;
  $('price-value').value = formatExact(data.energy_price_usd);
  showPrice(data.energy_price_usd);
  previewPrice();
}

const LOADERS = { overview: loadOverview, users: loadUsers, payments: loadPayments, journal: loadJournal,
  broadcast: loadBroadcast, reference: loadReference, price: loadPrice };

function show() {
  const wanted = location.hash.replace('#', '');
  const pane = PANES.includes(wanted) ? wanted : 'overview';
  for (const name of PANES) $(`pane-${name}`).hidden = name !== pane;
  document.querySelectorAll('#admin-nav a[data-pane]').forEach((link) => {
    link.classList.toggle('active', link.dataset.pane === pane);
    link.setAttribute('aria-current', link.dataset.pane === pane ? 'page' : 'false');
  });
  LOADERS[pane]();
}

function bind() {
  $('users-search').addEventListener('submit', (event) => { event.preventDefault(); loadUsers(); });
  $('journal-search').addEventListener('submit', (event) => { event.preventDefault(); loadJournal(); });
  $('broadcast-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const target = $('broadcast-user').value;
    const sent = await act(site.post('/api/admin/broadcast', { text: $('broadcast-text').value,
      user_id: target ? Number(target) : null }));
    if (sent) {
      toast(t('Уведомление отправлено: {count}', { count: sent.sent }));
      $('broadcast-text').value = '';
    }
  });
  $('reference-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    let values;
    try {
      values = readReference();
    } catch (error) {
      toast(error.message, 'bad');
      return;
    }
    if (await act(site.put('/api/admin/reference', { values }), 'Справочник сохранён')) loadReference();
  });
  $('reference-reset').addEventListener('click', async () => {
    if (!confirm(t('Вернуть исходные значения справочника типовых нагрузок?'))) return;
    if (await act(site.remove('/api/admin/reference'), 'Справочник возвращён к исходным значениям')) loadReference();
  });
  $('price-value').addEventListener('input', previewPrice);
  $('price-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    $('price-error').textContent = '';
    const price = parseNumber($('price-value').value);
    try {
      const saved = await site.put('/api/admin/options', { energy_price_usd: price });
      showPrice(saved.energy_price_usd ?? price);
      toast(t('Стоимость сохранена'));
    } catch (error) {
      $('price-error').textContent = error.message;
    }
  });
  window.addEventListener('hashchange', show);
}

applyTheme('light');
const user = await whoAmI();
session.user = user;
await loadLanguage(user ? user.language : null);
$('lang-slot').replaceChildren(languageSwitch(() => Boolean(session.user)));
$('admin-out').addEventListener('click', logout);
translatePage();
if (user) $('admin-who').textContent = user.email;
if (user && user.is_admin) {
  $('desk').hidden = false;
  bind();
  show();
} else {
  $('denied').hidden = false;
}

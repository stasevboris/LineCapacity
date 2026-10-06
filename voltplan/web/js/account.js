import { site } from './api.js';
import { $, formatNumber, h, parseNumber } from './dom.js';
import { LANGUAGES, language, remember, t } from './i18n.js';
import { act, askText, button, dialog, empty, role, when } from './panel.js';
import { logout, refreshBell, session } from './session.js';
import { startSite } from './site.js';

const COLLAB = { teams: 'teams', friends: 'friends', invitations: 'invitations', messages: 'chat' };
const LEGACY = { tariff: 'payments' };
const STATUS_PAID = { paid: 'оплачен', pending: 'ожидает оплаты', declined: 'отклонён', failed: 'не выполнен' };
const STATUS_CLASS = { paid: 'st-paid', pending: 'st-wait', declined: 'st-failed', failed: 'st-failed' };
const PROVIDERS = { demo: 'карта (демонстрация)', bepaid: 'bePaid (тестовая среда)' };
const DAY = 86400;

const view = { archived: false };

function initials(user) {
  const source = (user.name || user.email || '·').trim();
  const words = source.split(/[\s@._-]+/).filter(Boolean);
  return ((words[0] || '·')[0] + (words[1] ? words[1][0] : '')).toUpperCase();
}

function showProfile() {
  const user = session.user;
  $('avatar').textContent = initials(user);
  $('acc-email').textContent = user.email;
  $('who-name').textContent = user.name || '';
  $('kv-email').textContent = user.email;
  $('kv-role').textContent = t(user.is_admin ? 'Администратор' : 'Пользователь');
  $('kv-created').textContent = when(user.created, 'date');
  $('profile-name').value = user.name;
  $('profile-language').replaceChildren(...Object.entries(LANGUAGES).map(([code, name]) =>
    h('option', { value: code, selected: code === language() }, name)));
  $('admin-link').hidden = !user.is_admin;
}

async function showTier() {
  const mine = await act(site.get('/api/account/tier'));
  if (!mine) return;
  const tier = mine.tier;
  $('tier-name').textContent = t(tier.title);
  $('tier-chip').className = `tier-chip t-${tier.code}`;
  $('tier-chip').dataset.tier = tier.code;
  const left = mine.until ? Math.max(0, Math.ceil((mine.until - Date.now() / 1000) / DAY)) : null;
  $('term').hidden = left === null;
  $('no-term').hidden = !(tier.code !== 'demo' && left === null);
  if (left !== null) {
    $('tier-until').textContent = when(mine.until, 'date');
    $('days-left').textContent = String(left);
    $('term-bar').style.width = `${Math.min(100, (left / 30) * 100)}%`;
  }
  $('tier-renew').hidden = tier.code === 'demo';
  $('tier-renew').href = `/pay?tier=${tier.code}`;
  $('tier-cta').textContent = t(tier.code === 'max' ? 'Сравнить тарифы' : 'Изменить тариф');
}

async function loadProjects() {
  const list = await act(site.get(`/api/projects?archived=${view.archived}`));
  if (!list) return;
  $('projects-title').textContent = t(view.archived ? 'Проекты в архиве' : 'Проекты');
  if (!list.length) {
    const note = view.archived ? 'В архиве пусто.' : 'Проектов пока нет — создайте первый.';
    $('projects-list').replaceChildren(empty(note));
    return;
  }
  const head = h('tr', {}, ['Название', 'Роль', 'Владелец', 'Вариантов', 'Изменён', ''].map((name, index) =>
    h('th', { class: index === 3 ? 'num' : null }, name ? t(name) : '')));
  const rows = list.map((project) => {
    const owner = project.role === 'owner';
    const actions = [h('a', { class: 'btn btn-primary btn-small', href: `/app?project=${project.id}` }, t('Открыть'))];
    if (owner) {
      actions.push(button('Переименовать', () => renameProject(project)));
      actions.push(button('Команде…', () => shareProject(project)));
      actions.push(button(project.archived ? 'Вернуть' : 'В архив', () => archiveProject(project)));
      actions.push(button('Удалить', () => deleteProject(project), 'btn btn-danger btn-small'));
    }
    return h('tr', { 'data-project': project.id },
      h('td', { translate: 'no' }, h('a', { href: `/app?project=${project.id}` }, project.name)),
      h('td', {}, role(project.role)),
      h('td', { translate: 'no' }, project.owner),
      h('td', { class: 'num' }, String(project.variants)),
      h('td', {}, when(project.updated)),
      h('td', {}, h('div', { class: 'row-actions' }, actions)));
  });
  $('projects-list').replaceChildren(h('table', { class: 'pay-table' }, h('thead', {}, head), h('tbody', {}, rows)));
}

async function renameProject(project) {
  const name = await askText('Переименовать проект', 'Новое название', project.name, 'Переименовать');
  if (!name) return;
  if (await act(site.patch(`/api/projects/${project.id}`, { name }), 'Проект переименован')) loadProjects();
}

async function archiveProject(project) {
  const done = project.archived ? 'Проект возвращён из архива' : 'Проект убран в архив';
  if (await act(site.patch(`/api/projects/${project.id}`, { archived: !project.archived }), done)) loadProjects();
}

async function deleteProject(project) {
  const question = t('Удалить проект «{name}» со всеми вариантами? Это действие нельзя отменить.',
    { name: project.name });
  if (!confirm(question)) return;
  if (await act(site.remove(`/api/projects/${project.id}`), 'Проект удалён')) loadProjects();
}

async function shareProject(project) {
  const teams = await act(site.get('/api/teams'));
  const shared = await act(site.get(`/api/projects/${project.id}/shares`));
  if (!teams || !shared) return;
  const box = h('div');
  const draw = (current) => {
    const openIds = new Set(current.teams.map((team) => team.id));
    if (!teams.length) {
      box.replaceChildren(empty('Сначала создайте команду на странице «Совместная работа».'));
      return;
    }
    box.replaceChildren(h('ul', { class: 'mark-list' }, teams.map((team) => h('li', {},
      h('div', { class: 'who' }, h('b', { translate: 'no' }, team.name),
        h('small', {}, t('участников: {count}', { count: team.members.length }))),
      openIds.has(team.id)
        ? button('Закрыть доступ', async () => {
          const next = await act(site.remove(`/api/projects/${project.id}/shares/${team.id}`), 'Доступ закрыт');
          if (next) draw(next);
        }, 'btn btn-danger btn-small')
        : button('Открыть доступ', async () => {
          const next = await act(site.post(`/api/projects/${project.id}/shares`, { team: team.id }),
            'Проект открыт команде');
          if (next) draw(next);
        }, 'btn btn-primary btn-small')))));
  };
  draw(shared);
  dialog({ title: t('Доступ к проекту «{name}»', { name: project.name }), body: box });
}

async function loadNotes() {
  const data = await act(site.get('/api/notifications'));
  if (!data) return;
  $('count-notifications').textContent = String(data.unseen);
  $('count-notifications').hidden = data.unseen === 0;
  const rows = data.items.map((note) => h('li', { class: note.seen ? 'note' : 'note unseen', 'data-note': note.id },
    h('span', { class: 'note-dot', 'aria-hidden': 'true' }),
    h('div', { class: 'who' }, h('span', { class: 'note-text' }, t(note.text)), h('time', {}, when(note.created))),
    note.link ? button('Перейти', () => follow(note)) : null));
  $('notes').replaceChildren(rows.length ? h('ul', { class: 'note-list' }, rows) : empty('Уведомлений нет.'));
}

async function follow(note) {
  await act(site.post('/api/notifications/seen', { ids: [note.id] }));
  refreshBell();
  if (note.link.startsWith('/account#')) {
    loadNotes();
    location.hash = note.link.split('#')[1];
    reveal();
  } else {
    location.href = note.link;
  }
}

function paymentRow(item) {
  return h('tr', { 'data-payment': item.id },
    h('td', {}, when(item.created)),
    h('td', {}, t(item.title)),
    h('td', { class: 'num', translate: 'no' }, `$${item.amount_usd.toFixed(2)}`),
    h('td', {}, t(PROVIDERS[item.provider] || item.provider)),
    h('td', { translate: 'no' }, item.card ? `${item.brand} ${item.card}` : '—'),
    h('td', {}, h('span', { class: `st-pill ${STATUS_CLASS[item.status] || 'st-failed'}` },
      t(STATUS_PAID[item.status] || item.status))));
}

async function loadPayments() {
  const payments = await act(site.get('/api/billing/history'));
  if (!payments) return;
  if (!payments.length) {
    $('payments-list').replaceChildren(empty('Платежей пока нет.'));
    return;
  }
  const names = ['Дата', 'Тариф', 'Сумма', 'Способ', 'Карта', 'Состояние'];
  const head = h('tr', {}, names.map((name, index) => h('th', { class: index === 2 ? 'num' : null }, t(name))));
  $('payments-list').replaceChildren(h('table', { class: 'pay-table' }, h('thead', {}, head),
    h('tbody', {}, payments.map(paymentRow))));
}

function markRow(mark, kind) {
  const details = kind === 'lines'
    ? `Rф ${formatNumber(mark.r_phase_ohm_per_km, 4)} · R0 ${formatNumber(mark.r_neutral_ohm_per_km, 4)} Ом/км`
    : `Sн ${formatNumber(mark.sn_kva, 1)} кВА · Uк ${formatNumber(mark.uk_percent, 2)} %`;
  const who = h('div', { class: 'who' }, h('b', { translate: 'no' }, mark.type_name), h('small', {}, details));
  return h('li', { 'data-mark': mark.id }, who,
    button('Удалить', async () => {
      if (!confirm(t('Удалить марку «{name}»?', { name: mark.type_name }))) return;
      if (await act(site.remove(`/api/marks/${mark.id}`), 'Марка удалена')) loadMarks();
    }, 'btn btn-danger btn-small'));
}

async function loadMarks() {
  const marks = await act(site.get('/api/marks'));
  if (!marks) return;
  const rows = [...marks.lines.map((mark) => markRow(mark, 'lines')),
    ...marks.transformers.map((mark) => markRow(mark, 'transformers'))];
  $('own-marks').replaceChildren(rows.length ? h('ul', { class: 'mark-list' }, rows) : empty('Своих марок пока нет.'));
}

function value(id) {
  return parseNumber($(id).value);
}

async function addMark(kind, data, form) {
  if (await act(site.post('/api/marks', { kind, data }), 'Марка добавлена')) {
    form.reset();
    loadMarks();
  }
}

function say(id, text, good) {
  $(id).textContent = text;
  $(id).className = `msg ${good ? 'ok' : 'err'}`;
}

async function saveProfile(event) {
  event.preventDefault();
  const chosen = $('profile-language').value;
  try {
    session.user = await site.post('/api/account/profile', { name: $('profile-name').value, language: chosen });
  } catch (error) {
    say('profile-error', error.message, false);
    return;
  }
  if (chosen !== language()) {
    remember(chosen);
    location.reload();
    return;
  }
  say('profile-error', t('Профиль сохранён'), true);
  showProfile();
}

async function changePassword(event) {
  event.preventDefault();
  if ($('password-new').value !== $('password-repeat').value) {
    say('password-error', t('Пароли не совпадают'), false);
    return;
  }
  try {
    await site.post('/api/account/password', { current: $('password-current').value, new: $('password-new').value });
  } catch (error) {
    say('password-error', error.message, false);
    return;
  }
  event.target.reset();
  say('password-error', t('Пароль изменён'), true);
}

function reveal() {
  const wanted = location.hash.replace('#', '');
  const section = $(LEGACY[wanted] || wanted);
  if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function bind() {
  $('project-new').addEventListener('submit', async (event) => {
    event.preventDefault();
    const project = await act(site.post('/api/projects', { name: $('project-name').value }), 'Проект создан');
    if (project) { $('project-name').value = ''; loadProjects(); }
  });
  document.querySelectorAll('input[name="archived"]').forEach((input) => input.addEventListener('change', () => {
    view.archived = input.value === '1';
    loadProjects();
  }));
  $('notes-seen').addEventListener('click', async () => {
    if (await act(site.post('/api/notifications/seen', {}))) {
      loadNotes();
      refreshBell();
    }
  });
  $('line-mark').addEventListener('submit', (event) => {
    event.preventDefault();
    addMark('line', { type_name: $('lm-name').value, r_phase_ohm_per_km: value('lm-phase'),
      r_neutral_ohm_per_km: value('lm-zero') }, event.target);
  });
  $('transformer-mark').addEventListener('submit', (event) => {
    event.preventDefault();
    addMark('transformer', { type_name: $('tm-name').value, sn_kva: value('tm-rated'), px_kw: value('tm-idle'),
      pk_kw: value('tm-short'), uvn_kv: value('tm-high'), unn_kv: value('tm-low'), uk_percent: value('tm-impedance'),
      pbv_steps: Math.trunc(value('tm-steps')), pbv_percent: value('tm-step') }, event.target);
  });
  $('profile-form').addEventListener('submit', saveProfile);
  $('password-form').addEventListener('submit', changePassword);
  $('profile-logout').addEventListener('click', logout);
  window.addEventListener('hashchange', reveal);
}

const wanted = location.hash.replace('#', '');
if (COLLAB[wanted]) location.replace(`/collab#${COLLAB[wanted]}`);
const user = await startSite();
if (user && !COLLAB[wanted]) {
  bind();
  showProfile();
  await Promise.all([showTier(), loadProjects(), loadNotes(), loadPayments(), loadMarks()]);
  site.get('/api/invitations').then((invitations) => {
    const waiting = invitations.incoming.filter((item) => item.status === 'waiting').length;
    $('count-invitations').textContent = String(waiting);
    $('count-invitations').hidden = waiting === 0;
  }).catch(() => null);
  reveal();
}

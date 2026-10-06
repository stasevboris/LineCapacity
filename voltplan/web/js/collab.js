import { site } from './api.js';
import { $, h, toast } from './dom.js';
import { t } from './i18n.js';
import { ROLE_NAMES, STATUS_NAMES, act, button, empty, role, when } from './panel.js';
import { refreshBell, session } from './session.js';
import { startSite } from './site.js';

const CHAT_POLL_MS = 5000;
const FILE_ICON = 'M21 12.5 12.5 21a5 5 0 0 1-7-7l8-8a3.5 3.5 0 0 1 5 5l-8 8a2 2 0 0 1-3-3l7.5-7.5';
const view = { teams: [], friends: [], chat: null, lastMessage: -1 };

function avatar(name) {
  return h('span', { class: 'cw-ava', translate: 'no' }, (name || '·').trim().charAt(0).toUpperCase());
}

function status(code) {
  return h('span', { class: `cw-status ${code} status-${code}` }, t(STATUS_NAMES[code] || code));
}

function size(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function memberRow(team, member, owner) {
  const me = member.id === session.user.id;
  const tools = [];
  if (owner && !me) {
    const select = h('select', { 'aria-label': t('Роль') }, ['editor', 'reader'].map((name) =>
      h('option', { value: name, selected: member.role === name }, t(ROLE_NAMES[name]))));
    select.addEventListener('change', async () => {
      const path = `/api/teams/${team.id}/members/${member.id}`;
      if (await act(site.patch(path, { role: select.value }), 'Роль изменена')) loadTeams();
    });
    tools.push(select, button('Исключить', async () => {
      if (!confirm(t('Исключить {name} из команды?', { name: member.name }))) return;
      if (await act(site.remove(`/api/teams/${team.id}/members/${member.id}`), 'Участник исключён')) loadTeams();
    }, 'cw-act cw-danger'));
  } else {
    tools.push(role(member.role));
  }
  return h('div', { class: 'cw-item', 'data-member': member.id }, avatar(member.name),
    h('div', { class: 'who', translate: 'no' }, h('b', {}, member.name + (me ? ` (${t('вы')})` : '')),
      h('span', { class: 'cw-sub' }, member.email)),
    h('div', { class: 'row-actions' }, tools));
}

function teamCard(team) {
  const owner = team.owner === session.user.id;
  const mine = team.members.find((member) => member.id === session.user.id);
  const tools = [button('Переписка команды', () => openChat({ team: team.id, title: team.name }), 'cw-act cw-ghost')];
  if (owner) {
    tools.push(button('Распустить команду', async () => {
      const question = t('Распустить команду «{name}»? Доступ её участников к проектам будет закрыт.',
        { name: team.name });
      if (!confirm(question)) return;
      if (await act(site.remove(`/api/teams/${team.id}`), 'Команда распущена')) loadAll();
    }, 'cw-act cw-danger'));
  } else {
    tools.push(button('Выйти из команды', async () => {
      if (!confirm(t('Выйти из команды «{name}»?', { name: team.name }))) return;
      if (await act(site.remove(`/api/teams/${team.id}/members/${session.user.id}`), 'Вы вышли из команды')) loadAll();
    }, 'cw-act cw-danger'));
  }
  return h('article', { class: 'cw-team team', 'data-team': team.id },
    h('div', { class: 'cw-team-head' }, h('b', { translate: 'no' }, team.name), role(owner ? 'owner' : mine.role)),
    team.members.map((member) => memberRow(team, member, owner)),
    h('div', { class: 'cw-row' }, tools));
}

function fillInviteTargets() {
  const owned = view.teams.filter((team) => team.owner === session.user.id);
  $('invite-target').replaceChildren(h('option', { value: '' }, t('в друзья')),
    ...owned.map((team) => h('option', { value: team.id }, t('в команду «{team}»', { team: team.name }))));
  $('invite-role').hidden = !$('invite-target').value;
}

async function loadTeams() {
  const teams = await act(site.get('/api/teams'));
  if (!teams) return;
  view.teams = teams;
  $('teams-list').replaceChildren(...(teams.length ? teams.map(teamCard) : [empty('Команд пока нет.')]));
  fillInviteTargets();
}

function invitationText(invitation, incoming) {
  const who = incoming ? (invitation.from ? `${invitation.from.name} (${invitation.from.email})` : '—') : invitation.to;
  const what = invitation.team
    ? t('в команду «{team}», роль: {role}', { team: invitation.team, role: t(ROLE_NAMES[invitation.role]) })
    : t('в друзья');
  return h('div', { class: 'who' }, h('b', { translate: 'no' }, who),
    h('span', { class: 'cw-sub' }, `${what} · ${when(invitation.created)}`));
}

async function answer(invitation, accept) {
  const done = accept ? 'Приглашение принято' : 'Приглашение отклонено';
  if (await act(site.post(`/api/invitations/${invitation.id}`, { accept }), done)) {
    loadAll();
    refreshBell();
  }
}

async function loadInvitations() {
  const invitations = await act(site.get('/api/invitations'));
  if (!invitations) return;
  const incoming = invitations.incoming.map((invitation) => h('div', { class: 'cw-item', 'data-invitation':
    invitation.id }, invitationText(invitation, true),
  invitation.status === 'waiting'
    ? h('div', { class: 'row-actions' },
      button('Принять', () => answer(invitation, true), 'cw-act btn-accept'),
      button('Отклонить', () => answer(invitation, false), 'cw-act cw-ghost'))
    : status(invitation.status)));
  $('incoming').replaceChildren(...(incoming.length ? incoming : [empty('Новых приглашений нет.')]));
  const outgoing = invitations.outgoing.map((invitation) => h('div', { class: 'cw-item' },
    invitationText(invitation, false), status(invitation.status)));
  $('outgoing').replaceChildren(...(outgoing.length ? outgoing : [empty('Вы ещё никого не приглашали.')]));
  const waiting = invitations.incoming.filter((invitation) => invitation.status === 'waiting').length;
  $('count-invitations').textContent = String(waiting);
  $('count-invitations').hidden = waiting === 0;
}

async function loadFriends() {
  const friends = await act(site.get('/api/friends'));
  if (!friends) return;
  view.friends = friends;
  const rows = friends.map((friend) => h('div', { class: 'cw-item', 'data-friend': friend.id }, avatar(friend.name),
    h('div', { class: 'who', translate: 'no' }, h('b', {}, friend.name), h('span', { class: 'cw-sub' }, friend.email)),
    h('div', { class: 'row-actions' },
      button('Написать', () => openChat({ user: friend.id, title: friend.name }), 'cw-act'),
      button('Удалить из друзей', async () => {
        if (!confirm(t('Удалить {name} из друзей?', { name: friend.name }))) return;
        if (await act(site.remove(`/api/friends/${friend.id}`), 'Удалено из друзей')) loadAll();
      }, 'cw-act cw-danger'))));
  const nobody = empty('Друзей пока нет — пригласите коллегу по почте.');
  $('friends-list').replaceChildren(...(rows.length ? rows : [nobody]));
}

async function loadShared() {
  const projects = await act(site.get('/api/projects'));
  if (!projects) return;
  const shared = projects.filter((project) => project.role !== 'owner');
  $('shared-list').replaceChildren(...(shared.length ? shared.map((project) => h('div', { class: 'cw-item',
    'data-project': project.id }, h('div', { class: 'who' }, h('b', { translate: 'no' }, project.name),
    h('span', { class: 'cw-sub', translate: 'no' }, project.owner)), role(project.role),
  h('a', { class: 'cw-act cw-link', href: `/app?project=${project.id}` }, t('Открыть'))))
    : [empty('Общих проектов пока нет.')]));
}

function chatKey(chat) {
  return chat ? (chat.team ? `team-${chat.team}` : `user-${chat.user}`) : '';
}

function drawTargets() {
  const entry = (chat, sub, label) => h('button', {
    type: 'button', class: `cw-item cw-target${chatKey(chat) === chatKey(view.chat) ? ' chosen' : ''}`,
    'data-chat': chatKey(chat), onclick: () => openChat(chat),
  }, avatar(chat.title), h('div', { class: 'who', translate: 'no' }, h('b', {}, chat.title),
    sub ? h('small', {}, sub) : null), h('span', { class: 'cw-pill' }, t(label)));
  const items = [
    ...view.friends.map((friend) => entry({ user: friend.id, title: friend.name }, friend.email, 'друг')),
    ...view.teams.map((team) => entry({ team: team.id, title: team.name },
      t('участников: {count}', { count: team.members.length }), 'команда')),
  ];
  $('chat-targets').replaceChildren(...(items.length ? items
    : [empty('Добавьте друзей или вступите в команду, чтобы начать переписку.')]));
}

function fileLink(message) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.8');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', FILE_ICON);
  svg.append(path);
  return h('div', { class: 'cw-file' }, h('a', { class: 'file', href: `/api/messages/${message.id}/file`,
    download: message.file, translate: 'no' }, svg, message.file));
}

function bubble(message) {
  const mine = message.from && message.from.id === session.user.id;
  return h('div', { class: `cw-msg bubble${mine ? ' mine' : ''}`, 'data-message': message.id },
    mine ? null : h('div', { class: 'cw-who', translate: 'no' }, message.from ? message.from.name : '—'),
    message.body ? h('div', { class: 'cw-body', translate: 'no' }, message.body) : null,
    message.file ? fileLink(message) : null,
    h('div', { class: 'cw-time' }, when(message.created)));
}

async function loadHistory() {
  const chat = view.chat;
  if (!chat) return;
  const query = chat.team ? `team=${chat.team}` : `user_id=${chat.user}`;
  let list;
  try {
    list = await site.get(`/api/messages?${query}`);
  } catch (error) {
    toast(error.message, 'bad');
    return;
  }
  if (chatKey(chat) !== chatKey(view.chat)) return;
  const last = list.length ? list[list.length - 1].id : 0;
  if (last === view.lastMessage) return;
  view.lastMessage = last;
  const feed = $('chat-feed');
  feed.replaceChildren(...(list.length ? list.map(bubble) : [h('p', { class: 'cw-empty' }, t('Сообщений пока нет.'))]));
  feed.scrollTop = feed.scrollHeight;
}

function openChat(chat) {
  view.chat = chat;
  view.lastMessage = -1;
  $('chat-title').textContent = chat.title;
  $('chat-title').setAttribute('translate', 'no');
  $('chat-form').hidden = false;
  $('chat-feed').replaceChildren();
  drawTargets();
  if (location.hash !== '#chat') history.replaceState(null, '', '#chat');
  $('chat').scrollIntoView({ behavior: 'smooth', block: 'start' });
  loadHistory();
  $('chat-text').focus();
}

function clearAttachment() {
  $('chat-file').value = '';
  $('chat-attach').hidden = true;
}

async function sendMessage(event) {
  event.preventDefault();
  if (!view.chat) return;
  const file = $('chat-file').files[0];
  if (!$('chat-text').value.trim() && !file) return;
  const data = new FormData();
  data.append('body', $('chat-text').value);
  if (view.chat.team) data.append('team', String(view.chat.team));
  else data.append('to_user', String(view.chat.user));
  if (file) data.append('file', file);
  if (await act(site.form('/api/messages', data))) {
    $('chat-text').value = '';
    clearAttachment();
    loadHistory();
  }
}

async function loadAll() {
  await Promise.all([loadTeams(), loadFriends(), loadInvitations(), loadShared()]);
  drawTargets();
}

function bind() {
  $('team-new').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (await act(site.post('/api/teams', { name: $('team-name').value }), 'Команда создана')) {
      $('team-name').value = '';
      loadAll();
    }
  });
  $('invite-target').addEventListener('change', () => { $('invite-role').hidden = !$('invite-target').value; });
  $('invite-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const team = $('invite-target').value;
    const body = team ? { email: $('invite-email').value, team: Number(team), role: $('invite-role').value }
      : { email: $('invite-email').value };
    if (await act(site.post('/api/invitations', body), 'Приглашение отправлено')) {
      $('invite-email').value = '';
      loadInvitations();
    }
  });
  $('friend-invite').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (await act(site.post('/api/invitations', { email: $('friend-email').value }), 'Приглашение отправлено')) {
      $('friend-email').value = '';
      loadInvitations();
    }
  });
  $('chat-form').addEventListener('submit', sendMessage);
  $('chat-file').addEventListener('change', () => {
    const file = $('chat-file').files[0];
    $('chat-attach').hidden = !file;
    if (file) {
      $('chat-attach-name').textContent = file.name;
      $('chat-attach-size').textContent = size(file.size);
    }
  });
  $('chat-attach-off').addEventListener('click', clearAttachment);
}

const user = await startSite();
if (user) {
  bind();
  await loadAll();
  setInterval(loadHistory, CHAT_POLL_MS);
  const reveal = () => {
    const wanted = location.hash.replace('#', '');
    if (wanted && $(wanted)) $(wanted).scrollIntoView({ block: 'start' });
  };
  reveal();
  window.addEventListener('hashchange', () => loadAll().then(reveal));
}

import { api } from './api.js';
import { toScreen } from './canvas.js';
import { $, h, s, toast } from './dom.js';
import { openActionDialog } from './dialogs.js';
import { adopt, notify, state } from './state.js';

const ICONS = {
  outgoing: 'M4 4v16M4 12h16',
  span: 'M3 12h18M6 9v6M18 9v6',
  branch_line: 'M4 6h16M12 6v12M8 18h8',
  branch_consumer: 'M4 6h16M12 6v8M8 14h8v6H8z',
  pole: 'M5 12h14M8 9v6M16 9v6',
  consumer: 'M7 7h10v10H7z',
};

const POINT_KINDS = {
  0: 'точка',
  1: 'конец отходящей линии',
  2: 'опора',
  3: 'конец пролёта',
  4: 'конец ответвления к линии',
  6: 'конец ответвления к потребителю',
};

function icon(kind) {
  const svg = s('svg', { viewBox: '0 0 24 24' });
  svg.append(s('path', { d: ICONS[kind] || ICONS.span }));
  return h('span', { class: 'action-ic' }, svg);
}

function actionButton(action) {
  return h('button', {
    type: 'button', class: 'action', 'data-action': action.kind,
    onclick: () => {
      hidePopup();
      openActionDialog(action.kind, action.kind === 'outgoing' ? null : state.point);
    },
  }, icon(action.kind), action.title);
}

function describePoint(point, pointKind) {
  if (!point) return null;
  const scheme = state.scheme;
  const contact = scheme.connection_points.find((p) => p.active && p.x === point.x && p.y === point.y);
  if (!contact) return null;
  if (pointKind === 2) {
    const pole = scheme.poles.find((p) => p.y === point.y && point.x >= p.x && point.x <= p.x + p.canvas_length);
    const where = contact.branch_no > 0 ? `ответвление № ${contact.branch_no}` : 'конец опоры';
    return [h('b', {}, `Опора ${pole ? pole.label : ''}`), `: ${where}`];
  }
  return [h('b', {}, POINT_KINDS[pointKind] || 'точка'), ` (x ${point.x}, y ${point.y})`];
}

export function renderActions() {
  const info = $('point-info');
  const box = $('actions');
  if (!state.scheme) {
    info.textContent = 'Создайте схему или откройте файл .cir.';
    box.replaceChildren();
    return;
  }
  const list = state.actions.length ? state.actions : [{ kind: 'outgoing', title: state.titles.outgoing }];
  const described = describePoint(state.point, state.pointKind);
  info.replaceChildren(...(described || ['Выберите синюю точку на схеме, чтобы продолжить построение от неё.']));
  info.classList.toggle('muted', !described);
  box.replaceChildren(...list.map(actionButton));
}

export function hidePopup() {
  $('popup').hidden = true;
}

function showPopup(point, actions) {
  const popup = $('popup');
  const stage = $('stage').getBoundingClientRect();
  const screen = toScreen(point);
  popup.replaceChildren(h('div', { class: 'popup-title' }, 'Добавить'), ...actions.map(actionButton));
  popup.hidden = false;
  const width = popup.offsetWidth;
  const height = popup.offsetHeight;
  let left = screen.x - stage.left + 14;
  let top = screen.y - stage.top + 14;
  if (left + width > stage.width - 8) left = screen.x - stage.left - width - 14;
  if (top + height > stage.height - 38) top = Math.max(8, stage.height - 38 - height);
  popup.style.left = `${Math.max(8, left)}px`;
  popup.style.top = `${Math.max(8, top)}px`;
}

export async function choosePoint(point, { popup = true, click = popup } = {}) {
  if (!state.scheme) return;
  const sent = state.scheme;
  try {
    const answer = await api.menu(sent, point);
    if (state.scheme !== sent) return;
    if (click) adopt(answer.scheme);
    state.point = point;
    state.pointKind = answer.point_kind;
    state.actions = answer.actions;
    notify('point');
    if (popup) showPopup(point, answer.actions);
  } catch (error) {
    toast(error.message, 'bad');
  }
}

export function clearPoint() {
  state.point = null;
  state.pointKind = 0;
  state.actions = [];
  hidePopup();
  notify('point');
}

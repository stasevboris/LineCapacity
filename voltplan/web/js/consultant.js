import { site } from './api.js';
import { h } from './dom.js';
import { t } from './i18n.js';

const STORE_KEY = 'voltplan-consultant';
const CHIPS = ['Как построить схему?', 'Какой тариф выбрать?', 'Как сравнить варианты?',
  'Что такое допустимая мощность?'];
const ICONS = {
  spark: 'M12 3l1.9 4.6L18.5 9.5 13.9 11.4 12 16l-1.9-4.6L5.5 9.5l4.6-1.9zM19 14l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z',
  close: 'M6 6l12 12M18 6L6 18',
  send: 'M4 12l16-8-6 16-3-6-7-2z',
};
const history = [];

function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.8');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', ICONS[name]);
  svg.append(path);
  return svg;
}

function load() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || '[]');
    if (Array.isArray(saved)) history.push(...saved.slice(-20));
  } catch (error) {
    history.length = 0;
  }
}

function save() {
  try {
    sessionStorage.setItem(STORE_KEY, JSON.stringify(history.slice(-20)));
  } catch (error) {
    return;
  }
}

function avatar() {
  return h('span', { class: 'consult-av' }, icon('spark'));
}

function rich(text) {
  return String(text).split(/\*\*(.+?)\*\*/g).map((part, index) => (index % 2 ? h('b', {}, part) : part));
}

function message(role, text) {
  if (role === 'user') {
    return h('div', { class: 'consult-msg user' }, h('div', { class: 'consult-bubble', translate: 'no' }, text));
  }
  return h('div', { class: 'consult-msg bot' }, avatar(), h('div', { class: 'consult-bubble' }, rich(text)));
}

export function mountConsultant({ signedIn, trigger }) {
  load();
  const body = h('div', { class: 'consult-body', 'aria-live': 'polite' });
  const chips = h('div', { class: 'consult-chips' });
  const input = h('input', { type: 'text', autocomplete: 'off', maxlength: 1000, 'aria-label': t('Вопрос'),
    placeholder: t('Спросите о построении схемы, расчёте или тарифах…'), disabled: !signedIn });
  const send = h('button', { type: 'submit', 'aria-label': t('Отправить'), disabled: !signedIn }, icon('send'));
  const form = h('form', { class: 'consult-input' }, input, send);
  const close = h('button', { class: 'consult-x', type: 'button', 'aria-label': t('Закрыть') }, icon('close'));
  const panel = h('div', { class: 'consult-panel', id: 'consult-panel', role: 'dialog',
    'aria-label': t('Консультант') },
    h('div', { class: 'consult-head' },
      h('div', { class: 'consult-id' }, avatar(),
        h('div', {}, h('b', {}, t('Консультант')), h('small', {}, t('Отвечает на вопросы о работе с VoltPlan')))),
      close),
    body, chips,
    signedIn ? null : h('p', { class: 'consult-guest' }, t('Войдите или зарегистрируйтесь, чтобы задать вопрос.'),
      ' ', h('a', { href: '/login' }, t('Вход'))),
    form);
  const button = trigger || h('button', { class: 'consult-fab', id: 'btn-consultant', type: 'button',
    'aria-label': t('Открыть консультанта') }, icon('spark'), h('span', {}, t('Консультант')));
  let busy = false;
  let shown = false;

  const scroll = () => { body.scrollTop = body.scrollHeight; };
  const add = (role, text) => { body.append(message(role, text)); scroll(); };
  const typing = (on) => {
    const current = body.querySelector('.consult-typing');
    if (on && !current) {
      body.append(h('div', { class: 'consult-msg bot consult-typing' }, avatar(),
        h('div', { class: 'consult-bubble' }, h('i'), h('i'), h('i'))));
      scroll();
    } else if (!on && current) {
      current.remove();
    }
  };

  async function ask(question) {
    if (busy || !signedIn || !question) return;
    busy = true;
    send.disabled = true;
    input.value = '';
    const previous = history.slice(-8);
    history.push({ role: 'user', text: question });
    add('user', question);
    typing(true);
    try {
      const reply = await site.post('/api/consultant', { question, history: previous });
      typing(false);
      history.push({ role: 'assistant', text: reply.answer });
      add('assistant', reply.answer);
    } catch (error) {
      typing(false);
      add('assistant', error.message);
    } finally {
      busy = false;
      send.disabled = false;
      save();
    }
  }

  function open() {
    panel.classList.add('open');
    if (!trigger) button.classList.add('hidden');
    if (!shown) {
      shown = true;
      add('assistant', t('Здравствуйте! Я консультант VoltPlan: подскажу, как построить и рассчитать схему, '
        + 'работать с проектами и выбрать тариф. О чём рассказать?'));
      history.forEach((item) => add(item.role, item.text));
      if (signedIn) {
        chips.replaceChildren(...CHIPS.map((text) => h('button', { class: 'consult-chip', type: 'button',
          onclick: () => ask(t(text)) }, t(text))));
      }
    }
    setTimeout(() => input.focus(), 60);
  }

  function hide() {
    panel.classList.remove('open');
    button.classList.remove('hidden');
  }

  button.addEventListener('click', () => (panel.classList.contains('open') ? hide() : open()));
  close.addEventListener('click', hide);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && panel.classList.contains('open')) hide();
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    ask(input.value.trim());
  });
  if (!trigger) document.body.append(button);
  document.body.append(panel);
  return button;
}

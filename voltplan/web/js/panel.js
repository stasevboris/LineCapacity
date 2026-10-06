import { h, toast } from './dom.js';
import { language, t } from './i18n.js';

export const ROLE_NAMES = { owner: 'владелец', editor: 'редактор', reader: 'читатель' };
export const STATUS_NAMES = {
  waiting: 'ждёт ответа', accepted: 'принято', declined: 'отклонено', cancelled: 'отменено',
};

export function when(seconds, style = 'short') {
  if (!seconds) return '—';
  const code = { ru: 'ru-RU', en: 'en-GB', zh: 'zh-CN' }[language()] || 'ru-RU';
  const options = style === 'date' ? { dateStyle: 'short' } : { dateStyle: 'short', timeStyle: 'short' };
  return new Intl.DateTimeFormat(code, options).format(new Date(seconds * 1000));
}

export function role(name) {
  return h('span', { class: `role role-${name}` }, t(ROLE_NAMES[name] || name));
}

export function empty(text) {
  return h('p', { class: 'empty-note' }, t(text));
}

export function button(text, onclick, cls = 'btn btn-ghost btn-small', attrs = {}) {
  return h('button', { class: cls, type: 'button', onclick, ...attrs }, t(text));
}

export async function act(promise, done) {
  try {
    const result = await promise;
    if (done) toast(t(done));
    return result;
  } catch (error) {
    toast(error.message, 'bad');
    return null;
  }
}

export function dialog({ title, body, okText, onOk }) {
  const error = h('span', { class: 'form-error', role: 'alert' });
  const close = () => shade.remove();
  const ok = h('button', { class: 'btn btn-primary btn-small', type: 'submit' }, t(okText || 'Готово'));
  const card = h('form', { class: 'dialog-card', novalidate: true },
    h('header', { class: 'dialog-head' }, h('h2', {}, title),
      h('button', { class: 'icon-x', type: 'button', 'aria-label': t('Закрыть'), onclick: close }, '✕')),
    h('div', { class: 'dialog-body', id: 'dialog-body' }, body),
    h('footer', { class: 'dialog-foot' }, error, button('Отмена', close), onOk ? ok : null));
  const shade = h('div', { class: 'dialog', role: 'dialog', 'aria-modal': 'true' }, card);
  card.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!onOk) return;
    error.textContent = '';
    ok.disabled = true;
    try {
      if ((await onOk()) !== false) close();
    } catch (problem) {
      error.textContent = problem.message;
    } finally {
      ok.disabled = false;
    }
  });
  shade.addEventListener('keydown', (event) => { if (event.key === 'Escape') close(); });
  document.body.append(shade);
  const first = card.querySelector('input, select');
  (first || card.querySelector('button')).focus();
  return close;
}

export function askText(title, label, value, okText) {
  return new Promise((resolve) => {
    const input = h('input', { maxlength: '120', value: value || '', 'aria-label': t(label) });
    let answered = false;
    dialog({
      title: t(title), okText,
      body: h('div', { class: 'field' }, h('label', {}, t(label)), input),
      onOk: () => {
        if (!input.value.trim()) throw new Error(t('Заполните поле'));
        answered = true;
        resolve(input.value.trim());
      },
    });
    const observer = new MutationObserver(() => {
      if (!document.body.contains(input)) {
        observer.disconnect();
        if (!answered) resolve(null);
      }
    });
    observer.observe(document.body, { childList: true });
  });
}

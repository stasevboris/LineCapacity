import { site } from './api.js';
import { mountConsultant } from './consultant.js';
import { $, h, s } from './dom.js';
import { loadLanguage, t, translatePage } from './i18n.js';
import { languageSwitch } from './language.js';

const THEME_KEY = 'voltplan-theme';
export const POLL_MS = 30000;

export const TIERS = { demo: 'Демо', pro: 'Профессионал', max: 'Максимум' };

export const session = { user: null };

export function applyTheme(theme) {
  if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  else document.documentElement.setAttribute('data-theme', 'light');
}

export function savedTheme() {
  let saved = null;
  try { saved = localStorage.getItem(THEME_KEY); } catch (error) { saved = null; }
  return saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

export function toggleTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem(THEME_KEY, next); } catch (error) { return next; }
  return next;
}

function initTheme() {
  applyTheme(savedTheme());
  const button = $('btn-theme');
  if (button) button.addEventListener('click', toggleTheme);
}

export async function whoAmI() {
  try {
    return (await site.get('/api/auth/state')).user;
  } catch (error) {
    return null;
  }
}

function bellIcon() {
  const svg = s('svg', { viewBox: '0 0 24 24', 'aria-hidden': 'true' });
  svg.append(s('path', { d: 'M12 3a6 6 0 0 0-6 6v4l-2 3h16l-2-3V9a6 6 0 0 0-6-6zm-2.5 15a2.5 2.5 0 0 0 5 0z' }));
  return svg;
}

export async function refreshBell() {
  const badge = $('bell-count');
  if (!badge || !session.user) return null;
  try {
    const data = await site.get('/api/notifications');
    badge.textContent = data.unseen > 99 ? '99+' : String(data.unseen);
    badge.hidden = data.unseen === 0;
    return data;
  } catch (error) {
    return null;
  }
}

export async function logout() {
  try { await site.post('/api/auth/logout'); } catch (error) { location.href = '/'; }
  location.href = '/';
}

function userArea(user) {
  if (!user) {
    return [
      h('a', { class: 'btn', href: '/login' }, t('Войти')),
      h('a', { class: 'btn btn-primary', href: '/register' }, t('Регистрация')),
    ];
  }
  return [
    h('a', { class: 'icon-btn bell', id: 'bell', href: '/account#notifications', title: t('Уведомления'),
      'aria-label': t('Уведомления') }, bellIcon(), h('span', { id: 'bell-count', class: 'bell-count', hidden: true })),
    user.is_admin ? h('a', { class: 'btn btn-small', id: 'admin-link', href: '/admin' }, t('Администрирование'))
      : null,
    h('a', { class: 'user-chip', id: 'user-chip', href: '/account', title: t('Личный кабинет') },
      h('span', { class: 'user-name' }, user.name || user.email),
      h('span', { class: `tier-badge tier-${user.tier}` }, t(TIERS[user.tier] || user.tier))),
    h('button', { class: 'btn btn-small', id: 'btn-logout', type: 'button', onclick: logout }, t('Выйти')),
  ];
}

export async function startPage() {
  const user = await whoAmI();
  session.user = user;
  await loadLanguage(user ? user.language : null);
  translatePage();
  initTheme();
  const languageBox = $('language-area');
  if (languageBox) languageBox.replaceChildren(languageSwitch(() => Boolean(session.user)));
  const box = $('user-area');
  if (box) box.replaceChildren(...userArea(user).filter(Boolean));
  if (user) {
    refreshBell();
    setInterval(refreshBell, POLL_MS);
    if (box) {
      const trigger = h('button', { class: 'btn btn-small', id: 'btn-consultant', type: 'button' }, t('Консультант'));
      box.prepend(trigger);
      mountConsultant({ signedIn: true, trigger });
    }
  }
  return user;
}

import { mountConsultant } from './consultant.js';
import { h, s } from './dom.js';
import { language, loadLanguage, t, translatePage } from './i18n.js';
import { languageSwitch } from './language.js';
import { POLL_MS, applyTheme, logout, refreshBell, savedTheme, session, toggleTheme, whoAmI } from './session.js';

const ICONS = {
  menu: 'M4 7h16M4 12h16M4 17h16',
  close: 'M6 6l12 12M18 6L6 18',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 '
    + '1.4M6.4 17.6 5 19',
  moon: 'M21 12.8A8.5 8.5 0 1 1 11.2 3 6.5 6.5 0 0 0 21 12.8z',
  bell: 'M6 9a6 6 0 0 1 12 0c0 5 2 6.5 2 6.5H4S6 14 6 9M10 19.5a2.2 2.2 0 0 0 4 0',
};
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

export function icon(name, width = '1.8') {
  const svg = s('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': width,
    'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' });
  svg.append(s('path', { d: ICONS[name] }));
  return svg;
}

function themeButton() {
  const button = h('button', { class: 'theme-toggle', id: 'btn-theme', type: 'button',
    'aria-label': t('Переключить тему оформления') });
  const sync = () => {
    button.replaceChildren(icon(document.documentElement.getAttribute('data-theme') === 'dark' ? 'sun' : 'moon'));
  };
  button.addEventListener('click', () => { toggleTheme(); sync(); });
  sync();
  return button;
}

function navToggle(links) {
  const button = h('button', { class: 'nav-toggle', type: 'button', 'aria-label': t('Открыть меню'),
    'aria-expanded': 'false' }, icon('menu', '2'));
  button.addEventListener('click', () => {
    const open = links.classList.toggle('open');
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    button.setAttribute('aria-label', t(open ? 'Закрыть меню' : 'Открыть меню'));
    button.replaceChildren(icon(open ? 'close' : 'menu', '2'));
  });
  links.before(button);
}

function markActive(links) {
  const here = location.pathname.replace(/\/$/, '') || '/';
  links.querySelectorAll(':scope > a:not(.btn)').forEach((link) => {
    const target = new URL(link.href, location.href).pathname.replace(/\/$/, '') || '/';
    if (target === here) link.classList.add('active');
  });
}

function bell() {
  return h('a', { class: 'nav-bell', id: 'bell', href: '/account#notifications', 'data-auth': 'in',
    title: t('Уведомления'), 'aria-label': t('Уведомления') }, icon('bell', '1.7'),
  h('span', { class: 'count', id: 'bell-count', hidden: true }));
}

function buildNav(user) {
  const links = document.querySelector('.nav .links');
  if (!links) return;
  links.prepend(languageSwitch(() => Boolean(session.user)), themeButton());
  const out = document.getElementById('logout');
  if (out) {
    out.before(bell());
    out.addEventListener('click', (event) => { event.preventDefault(); logout(); });
    if (user) out.title = t('Выйти из учётной записи {email}', { email: user.email });
  }
  navToggle(links);
  markActive(links);
}

function reveal() {
  const items = [...document.querySelectorAll('.reveal')];
  if (!items.length) return;
  if (REDUCED || !('IntersectionObserver' in window)) {
    items.forEach((item) => item.classList.add('in'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
  items.forEach((item) => observer.observe(item));
  let ticking = false;
  const sweep = () => {
    const height = window.innerHeight || document.documentElement.clientHeight;
    let pending = false;
    items.forEach((item) => {
      if (item.classList.contains('in')) return;
      if (item.getBoundingClientRect().top < height * 0.92) {
        item.classList.add('in');
        observer.unobserve(item);
      } else {
        pending = true;
      }
    });
    if (!pending) {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    }
  };
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { ticking = false; sweep(); });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  sweep();
}

function counters() {
  const numbers = [...document.querySelectorAll('[data-count]')];
  if (!numbers.length) return;
  const comma = language() === 'ru' ? ',' : '.';
  const format = (value, digits) => value.toFixed(digits).replace('.', comma)
    .replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const run = (element) => {
    const target = parseFloat(element.getAttribute('data-count'));
    const digits = Number(element.getAttribute('data-dec') || 0);
    if (REDUCED) {
      element.textContent = format(target, digits);
      return;
    }
    let start = 0;
    const step = (stamp) => {
      if (!start) start = stamp;
      const progress = Math.min((stamp - start) / 1300, 1);
      element.textContent = format(target * (1 - (1 - progress) ** 3), digits);
      if (progress < 1) requestAnimationFrame(step);
      else element.textContent = format(target, digits);
    };
    requestAnimationFrame(step);
  };
  if (!('IntersectionObserver' in window)) {
    numbers.forEach(run);
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        run(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  numbers.forEach((item) => observer.observe(item));
}

function tilt() {
  if (REDUCED || matchMedia('(pointer: coarse)').matches) return;
  document.querySelectorAll('.cards, .steps').forEach((group) => {
    group.querySelectorAll('.card, .step').forEach((item) => item.classList.add('tilt'));
    group.addEventListener('pointermove', (event) => {
      const item = event.target.closest('.tilt');
      if (!item) return;
      const box = item.getBoundingClientRect();
      const dx = (event.clientX - box.left) / box.width - 0.5;
      const dy = (event.clientY - box.top) / box.height - 0.5;
      item.style.transform = `rotateY(${(dx * 9).toFixed(2)}deg) rotateX(${(-dy * 9).toFixed(2)}deg) translateZ(6px)`;
    });
    group.addEventListener('pointerleave', () => {
      group.querySelectorAll('.tilt').forEach((item) => { item.style.transform = ''; });
    });
  });
}

function figures() {
  const items = [...document.querySelectorAll('.figure')];
  if (!items.length) return;
  if (!('IntersectionObserver' in window)) {
    items.forEach((item) => item.classList.add('in'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.25 });
  items.forEach((item) => observer.observe(item));
}

export async function startSite() {
  applyTheme(savedTheme());
  const user = await whoAmI();
  session.user = user;
  await loadLanguage(user ? user.language : null);
  window.VOLTPLAN_SCENE_LANG = language();
  document.dispatchEvent(new CustomEvent('voltplan-language', { detail: language() }));
  buildNav(user);
  if (user) {
    document.body.classList.add('signed-in');
    if (user.is_admin) document.body.classList.add('admin-user');
    refreshBell();
    setInterval(refreshBell, POLL_MS);
  }
  translatePage();
  mountConsultant({ signedIn: Boolean(user) });
  reveal();
  counters();
  tilt();
  figures();
  return user;
}

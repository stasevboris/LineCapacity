import { site } from './api.js';
import { $ } from './dom.js';
import { t } from './i18n.js';
import { startSite } from './site.js';

const STRENGTH = [
  { width: '0%', color: '', text: '' },
  { width: '25%', color: '#ef4444', text: 'Слабый пароль' },
  { width: '50%', color: '#f59e0b', text: 'Средний пароль' },
  { width: '70%', color: '#eab308', text: 'Хороший пароль' },
  { width: '100%', color: '#16a34a', text: 'Надёжный пароль' },
];

function target() {
  const next = new URLSearchParams(location.search).get('next') || '';
  return next.startsWith('/') && !next.startsWith('//') && !next.includes('\\') ? next : '/app';
}

function keepTarget() {
  const next = new URLSearchParams(location.search).get('next');
  if (next) $('to-other').href += `?next=${encodeURIComponent(next)}`;
}

async function submit(event, send) {
  event.preventDefault();
  const error = $('form-error');
  error.textContent = '';
  $('btn-submit').disabled = true;
  try {
    await send();
    location.href = target();
  } catch (problem) {
    error.textContent = problem.message;
    $('btn-submit').disabled = false;
  }
}

function strength(value) {
  let score = 0;
  if (value.length >= 8) score += 1;
  if (value.length >= 12) score += 1;
  if (/[A-ZА-ЯЁ]/.test(value) && /[a-zа-яё]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^A-Za-zА-Яа-яЁё0-9]/.test(value)) score += 1;
  return STRENGTH[Math.min(value ? Math.max(score, 1) : 0, 4)];
}

const user = await startSite();
if (user) location.replace(target());
keepTarget();

const login = $('login-form');
if (login) {
  login.addEventListener('submit', (event) => submit(event, () => site.post('/api/auth/login', {
    email: $('email').value, password: $('password').value,
  })));
}

const register = $('register-form');
if (register) {
  $('password').addEventListener('input', () => {
    const level = strength($('password').value);
    $('strength-bar').style.width = level.width;
    $('strength-bar').style.background = level.color;
    $('strength-text').textContent = level.text ? t(level.text) : '';
  });
  register.addEventListener('submit', (event) => submit(event, () => {
    if ($('password').value !== $('password2').value) throw new Error(t('Пароли не совпадают'));
    return site.post('/api/auth/register', {
      email: $('email').value, password: $('password').value, name: $('name').value,
    });
  }));
}
$('email').focus();

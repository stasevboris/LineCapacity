import { $ } from './dom.js';
import { language, t } from './i18n.js';
import { startSite } from './site.js';

const EVERY_MS = 10000;

function mark(id, ok) {
  const item = $(id);
  item.textContent = t(ok ? '● Работает' : '● Недоступен');
  item.classList.toggle('off', !ok);
}

async function check() {
  const started = performance.now();
  let data = null;
  try {
    const response = await fetch('/api/health', { cache: 'no-store' });
    data = response.ok ? await response.json() : null;
  } catch (error) {
    data = null;
  }
  const spent = Math.round(performance.now() - started);
  const ok = Boolean(data && data.status === 'ok');
  $('ind').className = `dot-ind ${ok ? 'up' : 'down'}`;
  $('state').textContent = t(ok ? 'Все системы работают' : 'Сервис недоступен');
  $('api').textContent = ok ? t('доступен ({ms} мс)', { ms: spent }) : t('нет ответа');
  $('marks').textContent = ok ? String(data.marks) : '—';
  mark('c-api', ok);
  mark('c-store', ok && data.storage);
  mark('c-cir', ok);
  const consultant = $('c-consultant');
  consultant.textContent = t(ok && data.consultant ? '● Работает' : '● Не настроен');
  consultant.classList.toggle('off', !(ok && data.consultant));
  const code = { ru: 'ru-RU', en: 'en-GB', zh: 'zh-CN' }[language()] || 'ru-RU';
  $('checked').textContent = new Date().toLocaleTimeString(code);
}

await startSite();
check();
setInterval(check, EVERY_MS);

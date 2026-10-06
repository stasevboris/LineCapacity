import { $ } from './dom.js';
import { t } from './i18n.js';
import { startSite } from './site.js';

function point(id, href, text) {
  const link = $(id);
  if (!link) return;
  link.href = href;
  link.textContent = t(text);
}

const user = await startSite();
if (user) {
  point('cta-main', '/app', 'Открыть редактор');
  point('cta-second', '/account', 'Личный кабинет');
  point('cta-band', '/app', 'Открыть редактор');
}

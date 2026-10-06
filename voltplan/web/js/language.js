import { site } from './api.js';
import { h } from './dom.js';
import { LANGUAGES, language, remember, t } from './i18n.js';

const SHORT = { ru: 'RU', en: 'EN', zh: '中文' };

export function languageSwitch(signedIn) {
  const box = h('div', { class: 'lang-switch', id: 'language', role: 'group', 'aria-label': t('Язык интерфейса'),
    translate: 'no' });
  for (const code of Object.keys(LANGUAGES)) {
    const chosen = code === language();
    const button = h('button', { type: 'button', 'data-lang': code, class: chosen ? 'on' : null,
      title: LANGUAGES[code], 'aria-pressed': chosen ? 'true' : 'false' }, SHORT[code]);
    button.addEventListener('click', async () => {
      if (code === language()) return;
      remember(code);
      if (signedIn()) {
        try { await site.post('/api/account/profile', { language: code }); } catch (error) { button.blur(); }
      }
      location.reload();
    });
    box.append(button);
  }
  return box;
}

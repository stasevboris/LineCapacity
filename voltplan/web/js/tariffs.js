import { site } from './api.js';
import { $, h, s } from './dom.js';
import { language, t } from './i18n.js';
import { session } from './session.js';
import { startSite } from './site.js';

const FEATURED = 'pro';
const LIMITS = [
  ['projects', 'Проектов'],
  ['variants', 'Вариантов схемы в проекте'],
  ['compared', 'Вариантов в одном сравнении'],
  ['scenarios', 'Сценариев в проекте'],
  ['poles', 'Опор в схеме'],
  ['consumers', 'Потребителей в схеме'],
];
const TAGLINES = {
  demo: 'Знакомство и учебные схемы — бесплатно и без срока.',
  pro: 'Рабочее проектирование: схемы предельного размера, свои марки, DOCX.',
  max: 'Всё из «Профессионала», эпюра, годовые потери и команды.',
};
const QUESTIONS = ['size', 'usage', 'projects', 'marks', 'analysis', 'team'];
const WHY = {
  max: 'Эпюра напряжения, годовые потери энергии и команды с общими проектами есть только в «Максимуме».',
  pro: 'Схемы до 598 потребителей, до 50 проектов, свои марки проводов и трансформаторов и отчёт DOCX.',
  demo: 'Небольшие схемы до 40 потребителей и два проекта — бесплатно, без карты.',
};

function mark(yes) {
  const svg = s('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
    'stroke-width': yes ? '2.4' : '2.2',
    'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' });
  svg.append(s('path', { d: yes ? 'M5 12.5l4.5 4.5L19 7' : 'M7 7l10 10M17 7L7 17' }));
  return h('span', { class: yes ? 'yes' : 'no' }, svg, h('span', { class: 'sr-only' }, t(yes ? 'есть' : 'нет')));
}

function until(seconds) {
  const code = { ru: 'ru-RU', en: 'en-GB', zh: 'zh-CN' }[language()] || 'ru-RU';
  return new Intl.DateTimeFormat(code, { dateStyle: 'long' }).format(new Date(seconds * 1000));
}

function action(tier, mine) {
  if (!session.user) {
    return h('a', { class: 'btn btn-primary', href: `/register?next=${encodeURIComponent(`/pay?tier=${tier.code}`)}` },
      t('Зарегистрироваться'));
  }
  const order = ['demo', 'pro', 'max'];
  if (tier.code !== 'demo' && order.indexOf(session.user.tier) > order.indexOf(tier.code)) {
    return h('button', { class: 'btn btn-ghost', type: 'button', disabled: true }, t('Входит в ваш тариф'));
  }
  if (tier.code === 'demo') {
    return h('button', { class: 'btn btn-ghost', type: 'button', disabled: true },
      t(mine ? 'Ваш текущий тариф' : 'Доступен всегда'));
  }
  const pay = h('a', { class: 'btn btn-primary', href: `/pay?tier=${tier.code}`, 'data-tier': tier.code },
    t(mine ? 'Продлить на 30 дней' : 'Оформить'));
  if (!mine || !session.user.tier_until) return pay;
  return h('div', { class: 'plan-action' }, h('button', { class: 'btn btn-ghost', type: 'button', disabled: true },
    t('Ваш тариф до {date}', { date: until(session.user.tier_until) })), pay);
}

function plan(tier, features, mine) {
  const lines = [
    ...LIMITS.slice(0, 1).map(([key, name]) => h('li', {}, `${t(name)}: ${tier[key]}`)),
    h('li', {}, t('Схема до {poles} опор и {consumers} потребителей',
      { poles: tier.poles, consumers: tier.consumers })),
    ...Object.entries(features).map(([code, name]) => h('li', { class: tier.features.includes(code) ? null : 'no' },
      t(name))),
  ];
  return h('div', { class: `plan tier-card${tier.code === FEATURED ? ' featured' : ''}${mine ? ' current' : ''}`,
    id: `plan-${tier.code}`, 'data-tier': tier.code },
  tier.code === FEATURED ? h('span', { class: 'flag' }, t('Рекомендуем')) : null,
  h('h3', {}, t(tier.title)),
  h('div', { class: 'tagline' }, t(TAGLINES[tier.code] || '')),
  h('div', { class: 'price' }, h('span', { translate: 'no' }, `$${tier.price_usd}`),
    h('small', {}, ' ', t(tier.price_usd ? 'за 30 дней' : 'бесплатно'))),
  h('ul', {}, lines),
  action(tier, mine));
}

function compare(tiers, features) {
  const rows = [
    ['Цена', (tier) => (tier.price_usd ? `$${tier.price_usd} / ${t('30 дней')}` : t('бесплатно'))],
    ...LIMITS.map(([key, name]) => [name, (tier) => String(tier[key])]),
    ['Построение схемы и расчёт режима', () => mark(true)],
    ['Меню «Расчёт», сценарии и сравнение вариантов', () => mark(true)],
    ['Обмен файлами .cir с LineCapacity', () => mark(true)],
    ...Object.entries(features).map(([code, name]) => [name, (tier) => mark(tier.features.includes(code))]),
  ];
  const cell = (tier, content, tag = 'td') => h(tag, { class: tier.code === FEATURED ? 'hl' : null }, content);
  $('cmp').replaceChildren(
    h('thead', {}, h('tr', {}, h('th', { class: 'corner' }), tiers.map((tier) => cell(tier, [t(tier.title),
      h('small', { translate: 'no' }, `$${tier.price_usd}`)], 'th')))),
    h('tbody', {}, rows.map(([name, value]) => h('tr', {}, h('th', {}, t(name)),
      tiers.map((tier) => cell(tier, value(tier)))))));
}

function quiz(titles) {
  const answers = {};
  const decide = () => {
    if (answers.analysis === 'yes' || answers.team === 'yes') return 'max';
    if (answers.size === 'l' || answers.usage === 'work' || answers.projects === 'many' || answers.marks === 'yes') {
      return 'pro';
    }
    return 'demo';
  };
  document.querySelectorAll('.quiz-q').forEach((question) => {
    const key = question.dataset.q;
    question.querySelectorAll('.quiz-opt').forEach((option) => option.addEventListener('click', () => {
      question.querySelectorAll('.quiz-opt').forEach((other) => other.classList.remove('on'));
      option.classList.add('on');
      answers[key] = option.dataset.v;
      const done = QUESTIONS.filter((name) => answers[name]).length;
      $('quiz-bar').style.width = `${Math.round((done / QUESTIONS.length) * 100)}%`;
      if (done < QUESTIONS.length) return;
      const code = decide();
      $('qr-name').textContent = t('Тариф «{name}»', { name: t(titles[code]) });
      $('qr-why').textContent = t(WHY[code]);
      $('qr-cta').href = `#plan-${code}`;
      $('qr-cta').textContent = code === 'demo' ? t('Начать бесплатно')
        : t('Перейти к тарифу «{name}»', { name: t(titles[code]) });
      $('quiz-result').classList.add('show');
      document.querySelectorAll('.plan').forEach((card) => card.classList.toggle('chosen', card.id === `plan-${code}`));
    }));
  });
}

await startSite();
const data = await site.get('/api/tiers');
const current = session.user ? session.user.tier : null;
$('plans').replaceChildren(...data.tiers.map((tier) => plan(tier, data.features, tier.code === current)));
compare(data.tiers, data.features);
quiz(Object.fromEntries(data.tiers.map((tier) => [tier.code, tier.title])));
if (session.user) {
  $('status').replaceChildren(t('Вы вошли как'), ' ', h('b', { translate: 'no' }, session.user.email), ' · ',
    t('тариф «{name}»', { name: t(data.tiers.find((tier) => tier.code === current).title) }), '. ',
    h('a', { href: '/app' }, t('Открыть редактор →')));
  const band = $('cta-band');
  band.href = '/app';
  band.textContent = t('Открыть редактор');
} else {
  $('status').replaceChildren(h('a', { href: '/login' }, t('Войдите')), ' ', t('или'), ' ',
    h('a', { href: '/register' }, t('зарегистрируйтесь')), t(', чтобы оформить тариф.'));
}

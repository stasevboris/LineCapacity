import { $, formatNumber, h, toast } from './dom.js';
import { t } from './i18n.js';
import { run } from './dialogs.js';
import { consumerSection, lineSection, poleSection, transformerSection } from './forms.js';
import { transformerCharts } from './charts.js';
import { resultsSection } from './results.js';
import { selectedObject, state } from './state.js';
import { computeAllowed } from './tools.js';

const TITLES = { transformer: 'Трансформатор', line: 'ЛЭП', pole: 'Опора', consumer: 'Потребитель' };
const LINE_KINDS = ['outgoing', 'span', 'branch_line', 'branch_consumer'];

function feederText(no) {
  return `Отходящая линия № ${Number(no) + 1}`;
}

async function apply(action, message) {
  try {
    await run(action);
    if (message) toast(message);
  } catch (error) {
    toast(error.message, 'bad');
  }
}

function objectName(kind, obj) {
  return { line: `ЛЭП ${obj.label}`, pole: `опору ${obj.label}`, consumer: `потребителя ${obj.label}` }[kind];
}

function describe(kind, obj) {
  if (kind === 'transformer') {
    return {
      section: transformerSection(obj),
      subtitle: t('R {r} Ом · X {x} Ом · Kт {kt}', { r: formatNumber(obj.r_ohm, 5), x: formatNumber(obj.x_ohm, 5),
        kt: formatNumber(obj.kt, 3) }),
    };
  }
  if (kind === 'line') return { section: lineSection(obj), subtitle: feederText(obj.feeder_no) };
  if (kind === 'pole') {
    return {
      section: poleSection(obj, { branchesEditable: false }),
      subtitle: `${feederText(obj.feeder_no)} · ответвлений: ${obj.branch_count}`,
    };
  }
  return { section: consumerSection(obj, { phase: obj }), subtitle: feederText(obj.feeder_no) };
}

function allowedBlock(index) {
  const results = state.results;
  if (!results) return null;
  const ready = results.period === 2 && results.good && !results.allowedDone;
  const reason = results.period !== 2 ? 'Доступно после расчёта по двум периодам'
    : !results.good ? 'Доступно, если пропускная способность сети достаточна'
      : results.allowedDone ? 'Выполните расчёт снова, чтобы определить допустимую мощность ещё раз' : '';
  const button = h('button', { class: 'btn', type: 'button', id: 'btn-allowed', disabled: !ready, title: reason || null,
    onclick: () => { button.disabled = true; computeAllowed(index); } },
  'Рассчитать допустимую мощность потребителя');
  return h('div', { class: 'props-actions allowed' }, button, reason ? h('span', { class: 'muted' }, reason) : null);
}

export function renderProps() {
  const box = $('props');
  const selection = state.selection;
  const obj = selectedObject();
  if (!selection || !obj) {
    box.replaceChildren(h('p', { class: 'muted' }, 'Выберите объект на схеме, чтобы изменить его параметры.'));
    return;
  }
  const { kind, index } = selection;
  const { section, subtitle } = describe(kind, obj);
  const error = h('div', { class: 'form-error', role: 'alert' });
  const applyButton = h('button', { class: 'btn btn-primary', type: 'button' }, 'Применить');
  applyButton.addEventListener('click', async () => {
    error.textContent = '';
    let fields;
    try {
      fields = section.changed();
    } catch (problem) {
      error.textContent = problem.message;
      return;
    }
    await apply({ kind: 'update', target: kind, index, fields }, 'Параметры изменены');
  });
  const buttons = state.readOnly ? [] : [applyButton];
  if (state.readOnly) section.el.querySelectorAll('input, select, button').forEach((el) => { el.disabled = true; });
  if (kind === 'pole' && !state.readOnly) {
    buttons.push(h('button', {
      class: 'btn', type: 'button',
      onclick: () => {
        if (confirm(`Добавить ответвление к опоре ${obj.label}?`)) {
          apply({ kind: 'add_branch', index }, 'Ответвление добавлено');
        }
      },
    }, 'Добавить ответвление'));
  }
  if (kind !== 'transformer' && !state.readOnly) {
    buttons.push(h('button', {
      class: 'btn btn-danger', type: 'button',
      onclick: () => {
        if (confirm(`Удалить ${objectName(kind, obj)}?`)) apply({ kind: 'delete', target: kind, index }, 'Удалено');
      },
    }, 'Удалить'));
  }
  const heading = kind === 'line' ? state.titles[LINE_KINDS[obj.line_type]] || TITLES.line : TITLES[kind];
  section.el.querySelector('legend')?.remove();
  const parts = [
    h('h3', {}, heading),
    h('p', { class: 'props-sub' }, subtitle),
    section.el,
    error,
    buttons.length ? h('div', { class: 'props-actions' }, buttons) : null,
    resultsSection(kind, index),
    kind === 'consumer' ? allowedBlock(index) : null,
    kind === 'transformer' ? transformerCharts() : null,
  ];
  box.replaceChildren(...parts.filter(Boolean));
}

export { objectName };

import { $, formatNumber, h, toast } from './dom.js';
import { run } from './dialogs.js';
import { consumerSection, lineSection, poleSection, transformerSection } from './forms.js';
import { transformerCharts } from './charts.js';
import { resultsSection } from './results.js';
import { selectedObject, state } from './state.js';

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
      subtitle: `R ${formatNumber(obj.r_ohm, 5)} Ом · X ${formatNumber(obj.x_ohm, 5)} Ом · `
        + `Kт ${formatNumber(obj.kt, 3)}`,
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
  const buttons = [applyButton];
  if (kind === 'pole') {
    buttons.push(h('button', {
      class: 'btn', type: 'button',
      onclick: () => {
        if (confirm(`Добавить ответвление к опоре ${obj.label}?`)) {
          apply({ kind: 'add_branch', index }, 'Ответвление добавлено');
        }
      },
    }, 'Добавить ответвление'));
  }
  if (kind !== 'transformer') {
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
    h('div', { class: 'props-actions' }, buttons),
    resultsSection(kind, index),
    kind === 'transformer' ? transformerCharts() : null,
  ];
  box.replaceChildren(...parts.filter(Boolean));
}

export { objectName };

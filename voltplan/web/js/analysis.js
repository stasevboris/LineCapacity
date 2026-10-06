import { site } from './api.js';
import { openModal } from './dialogs.js';
import { $, formatNumber, h, s, toast } from './dom.js';
import { t } from './i18n.js';
import { shownVariant } from './project.js';
import { selectedObject, state } from './state.js';

const PHASE_TOKENS = ['--phase-1', '--phase-2', '--phase-3'];
const COLUMNS = [
  ['min_voltage', 'Uмин, В', 1],
  ['voltage_loss_percent', 'ΔU, %', 1],
  ['loss_kw', 'Потери мощности, кВт', 2],
  ['max_temperature', 'Tмакс провода, °C', 1],
  ['load_factor', 'Загрузка ТП', 2],
  ['wear_hours', 'Износ изоляции, ч', 2],
];

function wide() {
  $('modal-card').classList.add('wide');
}

function needScheme() {
  if (state.scheme) return true;
  toast(t('Сначала создайте схему или откройте файл .cir'), 'bad');
  return false;
}

function quality(row) {
  const data = row.quality;
  if (data.ok) return t('в норме');
  return t('вне нормы у {count} из {total}', { count: data.outside, total: data.total });
}

function tenths(value) {
  return Number(value).toFixed(1).replace('.', ',');
}

function cell(row, key, digits, best) {
  const value = row[key];
  const mark = value !== null && value !== undefined && best[key] === value;
  return h('td', { class: mark ? 'num best' : 'num' }, value === null || value === undefined ? '—'
    : formatNumber(value, digits));
}

function compareTable(result) {
  const withCost = result.rows.some((row) => row.annual);
  const head = ['Вариант', 'Заключение', 'Качество напряжения (ГОСТ 32144)', ...COLUMNS.map((item) => item[1])];
  if (withCost) head.push('Потери энергии за год, кВт·ч', 'Стоимость потерь, $');
  const rows = result.rows.map((row, index) => {
    if (row.error) {
      return h('tr', {}, h('td', { translate: 'no' }, shownVariant(row.name)),
        h('td', { colspan: head.length - 1, class: 'bad' }, t(row.error)));
    }
    const winner = index === result.best;
    return h('tr', { class: winner ? 'winner' : '', 'data-variant': row.variant },
      h('td', {}, h('span', { translate: 'no' }, shownVariant(row.name)),
        winner ? h('span', { class: 'best-badge' }, t('лучший')) : null),
      h('td', { class: row.good ? 'good' : 'bad' }, t(row.good ? 'достаточна' : 'недостаточна')),
      h('td', { class: row.quality.ok ? 'good' : 'bad' }, quality(row)),
      ...COLUMNS.map(([key, , digits]) => cell(row, key, digits, result.best_values)),
      withCost ? cell(row, 'annual_kwh', 0, result.best_values) : null,
      withCost ? cell(row, 'annual_cost_usd', 2, result.best_values) : null);
  });
  return h('div', {}, h('div', { class: 'table-wrap' }, h('table', { class: 'summary-table compare-table' },
    h('thead', {}, h('tr', {}, head.map((name, index) => h('th', { class: index > 2 ? 'num' : null }, t(name))))),
    h('tbody', {}, rows))),
  h('p', { class: 'muted compare-rule' }, t('Лучший вариант выбирается по порядку: пропускная способность '
    + 'достаточна; напряжение у всех потребителей в пределах ±10 % номинального (ГОСТ 32144-2013); выше наименьшее '
    + 'напряжение у потребителя; ниже потери мощности. Лучшие значения выделены.')));
}

export async function openCompare() {
  if (!state.project) {
    toast(t('Варианты хранятся в проекте: сначала сохраните схему в проект'), 'bad');
    return;
  }
  const variants = state.project.variants;
  if (variants.length < 2) {
    toast(t('В проекте один вариант. Создайте ещё один кнопкой «+ Вариант».'), 'bad');
    return;
  }
  const boxes = variants.map((variant) => h('label', { class: 'check' },
    h('input', { type: 'checkbox', value: variant.id, checked: true }),
    h('span', { translate: 'no' }, shownVariant(variant.name))));
  const period = h('select', {}, [2, 0, 1].map((value) => h('option', { value },
    t({ 0: 'лето', 1: 'зима', 2: 'лето и зима' }[value]))));
  const minLoad = h('input', { type: 'checkbox', checked: true });
  const note = h('p', { class: 'muted' }, t('Сравниваются сохранённые схемы вариантов с настройками расчёта проекта.'));
  openModal({
    title: t('Сравнение вариантов'),
    sections: [{ el: h('fieldset', { class: 'fieldset' }, h('legend', {}, t('Варианты')), h('div', { class: 'choice' },
      boxes)) }, { el: h('div', { class: 'row' }, h('div', { class: 'field' }, h('label', {}, t('Период'), period)),
      h('label', { class: 'check' }, minLoad, t('Режим минимальных нагрузок'))) }, { el: note }],
    okText: t('Сравнить'),
    async onSubmit() {
      const chosen = boxes.map((label) => label.querySelector('input')).filter((input) => input.checked)
        .map((input) => Number(input.value));
      if (chosen.length < 2) throw new Error(t('Выберите хотя бы два варианта'));
      const result = await site.post(`/api/projects/${state.project.id}/compare`, {
        variants: chosen, settings: state.settings, period: Number(period.value), min_load: minLoad.checked,
      });
      setTimeout(() => {
        openModal({ title: t('Сравнение вариантов'), sections: [{ el: compareTable(result) }], okText: t('Закрыть'),
          onSubmit: () => true });
        wide();
      }, 0);
    },
  });
}

function colour(token) {
  return getComputedStyle(document.documentElement).getPropertyValue(token).trim();
}

function chart(data) {
  const width = 820;
  const height = 360;
  const pad = { left: 56, right: 18, top: 16, bottom: 44 };
  const values = data.points.flatMap((point) => point.voltages.filter((value) => value !== null));
  const low = Math.min(data.limits.low, ...values) - 4;
  const high = Math.max(data.limits.high, ...values) + 4;
  const last = Math.max(...data.points.map((point) => point.distance_m), 1);
  const x = (distance) => pad.left + (distance / last) * (width - pad.left - pad.right);
  const y = (voltage) => pad.top + (high - voltage) / (high - low) * (height - pad.top - pad.bottom);
  const svg = s('svg', { viewBox: `0 0 ${width} ${height}`, class: 'epure', role: 'img',
    'aria-label': t('Эпюра напряжения вдоль линии') });
  for (let step = Math.ceil(low / 10) * 10; step <= high; step += 10) {
    svg.append(s('line', { x1: pad.left, x2: width - pad.right, y1: y(step), y2: y(step), class: 'chart-grid' }));
    svg.append(s('text', { x: pad.left - 8, y: y(step) + 4, 'text-anchor': 'end', class: 'chart-tick' }, String(step)));
  }
  for (const limit of [data.limits.low, data.limits.high]) {
    svg.append(s('line', { x1: pad.left, x2: width - pad.right, y1: y(limit), y2: y(limit), class: 'chart-limit' }));
  }
  data.points.forEach((point) => {
    svg.append(s('line', { x1: x(point.distance_m), x2: x(point.distance_m), y1: pad.top, y2: height - pad.bottom,
      class: 'epure-node' }));
  });
  for (let phase = 0; phase < 3; phase += 1) {
    const path = data.points.filter((point) => point.voltages[phase] !== null)
      .map((point, index) => {
        const left = x(point.distance_m).toFixed(1);
        return `${index ? 'L' : 'M'}${left} ${y(point.voltages[phase]).toFixed(1)}`;
      });
    if (path.length < 2) continue;
    svg.append(s('path', { d: path.join(' '), class: 'epure-line', stroke: colour(PHASE_TOKENS[phase]) }));
    data.points.forEach((point) => {
      if (point.voltages[phase] === null) return;
      const dot = s('circle', { cx: x(point.distance_m), cy: y(point.voltages[phase]), r: 3.5,
        fill: colour(PHASE_TOKENS[phase]) });
      dot.append(s('title', {}, t('{name}: L{phase} {value} В', { name: t(point.name), phase: phase + 1,
        value: formatNumber(point.voltages[phase], 1) })));
      svg.append(dot);
    });
  }
  svg.append(s('text', { x: width - pad.right, y: height - 10, 'text-anchor': 'end', class: 'chart-tick' },
    t('расстояние от шин ТП, м')));
  svg.append(s('text', { x: pad.left, y: height - 10, class: 'chart-tick' }, '0'));
  svg.append(s('text', { x: width - pad.right, y: height - 26, 'text-anchor': 'end', class: 'chart-tick' },
    formatNumber(last, 0)));
  return svg;
}

function pointTable(data) {
  return h('div', { class: 'table-wrap' }, h('table', { class: 'summary-table' },
    h('thead', {}, h('tr', {}, ['Узел', 'Расстояние, м', 'L1, В', 'L2, В', 'L3, В']
      .map((name, index) => h('th', { class: index ? 'num' : null }, t(name))))),
    h('tbody', {}, data.points.map((point) => h('tr', {}, h('td', {}, t(point.name)),
      h('td', { class: 'num' }, formatNumber(point.distance_m, 1)),
      ...point.voltages.map((value) => h('td', { class: value !== null && (value < data.limits.low
        || value > data.limits.high) ? 'num bad' : 'num' }, value === null ? '—' : tenths(value))))))));
}

export async function openProfile() {
  if (!needScheme()) return;
  const chosen = state.selection && state.selection.kind === 'consumer' ? state.selection.index : null;
  const consumer = h('select', {}, h('option', { value: '' }, t('с наименьшим напряжением')),
    state.scheme.consumers.map((item, index) => h('option', { value: index, selected: index === chosen },
      `${item.label} — ${item.address}`)));
  const season = h('select', {}, h('option', { value: 1 }, t('зима')), h('option', { value: 0 }, t('лето')));
  openModal({
    title: t('Эпюра напряжения вдоль линии'),
    sections: [{ el: h('div', { class: 'row' },
      h('div', { class: 'field' }, h('label', {}, t('Потребитель'), consumer)),
      h('div', { class: 'field' }, h('label', {}, t('Сезон'), season))) }],
    okText: t('Построить'),
    async onSubmit() {
      const data = await site.post('/api/calc/profile', { scheme: state.scheme, settings: state.settings,
        consumer: consumer.value === '' ? null : Number(consumer.value), season: Number(season.value) });
      const legend = h('p', { class: 'epure-legend' }, [0, 1, 2].map((phase) => h('span', {},
        h('i', { style: `background:${colour(PHASE_TOKENS[phase])}` }), `L${phase + 1}`)),
      h('span', {}, h('i', { class: 'dash' }), t('допустимые пределы')));
      setTimeout(() => {
        openModal({ title: t('Эпюра напряжения: {name}', { name: data.points[data.points.length - 1].name }),
          sections: [{ el: legend }, { el: chart(data) }, { el: pointTable(data) }], okText: t('Закрыть'),
          onSubmit: () => true });
        wide();
      }, 0);
    },
  });
}

export async function openLosses() {
  if (!needScheme()) return;
  let data;
  try {
    data = await site.post('/api/calc/losses', { scheme: state.scheme, settings: state.settings });
  } catch (error) {
    toast(error.message, 'bad');
    return;
  }
  const rows = [
    ['Наибольшая нагрузка сети', `${formatNumber(data.peak_kw, 2)} кВт`],
    ['Годовое потребление потребителей', `${formatNumber(data.consumed_kwh, 0)} кВт·ч`],
    ['Время использования наибольшей нагрузки Tmax', `${formatNumber(data.use_hours, 0)} ч`],
    ['Время наибольших потерь τ', `${formatNumber(data.loss_hours, 0)} ч`],
    ['Потери в ЛЭП', `${formatNumber(data.lines_kwh, 0)} кВт·ч`],
    ['Потери холостого хода трансформатора', `${formatNumber(data.transformer_idle_kwh, 0)} кВт·ч`],
    ['Нагрузочные потери трансформатора', `${formatNumber(data.transformer_load_kwh, 0)} кВт·ч`],
    ['Потери энергии за год', `${formatNumber(data.total_kwh, 0)} кВт·ч`],
    ['Доля от потребления', data.share_percent === null ? '—' : `${formatNumber(data.share_percent, 2)} %`],
    ['Стоимость электроэнергии', `$${formatNumber(data.price_usd, 3)} за кВт·ч`],
    ['Стоимость потерь за год', `$${formatNumber(data.cost_usd, 2)}`],
  ];
  const body = rows.map(([name, value]) => h('tr', {}, h('td', {}, t(name)), h('td', { class: 'num' }, value)));
  const table = h('table', { class: 'summary-table losses-table' }, h('tbody', {}, body));
  const note = h('p', { class: 'muted' }, t('Потери за год оцениваются методом времени наибольших потерь: '
    + 'τ = (0,124 + Tmax/10000)² · 8760 ч, Tmax — годовое потребление, делённое на наибольшую нагрузку.'));
  openModal({ title: t('Годовые потери энергии'), sections: [{ el: table }, { el: note }], okText: t('Закрыть'),
    onSubmit: () => true });
}

export function selectedConsumer() {
  return state.selection && state.selection.kind === 'consumer' ? selectedObject() : null;
}

export async function downloadReport() {
  if (!needScheme()) return;
  try {
    const response = await fetch('/api/calc/report.docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scheme: state.scheme, name: state.name, settings: state.settings }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(t(data.detail || 'Отчёт не создан'));
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = `${t('Отчёт')} — ${state.name}.docx`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(t('Отчёт сохранён в файл .docx'));
  } catch (error) {
    toast(error.message, 'bad');
  }
}

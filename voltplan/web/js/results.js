import { $, h, s, toast } from './dom.js';
import { CONSUMER_SIZE, lineEnd } from './render.js';
import { state } from './state.js';

const TEXT_HEIGHT = 14;
const BUS_STEP = 70;
const SUM_OFFSETS = [340, 420, 500];

function label(layer, x, y, text, cls, vertical = false) {
  const attrs = { x, y, class: `res ${cls}`, 'dominant-baseline': 'hanging' };
  if (vertical) attrs.transform = `rotate(-90 ${x} ${y})`;
  layer.append(s('text', attrs, text));
}

export function shownSeason() {
  const results = state.results;
  if (!results) return null;
  if (results.labels[String(state.season)]) return state.season;
  return Number(Object.keys(results.seasons).sort().pop());
}

function consumerLabels(layer, scheme, labels) {
  scheme.consumers.forEach((consumer, index) => {
    const values = labels[index] || [];
    const shift = values.length === 3 ? 1 : 0;
    values.forEach((item, j) => {
      const y = consumer.y + (j * TEXT_HEIGHT - TEXT_HEIGHT + 2) * shift;
      label(layer, consumer.x + CONSUMER_SIZE / 2 + 2, y, item.text, item.bad ? 'res-bad' : 'res-ok');
    });
  });
}

function seasonLabels(layer, scheme, labels) {
  consumerLabels(layer, scheme, labels.consumers);
  scheme.lines.forEach((line, index) => {
    const item = labels.lines[index];
    const cls = item.bad ? 'res-bad' : 'res-temp';
    if (line.vertical === 1) label(layer, line.x + 3, line.y + 30, item.text, `${cls} res-small`, true);
    else label(layer, line.x + 10, line.y + 2, item.text, `${cls} res-mid`);
  });
  const hottest = scheme.lines[labels.max_line];
  if (hottest) {
    const end = lineEnd(hottest);
    layer.append(s('line', { x1: hottest.x, y1: hottest.y, x2: end.x, y2: end.y, class: 'res-hot' }));
  }
  const worst = scheme.consumers[labels.min_consumer];
  if (worst) {
    const phase = worst.phase_mode === 1 ? `ph${worst.phase_no}` : 'ph0';
    layer.append(s('rect', {
      x: worst.x - CONSUMER_SIZE / 2, y: worst.y, width: CONSUMER_SIZE, height: CONSUMER_SIZE,
      class: `res-worst ${phase}`,
    }));
  }
  const t = scheme.transformer;
  labels.bus.forEach((item, m) => {
    label(layer, t.x + 100 + BUS_STEP * m, t.y - 20, item.text, item.bad ? 'res-bad' : 'res-ok');
  });
  labels.sums.forEach((text, m) => label(layer, t.x + SUM_OFFSETS[m], t.y - 20, text, 'res-sum'));
  label(layer, t.x - 25, t.y + labels.transformer.length * 5 + 40, labels.transformer, 'res-temp', true);
}

export function renderResults() {
  const layer = $('layer-results');
  layer.replaceChildren();
  updateBar();
  const scheme = state.scheme;
  const season = shownSeason();
  if (!scheme || season === null) return;
  const labels = state.results.labels[String(season)];
  if (season === 2) consumerLabels(layer, scheme, labels.consumers);
  else seasonLabels(layer, scheme, labels);
}

function updateBar() {
  const bar = $('results-bar');
  const results = state.results;
  bar.hidden = !results;
  $('btn-report').disabled = !(state.reportEnabled && state.report);
  if (!results) return;
  const season = shownSeason();
  bar.querySelectorAll('input[name="season"]').forEach((input) => {
    input.disabled = !results.labels[input.value];
    input.checked = Number(input.value) === season;
  });
  const verdict = $('results-verdict');
  verdict.textContent = results.good ? 'Пропускная способность достаточна' : 'Пропускная способность недостаточна';
  verdict.className = `verdict ${results.good ? 'good' : 'bad'}`;
}

export function resultsSection(kind, index) {
  const results = state.results;
  if (!results) return null;
  const memo = kind === 'transformer' ? results.memo.transformer : results.memo[`${kind}s`]?.[index];
  if (!memo) return null;
  return h('section', { class: 'results-block' }, h('h4', {}, 'Результаты расчёта'),
    h('pre', { class: 'memo' }, memo.map((line) => h('div', { class: 'memo-line' }, line || ' '))));
}

export function openReport() {
  if (!state.report) return;
  if (!state.reportReady) {
    toast('Недостаточно потребителей в схеме!');
    return;
  }
  $('report-body').replaceChildren(...state.report.map((row) => h('p', { class: `report-row tone-${row.tone}` },
    row.text || ' ')));
  $('report').hidden = false;
}

export function closeReport() {
  $('report').hidden = true;
}

export function reportOpen() {
  return !$('report').hidden;
}

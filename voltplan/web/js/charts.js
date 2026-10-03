import { h, s } from './dom.js';
import { state } from './state.js';

const W = 288;
const H = 128;
const PAD = { left: 34, right: 8, top: 10, bottom: 20 };
const SLOTS = 48;
const SEASON_NAMES = { 0: 'Летний период', 1: 'Зимний период' };

const plotW = W - PAD.left - PAD.right;
const plotH = H - PAD.top - PAD.bottom;
const slotW = plotW / SLOTS;

function comma(value, digits) {
  if (Math.abs(value) >= 1e5) return value.toExponential(1).replace('.', ',').replace('e+', 'E');
  return value.toFixed(digits).replace('.', ',');
}

function clock(slot) {
  const minutes = slot * 30;
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
}

function finite(values) {
  return (values || []).filter((value) => Number.isFinite(value));
}

function scale(values, floor) {
  const numbers = finite(values);
  let low = Math.min(floor, ...numbers);
  let high = Math.max(...numbers, low + 1e-9);
  const raw = (high - low) / 4;
  const power = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((k) => k * power).find((k) => k >= raw * 0.999) || raw;
  low = Math.floor(low / step) * step;
  high = Math.ceil(high / step) * step;
  if (high === low) high = low + step;
  return { low, high, step, digits: Math.max(0, -Math.floor(Math.log10(step) + 1e-9)) };
}

function yOf(value, range) {
  return PAD.top + plotH - ((value - range.low) / (range.high - range.low)) * plotH;
}

function frame(svg, range) {
  for (let value = range.low; value <= range.high + range.step / 2; value += range.step) {
    const y = yOf(value, range);
    svg.append(s('line', { x1: PAD.left, x2: W - PAD.right, y1: y, y2: y, class: 'chart-grid' }));
    svg.append(s('text', { x: PAD.left - 4, y: y + 3, class: 'chart-tick', 'text-anchor': 'end' },
      comma(value, range.digits)));
  }
  for (let hour = 0; hour <= 24; hour += 6) {
    const x = PAD.left + (hour / 24) * plotW;
    svg.append(s('text', { x, y: H - 5, class: 'chart-tick', 'text-anchor': 'middle' }, String(hour)));
  }
}

function chart(label) {
  return s('svg', { viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', 'aria-label': label });
}

function loadChart(values) {
  const range = scale(values, 0);
  const svg = chart('Коэффициент загрузки по получасам');
  frame(svg, range);
  values.forEach((value, slot) => {
    if (!Number.isFinite(value)) return;
    const top = yOf(Math.max(value, range.low), range);
    const bar = s('rect', {
      x: PAD.left + slot * slotW + 0.6, y: top, width: slotW - 1.2, height: PAD.top + plotH - top,
      class: value > 1 ? 'chart-bar over' : 'chart-bar',
    });
    bar.append(s('title', {}, `${clock(slot)} — ${comma(value, 2)}`));
    svg.append(bar);
  });
  if (range.low <= 1 && range.high >= 1) {
    const y = yOf(1, range);
    svg.append(s('line', { x1: PAD.left, x2: W - PAD.right, y1: y, y2: y, class: 'chart-limit' }));
  }
  return svg;
}

function path(values, range) {
  let d = '';
  values.forEach((value, slot) => {
    if (!Number.isFinite(value)) return;
    const x = PAD.left + (slot + 0.5) * slotW;
    d += `${d ? 'L' : 'M'}${x.toFixed(1)} ${yOf(value, range).toFixed(1)}`;
  });
  return d;
}

function temperatureChart(winding, oil) {
  const range = scale([...winding, ...(oil || [])], Math.min(...finite([...winding, ...(oil || [])])));
  const svg = chart('Температура обмоток и масла по получасам');
  frame(svg, range);
  svg.append(s('path', { d: path(winding, range), class: 'chart-line winding' }));
  if (oil) svg.append(s('path', { d: path(oil, range), class: 'chart-line oil' }));
  winding.forEach((value, slot) => {
    const hit = s('rect', { x: PAD.left + slot * slotW, y: PAD.top, width: slotW, height: plotH, class: 'chart-hit' });
    const parts = [`${clock(slot)}`, `обмотки ${Number.isFinite(value) ? comma(value, 1) : '—'} °C`];
    if (oil) parts.push(`масло ${Number.isFinite(oil[slot]) ? comma(oil[slot], 1) : '—'} °C`);
    hit.append(s('title', {}, parts.join(' — ')));
    svg.append(hit);
  });
  return svg;
}

function seasonCharts(data) {
  if (!finite(data.load).length || !finite(data.winding).length) {
    return [h('p', { class: 'muted' }, 'Графики не построены: значения вне допустимого диапазона.')];
  }
  const legend = [h('span', { class: 'key winding' }, 'обмотки')];
  if (data.oil) legend.push(h('span', { class: 'key oil' }, 'масло'));
  return [
    h('p', { class: 'chart-title' }, 'Коэффициент загрузки трансформатора (без учёта мощности утяжеления нагрузки)'),
    loadChart(data.load),
    h('p', { class: 'chart-title' }, 'Температуры обмоток и масла, °C', h('span', { class: 'chart-legend' }, legend)),
    temperatureChart(data.winding, data.oil),
    h('p', { class: 'chart-axis' }, 'время суток, ч'),
  ];
}

export function transformerCharts() {
  const charts = state.results?.charts;
  if (!charts) return null;
  const seasons = Object.keys(charts).sort();
  if (!seasons.length) return null;
  let current = seasons[0];
  const body = h('div', { class: 'chart-body' });
  const show = () => body.replaceChildren(...seasonCharts(charts[current]));
  const tabs = h('div', { class: 'seg chart-tabs', role: 'radiogroup', 'aria-label': 'Период' },
    seasons.map((key) => {
      const input = h('input', { type: 'radio', name: 'chart-season', value: key, checked: key === current });
      input.addEventListener('change', () => {
        current = key;
        show();
      });
      return h('label', {}, input, SEASON_NAMES[key]);
    }));
  show();
  return h('section', { class: 'results-block charts' }, h('h4', {}, 'Расчётные суточные графики'), tabs, body);
}

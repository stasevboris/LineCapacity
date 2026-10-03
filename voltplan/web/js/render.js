import { $, s } from './dom.js';
import { state } from './state.js';

export const CONSUMER_SIZE = 10;

export function lineEnd(line) {
  return line.vertical === 1
    ? { x: line.x, y: line.y + line.canvas_length }
    : { x: line.x + line.canvas_length, y: line.y };
}

export function schemeBounds(scheme) {
  const t = scheme.transformer;
  let minX = t.x - 30, minY = t.y - 30, maxX = t.x + 40, maxY = t.y + 40;
  const grow = (x, y) => {
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  };
  for (const line of scheme.lines) {
    const end = lineEnd(line);
    grow(line.x, line.y - 32); grow(end.x, end.y);
  }
  for (const pole of scheme.poles) { grow(pole.x, pole.y - 22); grow(pole.x + pole.canvas_length + 20, pole.y); }
  for (const consumer of scheme.consumers) { grow(consumer.x - 20, consumer.y + CONSUMER_SIZE + 18); }
  return { minX, minY, maxX, maxY };
}

function busBottom(scheme) {
  const t = scheme.transformer;
  let lowest = t.y + 40;
  for (const line of scheme.lines) lowest = Math.max(lowest, line.y, lineEnd(line).y);
  for (const pole of scheme.poles) lowest = Math.max(lowest, pole.y);
  for (const consumer of scheme.consumers) lowest = Math.max(lowest, consumer.y + CONSUMER_SIZE);
  return Math.min(t.y + t.h, lowest + 30);
}

function label(layer, x, y, text, cls, vertical = false) {
  if (!text) return;
  const attrs = { x, y, class: `lbl ${cls}`, 'dominant-baseline': 'hanging' };
  if (vertical) attrs.transform = `rotate(-90 ${x} ${y})`;
  layer.append(s('text', attrs, text));
}

function lengthText(value) {
  const number = Number(value);
  return `${String(Number(number.toFixed(2))).replace('.', ',')} м`;
}

function isSelected(kind, index) {
  const sel = state.selection;
  return Boolean(sel && sel.kind === kind && (kind === 'transformer' || sel.index === index));
}

function group(kind, index) {
  const selected = isSelected(kind, index);
  return { g: s('g', { class: selected ? 'obj sel' : 'obj', 'data-kind': kind, 'data-index': index }), selected };
}

function wire(g, selected, x1, y1, x2, y2, cls) {
  if (selected) g.append(s('line', { x1, y1, x2, y2, class: 'w-halo' }));
  g.append(s('line', { x1, y1, x2, y2, class: cls }));
  g.append(s('line', { x1, y1, x2, y2, class: 'w-hit' }));
}

function paintTransformer(scheme, layers) {
  const t = scheme.transformer;
  const bottom = busBottom(scheme);
  const { g, selected } = group('transformer', 0);
  wire(g, selected, t.x, t.y, t.x, bottom, 'w-bus');
  layers.lines.append(g);
  label(layers.labels, t.x - 20, t.y - 20, t.label || t.type_name, 'lbl-bus');
}

function paintLine(line, index, layers) {
  const end = lineEnd(line);
  const { g, selected } = group('line', index);
  wire(g, selected, line.x, line.y, end.x, end.y, 'w-line');
  layers.lines.append(g);
  if (line.vertical === 1) {
    label(layers.labels, line.x - 26, line.y + 38, line.label, 'lbl-line', true);
    label(layers.labels, line.x - 13, line.y + 38, lengthText(line.length_m), 'lbl-line', true);
  } else {
    label(layers.labels, line.x + 10, line.y - 28, line.label, 'lbl-line');
    label(layers.labels, line.x + 10, line.y - 15, lengthText(line.length_m), 'lbl-line');
  }
}

function paintPole(pole, index, layers) {
  const { g, selected } = group('pole', index);
  wire(g, selected, pole.x, pole.y, pole.x + pole.canvas_length, pole.y, 'w-pole');
  layers.poles.append(g);
  label(layers.labels, pole.x + 10, pole.y - 20, pole.label, 'lbl-pole');
}

function paintConsumer(consumer, index, layers) {
  const phase = consumer.phase_mode === 1 ? `ph${consumer.phase_no}` : 'ph0';
  const { g, selected } = group('consumer', index);
  const box = { x: consumer.x - CONSUMER_SIZE / 2, y: consumer.y, width: CONSUMER_SIZE, height: CONSUMER_SIZE };
  if (selected) g.append(s('rect', { ...box, class: 'w-halo-box' }));
  g.append(s('rect', { ...box, class: `cons ${phase}` }));
  g.append(s('rect', { x: consumer.x - 9, y: consumer.y - 4, width: 18, height: 18, fill: 'transparent' }));
  layers.consumers.append(g);
  label(layers.labels, consumer.x - CONSUMER_SIZE / 2, consumer.y + 13, consumer.label, 'lbl-cons');
}

function paintPoints(scheme, layer) {
  const current = state.point;
  scheme.connection_points.forEach((point, index) => {
    if (!point.active) return;
    const g = s('g', { class: 'pt-group', 'data-point': index, 'data-x': point.x, 'data-y': point.y });
    if (current && current.x === point.x && current.y === point.y) {
      g.append(s('circle', { cx: point.x, cy: point.y, r: 7, class: 'pt-ring' }));
    }
    g.append(s('circle', { cx: point.x, cy: point.y, r: 9, class: 'pt-hit' }));
    g.append(s('circle', { cx: point.x, cy: point.y, r: 3.6, class: 'pt' }));
    layer.append(g);
  });
}

export function render() {
  const layers = {
    lines: $('layer-lines'), poles: $('layer-poles'), consumers: $('layer-consumers'),
    labels: $('layer-labels'), points: $('layer-points'),
  };
  for (const layer of Object.values(layers)) layer.replaceChildren();
  const scheme = state.scheme;
  $('empty').hidden = Boolean(scheme);
  if (!scheme) return;
  paintTransformer(scheme, layers);
  scheme.lines.forEach((line, index) => paintLine(line, index, layers));
  scheme.poles.forEach((pole, index) => paintPole(pole, index, layers));
  scheme.consumers.forEach((consumer, index) => paintConsumer(consumer, index, layers));
  paintPoints(scheme, layers.points);
}

export function applyView() {
  const { x, y, scale } = state.view;
  $('viewport').setAttribute('transform', `translate(${x} ${y}) scale(${scale})`);
  $('status-zoom').textContent = `${Math.round(scale * 100)} %`;
}

import { $ } from './dom.js';
import { applyView, schemeBounds } from './render.js';
import { state } from './state.js';

const MIN_SCALE = 0.1;
const MAX_SCALE = 6;
const DRAG_THRESHOLD = 4;

let handlers = { point() {}, object() {}, empty() {} };
let drag = null;

export function toScheme(clientX, clientY) {
  const rect = $('scene').getBoundingClientRect();
  const { x, y, scale } = state.view;
  return { x: (clientX - rect.left - x) / scale, y: (clientY - rect.top - y) / scale };
}

export function toScreen(point) {
  const rect = $('scene').getBoundingClientRect();
  const { x, y, scale } = state.view;
  return { x: rect.left + x + point.x * scale, y: rect.top + y + point.y * scale };
}

export function zoomAt(factor, clientX, clientY) {
  const rect = $('scene').getBoundingClientRect();
  const mx = clientX - rect.left;
  const my = clientY - rect.top;
  const view = state.view;
  const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, view.scale * factor));
  view.x = mx - (mx - view.x) * (next / view.scale);
  view.y = my - (my - view.y) * (next / view.scale);
  view.scale = next;
  applyView();
}

export function zoomCenter(factor) {
  const rect = $('scene').getBoundingClientRect();
  zoomAt(factor, rect.left + rect.width / 2, rect.top + rect.height / 2);
}

function resultBounds(box) {
  const layer = $('layer-results');
  if (!state.results || !layer.childElementCount) return box;
  const found = layer.getBBox();
  return {
    minX: Math.min(box.minX, found.x), minY: Math.min(box.minY, found.y),
    maxX: Math.max(box.maxX, found.x + found.width), maxY: Math.max(box.maxY, found.y + found.height),
  };
}

export function fit() {
  if (!state.scheme) return;
  const rect = $('scene').getBoundingClientRect();
  const box = resultBounds(schemeBounds(state.scheme));
  const width = Math.max(box.maxX - box.minX, 120);
  const height = Math.max(box.maxY - box.minY, 120);
  const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, 0.92 * Math.min(rect.width / width, rect.height / height)));
  state.view.scale = Math.min(scale, 2.2);
  state.view.x = rect.width / 2 - ((box.minX + box.maxX) / 2) * state.view.scale;
  state.view.y = rect.height / 2 - ((box.minY + box.maxY) / 2) * state.view.scale;
  applyView();
}

function targetOf(event) {
  const pointEl = event.target.closest('[data-point]');
  if (pointEl) return { type: 'point', x: Number(pointEl.dataset.x), y: Number(pointEl.dataset.y) };
  const objEl = event.target.closest('[data-kind]');
  if (objEl) return { type: 'object', kind: objEl.dataset.kind, index: Number(objEl.dataset.index) };
  return { type: 'empty' };
}

export function initCanvas(callbacks) {
  handlers = { ...handlers, ...callbacks };
  const scene = $('scene');

  scene.addEventListener('pointerdown', (event) => {
    if (event.button !== 0 && event.button !== 1) return;
    drag = {
      startX: event.clientX, startY: event.clientY, viewX: state.view.x, viewY: state.view.y,
      moved: false, target: targetOf(event),
    };
    scene.setPointerCapture(event.pointerId);
  });

  scene.addEventListener('pointermove', (event) => {
    if (!drag) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    drag.moved = true;
    scene.classList.add('panning');
    state.view.x = drag.viewX + dx;
    state.view.y = drag.viewY + dy;
    applyView();
  });

  const finish = (event) => {
    if (!drag) return;
    const current = drag;
    drag = null;
    scene.classList.remove('panning');
    if (current.moved) return;
    const target = current.target;
    if (target.type === 'point') handlers.point({ x: target.x, y: target.y }, event);
    else if (target.type === 'object') handlers.object(target.kind, target.index, event);
    else handlers.empty(event);
  };
  scene.addEventListener('pointerup', finish);
  scene.addEventListener('pointercancel', () => { drag = null; scene.classList.remove('panning'); });

  scene.addEventListener('wheel', (event) => {
    event.preventDefault();
    zoomAt(event.deltaY > 0 ? 0.88 : 1 / 0.88, event.clientX, event.clientY);
  }, { passive: false });

  scene.addEventListener('pointermove', (event) => {
    if (drag || !state.scheme) return;
    const p = toScheme(event.clientX, event.clientY);
    $('status-hint').textContent = `x ${Math.round(p.x)}, y ${Math.round(p.y)}`;
  });
  scene.addEventListener('pointerleave', () => {
    $('status-hint').textContent = 'Колесо — масштаб, перетаскивание — перемещение полотна.';
  });

  $('zoom-in').addEventListener('click', () => zoomCenter(1.25));
  $('zoom-out').addEventListener('click', () => zoomCenter(0.8));
  $('zoom-fit').addEventListener('click', fit);
  applyView();
}

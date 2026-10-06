const listeners = new Set();

export const state = {
  scheme: null,
  name: 'Новая схема',
  dirty: false,
  point: null,
  pointKind: 0,
  actions: [],
  selection: null,
  blocks: [],
  titles: {},
  catalog: { transformers: [], lines: [] },
  view: { x: 60, y: 40, scale: 1 },
  results: null,
  season: 1,
  report: null,
  reportReady: false,
  reportEnabled: false,
  project: null,
  readOnly: false,
  settings: {},
  settingsInfo: null,
  nextPeriod: null,
};

export function subscribe(listener) {
  listeners.add(listener);
}

export function notify(reason) {
  for (const listener of listeners) listener(reason);
}

export function applyResults(results, season) {
  state.results = results;
  state.season = season;
  state.report = results.report;
  state.reportReady = results.report_ready;
  if (results.show_report) state.reportEnabled = true;
  notify('results');
}

export function clearResults() {
  state.results = null;
  notify('results');
}

export function commit(scheme, { current = null, blocks = [] } = {}) {
  state.blocks.push(...blocks);
  state.scheme = scheme;
  state.results = null;
  state.dirty = true;
  state.selection = validSelection(state.selection);
  state.point = current && isActivePoint(current) ? current : null;
  state.actions = [];
  notify('scheme');
}

export function load(scheme, name, { blocks = [scheme], dirty = false, current = null, project = null } = {}) {
  state.scheme = scheme;
  state.name = name;
  state.project = project;
  state.readOnly = Boolean(project && project.role === 'reader');
  if (project) state.settings = { ...(project.settings || {}) };
  state.nextPeriod = null;
  state.dirty = dirty;
  state.results = null;
  state.report = null;
  state.reportReady = false;
  state.blocks = scheme ? [...blocks] : [];
  state.point = current && isActivePoint(current) ? current : null;
  state.actions = [];
  state.selection = null;
  notify('load');
}

export function adopt(scheme) {
  state.scheme = scheme;
}

export function undoBlock() {
  const count = state.blocks.length;
  return count ? state.blocks[Math.max(0, count - 2)] : null;
}

export function restore(scheme) {
  if (state.blocks.length > 1) state.blocks.pop();
  state.scheme = scheme;
  state.results = null;
  state.dirty = true;
  state.point = null;
  state.actions = [];
  state.selection = validSelection(state.selection);
  notify('scheme');
}

export function isActivePoint(point) {
  if (!state.scheme || !point) return false;
  return state.scheme.connection_points.some((p) => p.active && p.x === point.x && p.y === point.y);
}

function validSelection(selection) {
  if (!selection || !state.scheme) return null;
  if (selection.kind === 'transformer') return selection;
  const list = collection(selection.kind);
  return list && selection.index < list.length ? selection : null;
}

export function collection(kind) {
  if (!state.scheme) return null;
  return { line: state.scheme.lines, pole: state.scheme.poles, consumer: state.scheme.consumers }[kind] || null;
}

export function selectedObject() {
  const selection = state.selection;
  if (!selection || !state.scheme) return null;
  if (selection.kind === 'transformer') return state.scheme.transformer;
  const list = collection(selection.kind);
  return list ? list[selection.index] : null;
}

export function keptProject() {
  return state.project && state.project.empty && !state.readOnly ? state.project : null;
}

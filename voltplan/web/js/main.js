import { choosePoint, clearPoint, hidePopup, renderActions } from './actions.js';
import { api, site } from './api.js';
import { openCalcDialog } from './calc.js';
import { fit, initCanvas } from './canvas.js';
import { $, toast } from './dom.js';
import { closeActiveModal, initModal, modalOpen, openNewSchemeDialog, run } from './dialogs.js';
import { confirmDiscard, initExchange, openFile, saveFile } from './exchange.js';
import { closePicker, initPicker, pickerOpen } from './picker.js';
import { objectName, renderProps } from './props.js';
import { applyView, render } from './render.js';
import { closeReport, openReport, renderResults, reportOpen } from './results.js';
import { initProjects, openFromAddress, renderProjectBar, saveToProject } from './project.js';
import { startPage } from './session.js';
import { assignKind, closeMenu, initTools, menuOpen } from './tools.js';
import {
  clearResults, keptProject, load, notify, restore, selectedObject, state, subscribe, undoBlock,
} from './state.js';

function updateStats() {
  const scheme = state.scheme;
  const count = (list) => (scheme ? list.length : 0);
  $('st-out').textContent = scheme ? scheme.outgoing_count : 0;
  $('st-lines').textContent = scheme ? count(scheme.lines) : 0;
  $('st-poles').textContent = scheme ? count(scheme.poles) : 0;
  $('st-cons').textContent = scheme ? count(scheme.consumers) : 0;
  $('st-free').textContent = scheme ? scheme.connection_points.filter((p) => p.active).length : 0;
}

function updateChrome() {
  $('btn-undo').disabled = state.blocks.length === 0 || state.readOnly;
  $('btn-save').disabled = !state.scheme;
  $('btn-calc').disabled = !state.scheme;
  $('dirty').hidden = !state.dirty;
  if (document.activeElement !== $('scheme-name')) $('scheme-name').value = state.name;
}

function refresh(reason) {
  render();
  renderResults();
  renderActions();
  if (reason !== 'point' && reason !== 'season') renderProps();
  updateStats();
  updateChrome();
  renderProjectBar();
  if (reason === 'scheme' && state.point) choosePoint(state.point, { popup: false });
}

function selectObject(kind, index) {
  hidePopup();
  state.selection = { kind, index };
  notify('select');
}

function deleteSelection() {
  const selection = state.selection;
  const obj = selectedObject();
  if (!selection || !obj || selection.kind === 'transformer' || state.readOnly) return;
  if (!confirm(`Удалить ${objectName(selection.kind, obj)}?`)) return;
  run({ kind: 'delete', target: selection.kind, index: selection.index })
    .then(() => toast('Удалено'))
    .catch((error) => toast(error.message, 'bad'));
}

function newScheme() {
  if (!confirmDiscard()) return;
  openNewSchemeDialog((result) => {
    const project = keptProject();
    load(result.scheme, project ? project.name : 'Новая схема',
      { blocks: result.snapshots, dirty: true, current: result.current, project });
    requestAnimationFrame(fit);
  });
}

async function doUndo() {
  const block = undoBlock();
  if (!block || state.readOnly) return;
  try {
    const result = await api.undo(state.scheme, block);
    restore(result.scheme);
    toast('Последнее действие отменено');
  } catch (error) {
    toast(error.message, 'bad');
  }
}

function initToolbar() {
  $('btn-new').addEventListener('click', newScheme);
  $('empty-new').addEventListener('click', newScheme);
  $('btn-open').addEventListener('click', openFile);
  $('empty-open').addEventListener('click', openFile);
  $('btn-save').addEventListener('click', saveFile);
  $('btn-undo').addEventListener('click', doUndo);
  $('btn-calc').addEventListener('click', openCalcDialog);
  $('btn-report').addEventListener('click', openReport);
  $('report-close').addEventListener('click', closeReport);
  $('btn-hide-results').addEventListener('click', clearResults);
  document.querySelectorAll('#results-bar input[name="season"]').forEach((input) => {
    input.addEventListener('change', () => {
      state.season = Number(input.value);
      notify('season');
    });
  });
  $('scheme-name').addEventListener('change', () => {
    state.name = $('scheme-name').value.trim() || 'Новая схема';
    $('scheme-name').value = state.name;
  });
}

function editableTarget(event) {
  const tag = event.target.tagName;
  return tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA';
}

function initKeyboard() {
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (menuOpen()) closeMenu();
      else if (pickerOpen()) closePicker();
      else if (modalOpen()) closeActiveModal();
      else if (reportOpen()) closeReport();
      else hidePopup();
      return;
    }
    if (modalOpen() || pickerOpen()) return;
    const ctrl = event.ctrlKey || event.metaKey;
    if (ctrl && event.code === 'KeyS') { event.preventDefault(); saveToProject(); return; }
    if (ctrl && event.code === 'KeyO') { event.preventDefault(); openFile(); return; }
    if (editableTarget(event)) return;
    if (ctrl && event.code === 'KeyZ') { event.preventDefault(); doUndo(); return; }
    if (event.key === 'Delete') { deleteSelection(); return; }
    if (event.key === 'F4') { event.preventDefault(); fit(); return; }
    if (event.key === 'F7') { event.preventDefault(); openCalcDialog(); return; }
    if (event.key === 'F6') { event.preventDefault(); assignKind(true); return; }
    if ((event.key === 'Insert' || event.key === '+') && state.scheme) {
      event.preventDefault();
      if (state.point) choosePoint(state.point, { click: false });
      else toast('Сначала выберите синюю точку присоединения на схеме');
    }
  });
  window.addEventListener('beforeunload', (event) => {
    if (state.dirty) { event.preventDefault(); event.returnValue = ''; }
  });
}

async function init() {
  await startPage();
  initPicker();
  initModal();
  initExchange();
  initToolbar();
  initProjects();
  initTools();
  initKeyboard();
  initCanvas({
    point: (point) => choosePoint(point),
    object: (kind, index) => selectObject(kind, index),
    empty: () => {
      hidePopup();
      if (state.selection) { state.selection = null; notify('select'); }
    },
  });
  subscribe(refresh);
  applyView();
  refresh('load');
  try {
    state.titles = await api.titles();
    state.catalog = await api.catalog();
    const own = await site.get('/api/marks');
    state.catalog = { lines: [...own.lines, ...state.catalog.lines],
      transformers: [...own.transformers, ...state.catalog.transformers] };
  } catch (error) {
    toast(`Справочник не загружен: ${error.message}`, 'bad');
  }
  window.addEventListener('resize', () => applyView());
  clearPoint();
  await openFromAddress();
}

init();

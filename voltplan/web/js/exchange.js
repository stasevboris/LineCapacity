import { api } from './api.js';
import { fit } from './canvas.js';
import { $, toast } from './dom.js';
import { keptProject, load, state } from './state.js';

function confirmDiscard() {
  return !state.dirty || confirm('В схеме есть несохранённые изменения. Продолжить без сохранения?');
}

export function openFile() {
  if (!confirmDiscard()) return;
  $('file-cir').click();
}

export async function importFile(file) {
  try {
    const result = await api.importCir(file);
    load(result.scheme, result.name, { project: keptProject() });
    requestAnimationFrame(fit);
    toast(`Открыт файл «${file.name}»`);
  } catch (error) {
    toast(error.message, 'bad');
  }
}

function cirFileName(name) {
  return name.toLowerCase().endsWith('.cir') ? name : `${name}.cir`;
}

async function pickTarget(suggested) {
  if (!window.showSaveFilePicker || navigator.webdriver) return null;
  try {
    return await window.showSaveFilePicker({
      suggestedName: suggested,
      types: [{ description: 'Схема LineCapacity', accept: { 'application/octet-stream': ['.cir'] } }],
    });
  } catch (error) {
    if (error.name === 'AbortError') return false;
    return null;
  }
}

function download(blob, suggested) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = suggested;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function saveFile() {
  if (!state.scheme) {
    toast('Схема пуста — сохранять нечего', 'bad');
    return;
  }
  const name = ($('scheme-name').value || 'схема').trim();
  const suggested = cirFileName(name);
  try {
    const target = await pickTarget(suggested);
    if (target === false) return;
    const blob = await api.exportCir(state.scheme, name);
    if (target) {
      const writable = await target.createWritable();
      await writable.write(blob);
      await writable.close();
    } else {
      download(blob, suggested);
    }
    if (!state.project) {
      state.dirty = false;
      $('dirty').hidden = true;
    }
    toast(`Схема сохранена в файл «${target ? target.name : suggested}»`);
  } catch (error) {
    toast(error.message, 'bad');
  }
}

export function initExchange() {
  $('file-cir').addEventListener('change', (event) => {
    const file = event.target.files[0];
    event.target.value = '';
    if (file) importFile(file);
  });
}

export { confirmDiscard };

import { $, formatNumber, h } from './dom.js';
import { state } from './state.js';

const LIMIT = 300;
let current = null;

function normalize(text) {
  return String(text).toLowerCase().replace(/х/g, 'x').replace(/\s+/g, ' ').trim();
}

function subtitle(kind, mark) {
  if (kind === 'transformers') {
    return `Sн ${formatNumber(mark.sn_kva, 1)} кВА · Uк ${formatNumber(mark.uk_percent, 2)} %`;
  }
  return `Rф ${formatNumber(mark.r_phase_ohm_per_km, 4)} · R0 ${formatNumber(mark.r_neutral_ohm_per_km, 4)} Ом/км`;
}

function fill() {
  const { kind, onPick } = current;
  const query = normalize($('picker-search').value);
  const marks = state.catalog[kind] || [];
  const found = query ? marks.filter((mark) => normalize(mark.type_name).includes(query)) : marks;
  const list = $('picker-list');
  list.replaceChildren(...found.slice(0, LIMIT).map((mark) => h('button', {
    type: 'button', class: 'picker-item', role: 'option',
    onclick: () => { close(); onPick(mark); },
  }, h('span', {}, mark.type_name, mark.own ? h('em', { class: 'own-mark' }, 'моя') : null),
  h('small', {}, subtitle(kind, mark)))));
  $('picker-count').textContent = found.length > LIMIT
    ? `Показаны первые ${LIMIT} из ${found.length}. Уточните поиск.`
    : `Найдено: ${found.length}`;
}

function close() {
  $('picker').hidden = true;
  current = null;
}

export function openPicker(kind, onPick) {
  current = { kind, onPick };
  $('picker-title').textContent = kind === 'transformers'
    ? 'Справочник трансформаторов' : 'Справочник проводов и кабелей';
  $('picker-search').value = '';
  fill();
  $('picker').hidden = false;
  $('picker-search').focus();
}

export function initPicker() {
  $('picker-search').addEventListener('input', fill);
  $('picker-close').addEventListener('click', close);
  $('picker').addEventListener('click', (event) => { if (event.target === $('picker')) close(); });
  $('picker-search').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      const first = $('picker-list').querySelector('.picker-item');
      if (first) { event.preventDefault(); first.click(); }
    }
  });
}

export function pickerOpen() {
  return !$('picker').hidden;
}

export function closePicker() {
  close();
}

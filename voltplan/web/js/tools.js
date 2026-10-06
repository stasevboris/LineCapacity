import { downloadReport, openCompare, openLosses, openProfile } from './analysis.js';
import { api, site } from './api.js';
import { openCalcDialog } from './calc.js';
import { closeActiveModal, openModal } from './dialogs.js';
import { $, formatExact, formatNumber, h, parseNumber, toast } from './dom.js';
import { t } from './i18n.js';
import { openReport } from './results.js';
import { commit, notify, state } from './state.js';

const MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь',
  'Ноябрь', 'Декабрь'];
const PERIOD_NAMES = { 0: 'лето', 1: 'зима', 2: 'лето и зима' };

function number(input, caption) {
  const value = parseNumber(input.value);
  if (!Number.isFinite(value)) {
    input.classList.add('invalid');
    input.focus();
    throw new Error(t('Неверное значение: {name}', { name: t(caption) }));
  }
  input.classList.remove('invalid');
  return value;
}

function needScheme() {
  if (state.scheme) return true;
  toast(t('Сначала создайте схему или откройте файл .cir'), 'bad');
  return false;
}

function needEditable() {
  if (!needScheme()) return false;
  if (!state.readOnly) return true;
  toast(t('Проект открыт только для просмотра'), 'bad');
  return false;
}

export async function loadSettingsInfo() {
  if (!state.settingsInfo) state.settingsInfo = await api.settingsForm();
  return state.settingsInfo;
}

export function effectiveSettings(layer = state.settings) {
  const reference = state.settingsInfo ? state.settingsInfo.reference : {};
  return { ...reference, ...layer };
}

async function keepSettings(layer) {
  const same = JSON.stringify(layer) === JSON.stringify(state.settings || {});
  state.settings = layer;
  if (!same && state.project && !state.readOnly) {
    await site.put(`/api/projects/${state.project.id}/settings`, { settings: layer });
  }
}

function adoptScheme(scheme) {
  commit(scheme, { blocks: [scheme] });
}

async function assignKind(typical) {
  if (!needEditable()) return;
  const question = typical ? 'Присвоить всем потребителям типовые значения нагрузки?'
    : 'Присвоить всем потребителям индивидуальные значения нагрузки?';
  if (!confirm(t(question))) return;
  try {
    const result = await api.loadKind(state.scheme, typical, state.settings);
    await keepSettings(result.settings);
    adoptScheme(result.scheme);
    toast(t(result.message));
  } catch (error) {
    toast(error.message, 'bad');
  }
}

function settingsFields(info, layer) {
  const reference = info.reference;
  const current = { ...reference, ...layer };
  const inputs = {};
  const groups = new Map();
  for (const item of info.fields) {
    if (!groups.has(item.group)) groups.set(item.group, []);
    groups.get(item.group).push(item);
  }
  const mark = (item, row) => {
    const value = item.kind === 'flag' ? inputs[item.key].checked : parseNumber(inputs[item.key].value);
    row.classList.toggle('changed', value !== reference[item.key]);
  };
  const sections = [...groups.entries()].map(([group, items]) => {
    const rows = items.map((item) => {
      const reset = h('button', { type: 'button', class: 'icon-btn reset', title: t('Вернуть значение справочника'),
        'aria-label': t('Вернуть значение справочника') }, '↺');
      let control;
      if (item.kind === 'flag') {
        control = h('input', { type: 'checkbox', name: item.key, checked: Boolean(current[item.key]) });
      } else {
        control = h('input', { name: item.key, value: formatExact(current[item.key]), inputmode: 'decimal',
          autocomplete: 'off' });
      }
      inputs[item.key] = control;
      const caption = item.unit ? `${t(item.label)}, ${t(item.unit)}` : t(item.label);
      const row = h('div', { class: 'setting-row', 'data-key': item.key },
        h('label', { class: item.kind === 'flag' ? 'check' : '' }, item.kind === 'flag' ? control : null, caption),
        item.kind === 'flag' ? null : control, reset);
      reset.addEventListener('click', () => {
        if (item.kind === 'flag') control.checked = Boolean(reference[item.key]);
        else control.value = formatExact(reference[item.key]);
        mark(item, row);
      });
      control.addEventListener('input', () => mark(item, row));
      control.addEventListener('change', () => mark(item, row));
      mark(item, row);
      return row;
    });
    return { el: h('fieldset', { class: 'fieldset settings-group' }, h('legend', {}, t(group)), rows) };
  });
  return {
    sections,
    read() {
      const overrides = {};
      for (const item of info.fields) {
        const value = item.kind === 'flag' ? inputs[item.key].checked : number(inputs[item.key], item.label);
        if (value !== reference[item.key]) overrides[item.key] = value;
      }
      return overrides;
    },
    resetAll() {
      for (const item of info.fields) {
        const control = inputs[item.key];
        if (item.kind === 'flag') control.checked = Boolean(reference[item.key]);
        else control.value = formatExact(reference[item.key]);
        mark(item, control.closest('.setting-row'));
      }
    },
  };
}

async function openSettings() {
  let info;
  try {
    info = await loadSettingsInfo();
  } catch (error) {
    toast(error.message, 'bad');
    return;
  }
  const form = settingsFields(info, state.settings);
  const hint = state.project
    ? (state.readOnly ? 'Настройки проекта можно изменить только в этом сеансе: проект открыт для просмотра.'
      : 'Настройки сохраняются в проекте. Значения, отличные от справочника, отмечены.')
    : 'Настройки действуют до конца сеанса. Значения, отличные от справочника, отмечены.';
  const resetAll = h('button', { type: 'button', class: 'btn btn-small', onclick: () => form.resetAll() },
    t('Вернуть все значения справочника'));
  openModal({
    title: t('Настройки расчёта'),
    sections: [{ el: h('p', { class: 'muted settings-hint' }, t(hint), ' ', resetAll) }, ...form.sections],
    okText: t('Сохранить'),
    async onSubmit() {
      const overrides = form.read();
      if (!confirm(t('Вы уверены, что необходимо изменить типовые настройки расчёта?'))) return false;
      if (state.project && !state.readOnly) {
        await site.put(`/api/projects/${state.project.id}/settings`, { settings: overrides });
      }
      state.settings = overrides;
      toast(t('Настройки расчёта изменены'));
      return true;
    },
  });
  $('modal-card').classList.add('wide');
}

function monthSelect() {
  return h('select', { name: 'month' }, h('option', { value: '' }, t('— выберите месяц —')),
    MONTHS.map((name, index) => h('option', { value: index + 1 }, t(name))));
}

function openMeter() {
  if (!needEditable()) return;
  const month = monthSelect();
  const power = h('input', { name: 'p_kw', inputmode: 'decimal', autocomplete: 'off' });
  const reactive = h('input', { name: 'q_kvar', inputmode: 'decimal', autocomplete: 'off' });
  const annual = h('input', { type: 'checkbox', name: 'by_annual', checked: true });
  const el = h('fieldset', { class: 'fieldset' }, h('legend', {}, t('Мощность по балансному прибору учёта')),
    h('div', { class: 'field' }, h('label', {}, t('Месяц'), month)),
    h('div', { class: 'row' },
      h('div', { class: 'field' }, h('label', {}, t('P, кВт'), power)),
      h('div', { class: 'field' }, h('label', {}, t('Q, квар'), reactive))),
    h('label', { class: 'check' }, annual, t('Учитывать годовое потребление')));
  openModal({
    title: t('Распределение нагрузок по балансному прибору'),
    sections: [{ el }],
    okText: t('Распределить и сохранить нагрузки'),
    async onSubmit() {
      if (!month.value) throw new Error(t('Некорректные данные! Повторите ввод!'));
      const result = await api.meter(state.scheme, number(power, 'Активная мощность'),
        number(reactive, 'Реактивная мощность'), Number(month.value), annual.checked, state.settings);
      state.nextPeriod = result.season;
      adoptScheme(result.scheme);
      toast(t(result.message));
    },
  });
}

function openExcel() {
  if (!needEditable()) return;
  const file = h('input', { type: 'file', accept: '.xlsx,.xlsm', name: 'file' });
  const list = h('select', { name: 'period', size: 8, class: 'period-list', disabled: true });
  const cos = h('input', { name: 'cos_phi', value: '1,0', inputmode: 'decimal', autocomplete: 'off' });
  const air = h('input', { name: 'air', value: '0,0', inputmode: 'decimal', autocomplete: 'off' });
  const info = h('p', { class: 'muted' }, t('Файл не выбран!'));
  file.addEventListener('change', async () => {
    list.replaceChildren();
    list.disabled = true;
    if (!file.files[0]) return;
    info.textContent = t('Чтение файла…');
    try {
      const table = await api.excelPeriods(file.files[0]);
      list.replaceChildren(...table.periods.map((text, index) => h('option', { value: index, selected: index === 0 },
        text)));
      list.disabled = false;
      info.textContent = t('Приборов учёта в таблице: {count}', { count: table.meters });
    } catch (error) {
      info.textContent = error.message;
    }
  });
  const el = h('fieldset', { class: 'fieldset' }, h('legend', {}, t('Файл Excel с нагрузками потребителей')),
    h('div', { class: 'field' }, file), info,
    h('div', { class: 'field' }, h('label', {}, t('Выберите дату и время:'), list)),
    h('div', { class: 'row' },
      h('div', { class: 'field' }, h('label', {}, t('Коэффициент мощности нагрузки (косинус фи)'), cos)),
      h('div', { class: 'field' }, h('label', {}, t('Температура воздуха (град. Цельсия)'), air))));
  openModal({
    title: t('Импорт индивидуальных нагрузок потребителей из файла Excel'),
    sections: [{ el }],
    okText: t('Сохранить выбранные нагрузки'),
    async onSubmit() {
      if (!file.files[0] || list.disabled || list.value === '') throw new Error(t('Не выбрана строка в таблице!'));
      const temperature = number(air, 'Температура воздуха');
      const result = await api.excelApply(file.files[0], state.scheme, Number(list.value), number(cos, 'cos φ'),
        temperature, state.settings);
      await keepSettings(result.settings);
      adoptScheme(result.scheme);
      toast(result.messages.map((message) => t(message)).join(' '), result.found ? '' : 'bad');
    },
  });
}

export async function computeAllowed(index) {
  const results = state.results;
  if (!results || results.allowedDone) return;
  try {
    const found = await api.allowed(state.scheme, index, state.settings);
    results.allowedDone = true;
    results.memo.consumers[index] = [...results.memo.consumers[index], ...found.memo];
    state.report = found.report.map((text) => ({ text, tone: text.startsWith(' ') ? 'value' : 'info' }));
    state.reportReady = true;
    notify('select');
    openReport();
  } catch (error) {
    toast(error.message, 'bad');
  }
}

function scenarioForm(info, scenario) {
  const name = h('input', { name: 'name', value: scenario ? scenario.name : '', maxlength: 120, autocomplete: 'off' });
  const period = h('select', { name: 'period' }, [2, 0, 1].map((value) => h('option', {
    value, selected: (scenario ? scenario.period : 2) === value }, t(PERIOD_NAMES[value]))));
  const minLoad = h('input', { type: 'checkbox', name: 'min_load', checked: scenario ? scenario.min_load : true });
  const base = { ...state.settings };
  const form = settingsFields(info, { ...base, ...(scenario ? scenario.settings : {}) });
  const head = h('fieldset', { class: 'fieldset' }, h('legend', {}, t('Сценарий')),
    h('div', { class: 'field' }, h('label', {}, t('Название'), name)),
    h('div', { class: 'row' }, h('div', { class: 'field' }, h('label', {}, t('Период'), period)),
      h('label', { class: 'check' }, minLoad, t('Режим минимальных нагрузок'))));
  return {
    sections: [{ el: head }, ...form.sections],
    read() {
      if (!name.value.trim()) throw new Error(t('Название сценария не может быть пустым'));
      const overrides = form.read();
      const own = {};
      for (const [key, value] of Object.entries(overrides)) if (base[key] !== value) own[key] = value;
      return { name: name.value.trim(), settings: own, period: Number(period.value), min_load: minLoad.checked };
    },
  };
}

function editScenario(info, scenario) {
  const form = scenarioForm(info, scenario);
  openModal({
    title: t(scenario ? 'Изменить сценарий' : 'Новый сценарий'),
    sections: form.sections,
    okText: t('Сохранить'),
    async onSubmit() {
      const data = form.read();
      const path = `/api/projects/${state.project.id}/scenarios`;
      if (scenario) await site.patch(`${path}/${scenario.id}`, data);
      else await site.post(path, data);
      setTimeout(openScenarios, 0);
    },
  });
  $('modal-card').classList.add('wide');
}

function value(number, digits = 1) {
  return number === null || number === undefined ? '—' : formatNumber(number, digits);
}

function summaryTable(rows) {
  const head = ['Сценарий', 'Период', 'Заключение', 'Сезон', 'Uмин, В', 'Потребитель', 'ΔU, %', 'Потери, кВт',
    'Tмакс провода, °C', 'Загрузка ТП', 'Износ, ч', 'Uмакс мин. нагр., В'];
  const body = [];
  for (const row of rows) {
    const seasons = row.seasons.length ? row.seasons : [null];
    seasons.forEach((season, index) => {
      const first = index === 0;
      body.push(h('tr', { class: first ? 'scenario-first' : '' },
        h('td', {}, first ? row.name : ''),
        h('td', {}, first ? t(PERIOD_NAMES[row.period]) : ''),
        h('td', { class: row.good === false ? 'bad' : 'good' }, first
          ? (row.error ? t(row.error) : t(row.good ? 'достаточна' : 'недостаточна')) : ''),
        h('td', {}, season ? t(season.season) : '—'),
        h('td', { class: 'num' }, season ? value(season.min_voltage) : '—'),
        h('td', {}, season ? season.min_consumer : '—'),
        h('td', { class: 'num' }, season ? value(season.voltage_loss_percent) : '—'),
        h('td', { class: 'num' }, season ? value(season.loss_kw, 2) : '—'),
        h('td', { class: 'num' }, season ? value(season.max_temperature) : '—'),
        h('td', { class: 'num' }, season ? value(season.load_factor, 2) : '—'),
        h('td', { class: 'num' }, season ? value(season.wear_hours, 2) : '—'),
        h('td', { class: 'num' }, first ? value(row.max_voltage) : '')));
    });
  }
  return h('div', { class: 'table-wrap' }, h('table', { class: 'summary-table' },
    h('thead', {}, h('tr', {}, head.map((name) => h('th', {}, t(name))))), h('tbody', {}, body)));
}

async function runScenarios(list) {
  const result = await api.scenarios(state.scheme, state.settings, list.map((item) => ({
    name: item.name, settings: item.settings, period: item.period, min_load: item.min_load })));
  closeActiveModal();
  openModal({ title: t('Результаты по сценариям'), sections: [{ el: summaryTable(result.rows) }],
    okText: t('Закрыть'), onSubmit: () => true });
  $('modal-card').classList.add('wide');
}

export async function openScenarios() {
  if (!needScheme()) return;
  if (!state.project) {
    toast(t('Сценарии хранятся в проекте: сначала сохраните схему в проект'), 'bad');
    return;
  }
  let info;
  let list;
  try {
    info = await loadSettingsInfo();
    list = await site.get(`/api/projects/${state.project.id}/scenarios`);
  } catch (error) {
    toast(error.message, 'bad');
    return;
  }
  const editable = !state.readOnly;
  const rows = list.map((scenario) => h('li', { 'data-scenario': scenario.id },
    h('div', { class: 'who' }, h('b', {}, scenario.name),
      h('small', {}, `${t(PERIOD_NAMES[scenario.period])}${scenario.min_load ? `, ${t('мин. нагрузки')}` : ''}; `
        + t('изменённых настроек: {count}', { count: Object.keys(scenario.settings).length }))),
    h('div', { class: 'row-actions' },
      h('button', { type: 'button', class: 'btn btn-small', onclick: () => runScenarios([scenario]) }, t('Рассчитать')),
      editable ? h('button', { type: 'button', class: 'btn btn-small', onclick: () => editScenario(info, scenario) },
        t('Изменить')) : null,
      editable ? h('button', { type: 'button', class: 'btn btn-small btn-danger', onclick: async () => {
        if (!confirm(t('Удалить сценарий «{name}»?', { name: scenario.name }))) return;
        await site.remove(`/api/projects/${state.project.id}/scenarios/${scenario.id}`);
        closeActiveModal();
        openScenarios();
      } }, t('Удалить')) : null)));
  const tools = h('div', { class: 'scenario-tools' },
    editable ? h('button', { type: 'button', class: 'btn', onclick: () => editScenario(info, null) },
      t('Добавить сценарий')) : null,
    list.length ? h('button', { type: 'button', class: 'btn btn-primary', onclick: () => runScenarios(list) },
      t('Рассчитать все')) : null);
  const body = list.length ? h('ul', { class: 'project-list' }, rows)
    : h('p', { class: 'muted' }, t('Сценариев пока нет. Сценарий — это набор настроек расчёта, период и режим.'));
  openModal({ title: t('Сценарии расчёта'), sections: [{ el: body }, { el: tools }], okText: t('Закрыть'),
    onSubmit: () => true });
}

const ITEMS = [
  { id: 'tool-calc', text: 'Запуск расчёта', key: 'F7', run: () => openCalcDialog() },
  { id: 'tool-report', text: 'Основные результаты последнего расчёта', run: () => $('btn-report').click() },
  { id: 'tool-typical', text: 'Присвоить всем потребителям типовые значения нагрузки', key: 'F6',
    run: () => assignKind(true) },
  { id: 'tool-individual', text: 'Присвоить всем потребителям индивидуальные значения нагрузки',
    run: () => assignKind(false) },
  { id: 'tool-meter', text: 'Распределение нагрузок потребителей по данным с балансного прибора', run: openMeter },
  { id: 'tool-excel', text: 'Импорт индивидуальных нагрузок потребителей из файла Excel', run: openExcel },
  { id: 'tool-settings', text: 'Настройки расчёта', run: openSettings },
  { id: 'tool-scenarios', text: 'Сценарии расчёта', run: openScenarios },
  { id: 'tool-compare', text: 'Сравнение вариантов проекта', run: openCompare },
  { id: 'tool-docx', text: 'Отчёт в формате DOCX', tier: 'Профессионал', run: downloadReport },
  { id: 'tool-profile', text: 'Эпюра напряжения вдоль линии', tier: 'Максимум', run: openProfile },
  { id: 'tool-losses', text: 'Годовые потери энергии и их стоимость', tier: 'Максимум', run: openLosses },
];

function closeMenu() {
  $('calc-menu').hidden = true;
  $('btn-calc-menu').setAttribute('aria-expanded', 'false');
}

function placeMenu(menu) {
  menu.style.left = '0px';
  menu.style.maxHeight = '';
  const box = menu.getBoundingClientRect();
  const overflow = box.right - (window.innerWidth - 8);
  if (overflow > 0) menu.style.left = `${-Math.min(overflow, box.left - 8)}px`;
  menu.style.maxHeight = `${Math.max(160, window.innerHeight - box.top - 8)}px`;
}

export function initTools() {
  const menu = $('calc-menu');
  menu.replaceChildren(...ITEMS.map((item) => h('button', { type: 'button', role: 'menuitem', id: item.id,
    class: 'menu-item', onclick: () => { closeMenu(); item.run(); } },
  h('span', {}, t(item.text)), item.key ? h('kbd', {}, item.key) : null,
  item.tier ? h('em', { class: 'menu-tier' }, t(item.tier)) : null)));
  $('btn-calc-menu').addEventListener('click', (event) => {
    event.stopPropagation();
    const open = menu.hidden;
    menu.hidden = !open;
    if (open) placeMenu(menu);
    $('btn-calc-menu').setAttribute('aria-expanded', String(open));
  });
  window.addEventListener('resize', () => { if (!menu.hidden) placeMenu(menu); });
  document.addEventListener('click', (event) => {
    if (!menu.hidden && !menu.contains(event.target)) closeMenu();
  });
  loadSettingsInfo().catch(() => null);
}

export function menuOpen() {
  return !$('calc-menu').hidden;
}

export { assignKind, closeMenu };

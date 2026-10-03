import { api } from './api.js';
import { formatExact, h, parseNumber } from './dom.js';
import { openPicker } from './picker.js';

export const MAX_TEXT = 255;

export const CATEGORIES = [
  { value: 0, label: 'Бытовой без КИЭ' },
  { value: 1, label: 'Бытовой с КИЭ' },
  { value: 2, label: 'Уличное освещение' },
  { value: 3, label: 'Иной' },
];

class FormError extends Error {}

let groupNumber = 0;

function field(caption, control) {
  return h('div', { class: 'field' }, h('label', {}, caption, control));
}

function textInput(name, value) {
  return h('input', { name, value: value ?? '', autocomplete: 'off', maxlength: MAX_TEXT });
}

function numberInput(name, value) {
  return h('input', { name, value: formatExact(value), autocomplete: 'off', inputmode: 'decimal' });
}

function selectInput(name, options, value) {
  return h('select', { name }, options.map((option) => h('option', {
    value: option.value, selected: String(option.value) === String(value),
  }, option.label)));
}

function segmented(options, value, onChange) {
  groupNumber += 1;
  const name = `group-${groupNumber}`;
  const wrap = h('div', { class: 'seg', role: 'radiogroup' });
  for (const option of options) {
    const input = h('input', { type: 'radio', name, value: option.value, checked: option.value === value });
    input.addEventListener('change', () => onChange(option.value));
    wrap.append(h('label', {}, input, option.label));
  }
  return {
    el: wrap,
    set(next) {
      wrap.querySelectorAll('input').forEach((input) => { input.checked = Number(input.value) === next; });
    },
  };
}

function fail(input, message) {
  input.classList.add('invalid');
  input.focus();
  throw new FormError(message);
}

function readNumber(input, caption, { min = null, max = null, positive = false } = {}) {
  input.classList.remove('invalid');
  const value = parseNumber(input.value);
  if (!Number.isFinite(value)) fail(input, `«${caption}»: введите число`);
  if (positive && value <= 0) fail(input, `«${caption}»: значение должно быть больше нуля`);
  if (min !== null && value < min) fail(input, `«${caption}»: значение не может быть меньше ${min}`);
  if (max !== null && value > max) fail(input, `«${caption}»: значение не может быть больше ${max}`);
  return value;
}

function readName(input, message) {
  input.classList.remove('invalid');
  if (!input.value.trim()) fail(input, message);
  return input.value;
}

function section(el, read, raw) {
  const initial = raw();
  return {
    el,
    read,
    changed() {
      const data = read();
      const now = raw();
      return Object.fromEntries(Object.entries(data).filter(([key]) => now[key] !== initial[key]));
    },
  };
}

function markField(caption, input, button) {
  return h('div', { class: 'field' }, h('label', { class: 'field-label' }, caption),
    h('div', { class: 'with-button' }, input, button));
}

function stepOptions(count) {
  return (Number(count) === 3 ? [-1, 0, 1] : [-2, -1, 0, 1, 2])
    .map((n) => ({ value: n, label: n > 0 ? `+${n}` : String(n) }));
}

export function transformerSection(values, { own = values } = {}) {
  const type = textInput('type_name', values.type_name);
  const pick = h('button', { type: 'button', class: 'btn' }, 'Справочник…');
  const label = textInput('label', values.label);
  const numbers = {};
  for (const name of ['sn_kva', 'px_kw', 'pk_kw', 'uvn_kv', 'unn_kv', 'uk_percent']) {
    numbers[name] = numberInput(name, values[name]);
  }
  const steps = selectInput('pbv_steps', [{ value: 3, label: '3' }, { value: 5, label: '5' }], values.pbv_steps);
  const percent = selectInput('pbv_percent', [{ value: 2.5, label: '2,5' }, { value: 5, label: '5' }],
    values.pbv_percent);
  const step = selectInput('pbv_step', stepOptions(values.pbv_steps), values.pbv_step);
  const setSteps = (count, wanted) => {
    const limit = Number(count) === 3 ? 1 : 2;
    const chosen = Math.max(-limit, Math.min(limit, Number(wanted)));
    step.replaceChildren(...stepOptions(count).map((o) => h('option', { value: o.value, selected: o.value === chosen },
      o.label)));
  };
  steps.addEventListener('change', () => setSteps(steps.value, step.value));
  pick.addEventListener('click', () => openPicker('transformers', (mark) => {
    type.value = mark.type_name;
    label.value = own.label;
    for (const name of Object.keys(numbers)) numbers[name].value = formatExact(mark[name]);
    steps.value = String(mark.pbv_steps);
    percent.value = String(mark.pbv_percent);
    setSteps(mark.pbv_steps, own.pbv_step);
  }));
  const el = h('fieldset', { class: 'fieldset' }, h('legend', {}, 'Трансформатор'),
    markField('Марка', type, pick), field('Надпись на схеме', label),
    h('div', { class: 'row' }, field('Sн, кВА', numbers.sn_kva), field('Uк, %', numbers.uk_percent)),
    h('div', { class: 'row' }, field('Pхх, кВт', numbers.px_kw), field('Pкз, кВт', numbers.pk_kw)),
    h('div', { class: 'row' }, field('Uвн, кВ', numbers.uvn_kv), field('Uнн, кВ', numbers.unn_kv)),
    h('div', { class: 'row' }, field('Ступеней ПБВ', steps), field('Ступень ПБВ, %', percent)),
    field('Номер ступени ПБВ', step));
  const captions = { sn_kva: 'Sн', px_kw: 'Pхх', pk_kw: 'Pкз', uvn_kv: 'Uвн', unn_kv: 'Uнн', uk_percent: 'Uк' };
  const read = () => {
    const data = { type_name: readName(type, 'Укажите марку трансформатора'), label: label.value };
    for (const [name, input] of Object.entries(numbers)) {
      data[name] = readNumber(input, captions[name], { positive: true });
    }
    data.pbv_steps = Number(steps.value);
    data.pbv_step = Number(step.value);
    data.pbv_percent = Number(percent.value);
    return data;
  };
  const raw = () => {
    const data = { type_name: type.value, label: label.value, pbv_steps: steps.value, pbv_step: step.value,
      pbv_percent: percent.value };
    for (const [name, input] of Object.entries(numbers)) data[name] = input.value;
    return data;
  };
  return section(el, read, raw);
}

const MARK_PAUSE = 250;

export function lineSection(values, { own = values, single = null, title = 'ЛЭП', onPhase = null } = {}) {
  let phaseMode = Number(values.phase_mode || 0);
  const type = textInput('type_name', values.type_name);
  const pick = h('button', { type: 'button', class: 'btn' }, 'Справочник…');
  const info = h('pre', { class: 'mark-rows', 'aria-live': 'polite' });
  let markTimer = null;
  let markAsked = 0;
  const describe = (pause = MARK_PAUSE) => {
    clearTimeout(markTimer);
    markTimer = setTimeout(async () => {
      markAsked += 1;
      const asked = markAsked;
      if (!type.value.trim()) {
        info.textContent = '';
        return;
      }
      let rows = [];
      try {
        rows = await api.markRows(type.value, phaseMode);
      } catch (error) {
        rows = [];
      }
      if (asked === markAsked) info.textContent = rows.join('\n');
    }, pause);
  };
  type.addEventListener('input', () => describe());
  const label = textInput('label', values.label);
  const length = numberInput('length_m', values.length_m);
  const phaseResistance = numberInput('r_phase_ohm_per_km', values.r_phase_ohm_per_km);
  const neutralResistance = numberInput('r_neutral_ohm_per_km', values.r_neutral_ohm_per_km);
  const singleResistance = numberInput('r_single_phase_ohm_per_km', values.r_single_phase_ohm_per_km);
  const phaseNo = selectInput('phase_no', [1, 2, 3].map((n) => ({ value: n, label: `L${n}` })), values.phase_no || 1);
  const threePhase = h('div', { class: 'row' }, field('Rф, Ом/км', phaseResistance),
    field('R0, Ом/км', neutralResistance));
  const onePhase = h('div', { class: 'row' }, field('R проводов, Ом/км', singleResistance), field('Фаза', phaseNo));
  const show = () => {
    threePhase.hidden = phaseMode !== 0;
    onePhase.hidden = phaseMode !== 1;
    if (onPhase) onPhase(phaseMode, Number(phaseNo.value));
  };
  const choice = segmented([{ value: 0, label: 'Трёхфазная' }, { value: 1, label: 'Однофазная' }], phaseMode,
    (value) => {
      phaseMode = value;
      if (value === 0) {
        phaseResistance.value = formatExact(own.r_phase_ohm_per_km);
        neutralResistance.value = formatExact(own.r_neutral_ohm_per_km);
      } else {
        singleResistance.value = formatExact(own.r_single_phase_ohm_per_km);
        phaseNo.value = String(own.phase_no || 1);
      }
      show();
      describe(0);
    });
  phaseNo.addEventListener('change', show);
  let singleInput = null;
  if (single !== null) singleInput = h('input', { type: 'checkbox', checked: Boolean(single) });
  pick.addEventListener('click', () => openPicker('lines', (mark) => {
    type.value = mark.type_name;
    label.value = own.label;
    length.value = formatExact(own.length_m);
    phaseMode = mark.phase_mode;
    if (phaseMode === 0) {
      phaseResistance.value = formatExact(mark.r_phase_ohm_per_km);
      neutralResistance.value = formatExact(mark.r_neutral_ohm_per_km);
    } else {
      singleResistance.value = formatExact(mark.r_phase_ohm_per_km);
      phaseNo.value = String(own.phase_no || 1);
    }
    choice.set(phaseMode);
    show();
    describe(0);
  }));
  show();
  describe(0);
  const el = h('fieldset', { class: 'fieldset' }, h('legend', {}, title),
    markField('Марка провода', type, pick), info, field('Надпись на схеме', label), field('Длина, м', length),
    h('div', { class: 'field' }, h('span', { class: 'field-label' }, 'Фазность'), choice.el),
    threePhase, onePhase,
    singleInput ? h('label', { class: 'check' }, singleInput, 'Отпайка к одиночной опоре') : null);
  const read = () => {
    const data = {
      type_name: readName(type, 'Укажите марку провода'),
      label: label.value,
      phase_mode: phaseMode,
      length_m: readNumber(length, 'Длина', { positive: true }),
    };
    if (phaseMode === 0) {
      data.r_phase_ohm_per_km = readNumber(phaseResistance, 'Rф', { positive: true });
      data.r_neutral_ohm_per_km = readNumber(neutralResistance, 'R0', { positive: true });
    } else {
      data.r_single_phase_ohm_per_km = readNumber(singleResistance, 'R проводов', { positive: true });
      data.phase_no = Number(phaseNo.value);
    }
    return data;
  };
  const raw = () => ({
    type_name: type.value, label: label.value, phase_mode: phaseMode, length_m: length.value,
    r_phase_ohm_per_km: phaseResistance.value, r_neutral_ohm_per_km: neutralResistance.value,
    r_single_phase_ohm_per_km: singleResistance.value,
    phase_no: phaseNo.value,
  });
  return { ...section(el, read, raw), toSingle: () => (singleInput ? singleInput.checked : false) };
}

export function poleSection(values, { branchesEditable = true, title = 'Опора' } = {}) {
  const label = textInput('label', values.label);
  const count = Number(values.branch_count ?? 1);
  const top = branchesEditable ? 10 : Math.max(10, count);
  const options = Array.from({ length: top + 1 }, (_, n) => ({ value: n, label: String(n) }));
  const branches = selectInput('branch_count', options, count);
  branches.disabled = !branchesEditable;
  const el = h('fieldset', { class: 'fieldset' }, h('legend', {}, title), field('Надпись на схеме', label),
    field('Количество ответвлений', branches),
    branchesEditable
      ? h('p', { class: 'props-sub' }, 'Ответвления — точки на опоре для потребителей и других линий.')
      : null);
  const read = () => (branchesEditable
    ? { label: label.value, branch_count: Number(branches.value) }
    : { label: label.value });
  const raw = () => ({ label: label.value, branch_count: branches.value });
  return section(el, read, raw);
}

export function phaseDescription(phaseMode, phaseNo) {
  return Number(phaseMode) === 1 ? `однофазный, фаза L${phaseNo}` : 'трёхфазный';
}

function knownCategory(value) {
  return value !== null && value !== undefined && [0, 1, 2, 3].includes(Number(value));
}

export function consumerSection(values, { phase = null, typeTexts = null, title = 'Потребитель' } = {}) {
  let loadType = Number(values.load_type || 0);
  const typeText = textInput('type_text', values.type_text);
  let typeTouched = false;
  typeText.addEventListener('input', () => { typeTouched = true; });
  const label = textInput('label', values.label);
  const address = textInput('address', values.address);
  const auto = knownCategory(values.category) ? [] : [{ value: '', label: 'Определить автоматически' }];
  const category = selectInput('category', [...auto, ...CATEGORIES],
    knownCategory(values.category) ? Number(values.category) : '');
  const annual = numberInput('annual_kwh', values.annual_kwh);
  const power = numberInput('p_kw', values.p_kw);
  const cos = numberInput('cos_phi', values.cos_phi);
  const typical = h('div', {}, field('Тип потребителя', category), field('Годовое потребление, кВт·ч', annual));
  const individual = h('div', { class: 'row' }, field('Мощность P, кВт', power),
    field('Коэффициент мощности cos φ', cos));
  const show = () => { typical.hidden = loadType !== 0; individual.hidden = loadType !== 1; };
  const choice = segmented([{ value: 0, label: 'Типовые' }, { value: 1, label: 'Индивидуальные' }], loadType,
    (value) => { loadType = value; show(); });
  show();
  const feeding = h('p', { class: 'props-sub' });
  const setPhase = (phaseMode, phaseNo) => {
    feeding.textContent = `Питание: ${phaseDescription(phaseMode, phaseNo)}`;
    if (typeTexts && !typeTouched) typeText.value = typeTexts[Number(phaseMode) === 1 ? 1 : 0];
  };
  if (phase) setPhase(phase.phase_mode, phase.phase_no);
  const el = h('fieldset', { class: 'fieldset' }, h('legend', {}, title), phase ? feeding : null,
    field('Дополнительные данные', typeText), field('Надпись на схеме', label), field('Адрес', address),
    h('div', { class: 'field' }, h('span', { class: 'field-label' }, 'Параметры электропотребления'), choice.el),
    typical, individual);
  const hiddenNumber = (input, fallback) => {
    const value = parseNumber(input.value);
    return Number.isFinite(value) ? value : fallback;
  };
  const read = () => ({
    type_text: typeText.value,
    label: label.value,
    address: address.value,
    load_type: loadType,
    category: category.value === '' ? null : Number(category.value),
    annual_kwh: loadType === 0
      ? readNumber(annual, 'Годовое потребление', { min: 0 }) : hiddenNumber(annual, values.annual_kwh),
    p_kw: loadType === 1 ? readNumber(power, 'Мощность', { min: 0 }) : hiddenNumber(power, values.p_kw),
    cos_phi: loadType === 1 ? readNumber(cos, 'cos φ', { max: 1, positive: true }) : hiddenNumber(cos, values.cos_phi),
  });
  const raw = () => ({
    type_text: typeText.value, label: label.value, address: address.value, load_type: loadType,
    category: category.value, annual_kwh: annual.value, p_kw: power.value, cos_phi: cos.value,
  });
  return { ...section(el, read, raw), setPhase };
}

export { FormError };

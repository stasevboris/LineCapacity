import { api } from './api.js';
import { h, toast } from './dom.js';
import { openModal } from './dialogs.js';
import { openReport } from './results.js';
import { applyResults, state } from './state.js';

const PERIODS = [
  { value: 0, label: 'Летний период' },
  { value: 1, label: 'Зимний период' },
  { value: 2, label: 'Зимний и летний периоды' },
];

function calcSection() {
  const preset = state.nextPeriod ?? 2;
  const radios = PERIODS.map((period) => h('input', {
    type: 'radio', name: 'period', value: period.value, checked: period.value === preset,
  }));
  const minLoad = h('input', { type: 'checkbox', name: 'min_load', checked: true });
  const el = h('fieldset', { class: 'fieldset' }, h('legend', {}, 'Период'),
    h('div', { class: 'choice' }, PERIODS.map((period, i) => h('label', { class: 'check' }, radios[i], period.label))),
    h('label', { class: 'check' }, minLoad, 'Режим минимальных нагрузок'));
  return {
    el,
    read() {
      const chosen = radios.find((radio) => radio.checked);
      return { period: Number(chosen.value), minLoad: minLoad.checked };
    },
  };
}

export function openCalcDialog() {
  if (!state.scheme) {
    toast('Сначала создайте схему или откройте файл .cir', 'bad');
    return;
  }
  const section = calcSection();
  openModal({
    title: 'Выбор вида расчёта',
    sections: [section],
    okText: 'Запустить расчёт',
    async onSubmit() {
      const { period, minLoad } = section.read();
      const results = await api.calc(state.scheme, period, minLoad, state.settings);
      state.nextPeriod = null;
      applyResults(results, period === 0 ? 0 : 1);
      if (results.show_report) openReport();
    },
  });
}

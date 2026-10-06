import { site } from './api.js';
import { fit } from './canvas.js';
import { closeActiveModal, openModal } from './dialogs.js';
import { $, h, toast } from './dom.js';
import { confirmDiscard } from './exchange.js';
import { t } from './i18n.js';
import { load, notify, state } from './state.js';

export const MAIN = 'Основной';

export function shownVariant(name) {
  return name === MAIN ? t(MAIN) : name;
}

const ROLE_NAMES = { owner: 'владелец', editor: 'редактор', reader: 'читатель' };

function address(project) {
  if (!project) return '/app';
  const main = project.variants.find((variant) => variant.main);
  const variant = main && main.id === project.variant ? '' : `&variant=${project.variant}`;
  return `/app?project=${project.id}${variant}`;
}

function describe(card, variant, scheme) {
  return {
    id: card.id, name: card.name, role: card.role, variants: card.variants, variant, empty: !scheme,
    settings: card.settings || {},
  };
}

function schemeName(card, data) {
  return data.main ? card.name : `${card.name} — ${data.name}`;
}

export async function openProject(id, variant = null) {
  const query = variant ? `?variant=${variant}` : '';
  const [card, data] = await Promise.all([
    site.get(`/api/projects/${id}`), site.get(`/api/projects/${id}/scheme${query}`),
  ]);
  const project = describe(card, data.variant, data.scheme);
  load(data.scheme, schemeName(card, data), { project });
  history.replaceState(null, '', address(project));
  if (data.scheme) requestAnimationFrame(fit);
  return project;
}

function nameField(label, value) {
  const input = h('input', { class: 'input', maxlength: '120', value, 'aria-label': t(label) });
  const el = h('div', { class: 'field' }, h('label', {}, t(label)), input);
  return { el, input };
}

function adopt(card, variant) {
  state.project = describe(card, variant, true);
  state.readOnly = card.role === 'reader';
  state.dirty = false;
  history.replaceState(null, '', address(state.project));
  notify('saved');
}

function saveAsProject() {
  const field = nameField('Название проекта', state.name || t('Новая схема'));
  openModal({
    title: t('Сохранить в новый проект'),
    sections: [field],
    okText: t('Создать проект'),
    async onSubmit() {
      const card = await site.post('/api/projects', { name: field.input.value, scheme: state.scheme });
      const main = card.variants.find((variant) => variant.main);
      state.name = card.name;
      adopt(card, main.id);
      toast(t('Схема сохранена в проект «{name}»', { name: card.name }));
    },
  });
}

export async function saveToProject() {
  if (!state.scheme) {
    toast(t('Схема пуста — сохранять нечего'), 'bad');
    return;
  }
  if (!state.project) {
    saveAsProject();
    return;
  }
  if (state.readOnly) {
    toast(t('Проект открыт только для просмотра — сохранять изменения может владелец или редактор'), 'bad');
    return;
  }
  try {
    const card = await site.put(`/api/projects/${state.project.id}/scheme`,
      { scheme: state.scheme, variant: state.project.variant });
    adopt(card, state.project.variant);
    toast(t('Сохранено в проект «{name}»', { name: card.name }));
  } catch (error) {
    toast(error.message, 'bad');
  }
}

export async function openProjectsDialog() {
  let list;
  try {
    list = await site.get('/api/projects');
  } catch (error) {
    toast(error.message, 'bad');
    return;
  }
  const choose = async (project) => {
    if (!confirmDiscard()) return;
    closeActiveModal();
    try {
      await openProject(project.id);
      toast(t('Открыт проект «{name}»', { name: project.name }));
    } catch (error) {
      toast(error.message, 'bad');
    }
  };
  const rows = list.map((project) => h('li', { 'data-project': project.id },
    h('div', { class: 'who' }, h('b', { translate: 'no' }, project.name),
      h('small', {}, `${t(ROLE_NAMES[project.role])} · ${project.owner}`)),
    h('button', { class: 'btn btn-small btn-primary', type: 'button', onclick: () => choose(project) }, t('Открыть'))));
  const body = rows.length
    ? h('ul', { class: 'project-list' }, rows)
    : h('p', { class: 'muted' }, t('Проектов пока нет. Постройте схему и нажмите «Сохранить в проект».'));
  const more = h('p', { class: 'muted project-more' },
    h('a', { href: '/account#projects' }, t('Все проекты в личном кабинете')));
  openModal({ title: t('Открыть проект'), sections: [{ el: body }, { el: more }], okText: t('Закрыть'),
    onSubmit: () => true });
}

async function switchVariant() {
  const select = $('variant-select');
  const wanted = Number(select.value);
  if (!state.project || wanted === state.project.variant) return;
  if (!confirmDiscard()) {
    select.value = String(state.project.variant);
    return;
  }
  try {
    await openProject(state.project.id, wanted);
  } catch (error) {
    toast(error.message, 'bad');
    select.value = String(state.project.variant);
  }
}

function saveAsVariant() {
  if (!state.project || state.readOnly) return;
  const field = nameField('Название варианта', t('Вариант {number}', { number: state.project.variants.length + 1 }));
  openModal({
    title: t('Сохранить как новый вариант'),
    sections: [field, { el: h('p', { class: 'muted' },
      t('Текущая схема станет новым вариантом проекта; сохранённый вариант останется без изменений.')) }],
    okText: t('Создать вариант'),
    async onSubmit() {
      const project = state.project;
      const created = await site.post(`/api/projects/${project.id}/variants`,
        { name: field.input.value, source: project.variant });
      if (state.scheme) {
        await site.put(`/api/projects/${project.id}/scheme`, { scheme: state.scheme, variant: created.variant });
      }
      state.dirty = false;
      await openProject(project.id, created.variant);
      toast(t('Создан вариант «{name}»', { name: created.name }));
    },
  });
}

function renameVariant() {
  const project = state.project;
  if (!project || state.readOnly) return;
  const current = project.variants.find((variant) => variant.id === project.variant);
  const field = nameField('Название варианта', current ? shownVariant(current.name) : '');
  openModal({
    title: t('Переименовать вариант'),
    sections: [field],
    okText: t('Переименовать'),
    async onSubmit() {
      if (current && field.input.value.trim() === shownVariant(current.name)) return;
      const card = await site.patch(`/api/projects/${project.id}/variants/${project.variant}`,
        { name: field.input.value });
      state.project = { ...project, variants: card.variants };
      notify('saved');
      toast(t('Вариант переименован'));
    },
  });
}

async function deleteVariant() {
  const project = state.project;
  if (!project || state.readOnly) return;
  const current = project.variants.find((variant) => variant.id === project.variant);
  if (!current || current.main) return;
  if (!confirm(t('Удалить вариант «{name}»?', { name: current.name }))) return;
  try {
    await site.remove(`/api/projects/${project.id}/variants/${project.variant}`);
    state.dirty = false;
    await openProject(project.id);
    toast(t('Вариант удалён'));
  } catch (error) {
    toast(error.message, 'bad');
  }
}

export function renderProjectBar() {
  const project = state.project;
  $('project-bar').hidden = !project;
  $('readonly-badge').hidden = !state.readOnly;
  $('btn-save-project').disabled = !state.scheme || state.readOnly;
  if (!project) return;
  $('project-title').textContent = project.name;
  $('project-role').textContent = t(ROLE_NAMES[project.role]);
  $('project-role').className = `role role-${project.role}`;
  const select = $('variant-select');
  const options = project.variants.map((variant) => h('option',
    { value: variant.id, selected: variant.id === project.variant },
    variant.main && variant.name !== MAIN ? t('{name} (основной)', { name: variant.name })
      : shownVariant(variant.name)));
  select.replaceChildren(...options);
  $('btn-variant-new').disabled = state.readOnly;
  $('btn-variant-rename').disabled = state.readOnly;
  const current = project.variants.find((variant) => variant.id === project.variant);
  $('btn-variant-delete').disabled = state.readOnly || !current || current.main;
}

export function initProjects() {
  $('btn-projects').addEventListener('click', openProjectsDialog);
  $('btn-save-project').addEventListener('click', saveToProject);
  $('variant-select').addEventListener('change', switchVariant);
  $('btn-variant-new').addEventListener('click', saveAsVariant);
  $('btn-variant-rename').addEventListener('click', renameVariant);
  $('btn-variant-delete').addEventListener('click', deleteVariant);
}

export async function openFromAddress() {
  const params = new URLSearchParams(location.search);
  const id = Number(params.get('project'));
  if (!id) return;
  try {
    await openProject(id, Number(params.get('variant')) || null);
  } catch (error) {
    toast(error.message, 'bad');
    history.replaceState(null, '', '/app');
  }
}

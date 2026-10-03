import { api } from './api.js';
import { $, toast } from './dom.js';
import { consumerSection, lineSection, poleSection, transformerSection } from './forms.js';
import { commit, state } from './state.js';

let submitHandler = null;

function closeModal() {
  $('modal').hidden = true;
  $('modal-body').replaceChildren();
  submitHandler = null;
}

export function modalOpen() {
  return !$('modal').hidden;
}

export function openModal({ title, sections, okText = 'Сохранить', onSubmit }) {
  $('modal-title').textContent = title;
  $('modal-body').replaceChildren(...sections.map((part) => part.el));
  $('modal-ok').textContent = okText;
  $('modal-error').textContent = '';
  $('modal-ok').disabled = false;
  submitHandler = onSubmit;
  $('toast').hidden = true;
  $('modal').hidden = false;
  const first = $('modal-body').querySelector('input:not([type=radio]):not([type=checkbox]), select');
  if (first) first.focus();
}

export function initModal() {
  $('modal-close').addEventListener('click', closeModal);
  $('modal-cancel').addEventListener('click', closeModal);
  $('modal-card').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!submitHandler) return;
    $('modal-error').textContent = '';
    $('modal-ok').disabled = true;
    try {
      const done = await submitHandler();
      if (done !== false) closeModal();
    } catch (error) {
      $('modal-error').textContent = error.message;
    } finally {
      $('modal-ok').disabled = false;
    }
  });
}

export function closeActiveModal() {
  closeModal();
}

export async function run(action) {
  const result = await api.apply(state.scheme, action);
  if (action.kind === 'delete') state.selection = null;
  commit(result.scheme, { current: result.current, blocks: result.snapshots });
  return result;
}

async function values(kind, point) {
  try {
    return await api.form(state.scheme, kind, point);
  } catch (error) {
    toast(error.message, 'bad');
    return null;
  }
}

export async function openNewSchemeDialog(onDone) {
  const form = await values('new', null);
  if (!form) return;
  const transformer = transformerSection(form.transformer);
  const line = lineSection(form.line, { own: form.blank, title: 'Первая отходящая ЛЭП' });
  const pole = poleSection(form.pole, { title: 'Первая опора' });
  openModal({
    title: form.title,
    sections: [transformer, line, pole],
    okText: 'Создать схему',
    async onSubmit() {
      const action = { kind: 'new', transformer: transformer.read(), line: line.read(), pole: pole.read() };
      onDone(await api.apply(null, action));
    },
  });
}

function build(kind, point, form) {
  if (kind === 'outgoing' || kind === 'span' || kind === 'branch_line') {
    const line = lineSection(form.line, { own: form.blank, single: kind === 'branch_line' ? false : null });
    const pole = poleSection(form.pole);
    return {
      sections: [line, pole],
      action: () => ({ kind, point, line: line.read(), pole: pole.read(), to_single: line.toSingle() }),
    };
  }
  if (kind === 'branch_consumer') {
    let consumer = null;
    const line = lineSection(form.line, {
      own: form.blank,
      onPhase: (phaseMode, phaseNo) => { if (consumer) consumer.setPhase(phaseMode, phaseNo); },
    });
    consumer = consumerSection(form.consumer, { phase: form.line, typeTexts: form.type_texts });
    return {
      sections: [line, consumer],
      action: () => ({ kind, point, line: line.read(), consumer: consumer.read() }),
    };
  }
  if (kind === 'pole') {
    const pole = poleSection(form.pole);
    return { sections: [pole], action: () => ({ kind, point, pole: pole.read() }) };
  }
  if (kind === 'consumer') {
    const consumer = consumerSection(form.consumer, { phase: form.feeding });
    return { sections: [consumer], action: () => ({ kind, point, consumer: consumer.read() }) };
  }
  return null;
}

export async function openActionDialog(kind, point) {
  const form = await values(kind, point);
  if (!form) return;
  const dialog = build(kind, point, form);
  if (!dialog) return;
  openModal({
    title: form.title,
    sections: dialog.sections,
    async onSubmit() {
      await run(dialog.action());
    },
  });
}

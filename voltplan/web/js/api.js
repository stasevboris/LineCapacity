async function failure(response) {
  let detail = '';
  try {
    const data = await response.json();
    detail = typeof data.detail === 'string' ? data.detail
      : Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join('; ') : '';
  } catch (error) {
    detail = '';
  }
  return new Error(detail || `Ошибка сервера (${response.status})`);
}

async function send(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new Error('Сервер недоступен. Проверьте, что VoltPlan запущен.');
  }
  if (!response.ok) throw await failure(response);
  return response;
}

async function postJson(path, body) {
  const response = await send(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
}

export const api = {
  async catalog() {
    return (await send('/api/catalog')).json();
  },
  async markRows(typeName, phaseMode) {
    const query = new URLSearchParams({ type_name: typeName, phase_mode: String(phaseMode) });
    return (await (await send(`/api/catalog/mark?${query}`)).json()).rows;
  },
  async titles() {
    return (await send('/api/scheme/titles')).json();
  },
  menu(scheme, point) {
    return postJson('/api/scheme/menu', { scheme, point });
  },
  calc(scheme, period, minLoad) {
    return postJson('/api/calc', { scheme, period, min_load: minLoad });
  },
  undo(scheme, block) {
    return postJson('/api/scheme/undo', { scheme, block });
  },
  form(scheme, kind, point) {
    return postJson('/api/scheme/form', { scheme, kind, point });
  },
  apply(scheme, action) {
    return postJson('/api/scheme/apply', { scheme, action });
  },
  async importCir(file) {
    const form = new FormData();
    form.append('file', file);
    return (await send('/api/exchange/import', { method: 'POST', body: form })).json();
  },
  async exportCir(scheme, name) {
    const response = await send('/api/exchange/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scheme, name }),
    });
    return response.blob();
  },
};

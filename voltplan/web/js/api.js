import { t } from './i18n.js';

const PROTECTED = ['/app', '/account', '/admin'];

function goToLogin() {
  const here = location.pathname + location.search + location.hash;
  location.href = `/login?next=${encodeURIComponent(here)}`;
}

async function failure(response) {
  let detail = '';
  try {
    const data = await response.json();
    detail = typeof data.detail === 'string' ? data.detail
      : Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join('; ') : '';
  } catch (error) {
    detail = '';
  }
  const problem = new Error(detail ? t(detail) : t('Ошибка сервера ({status})', { status: response.status }));
  problem.status = response.status;
  return problem;
}

async function send(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new Error(t('Сервер недоступен. Проверьте, что VoltPlan запущен.'));
  }
  if (response.status === 401 && PROTECTED.some((prefix) => location.pathname.startsWith(prefix))) {
    goToLogin();
  }
  if (!response.ok) throw await failure(response);
  return response;
}

function jsonCall(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  return send(path, options).then((response) => response.json());
}

function postJson(path, body) {
  return jsonCall('POST', path, body);
}

export const site = {
  get: (path) => jsonCall('GET', path),
  post: (path, body) => jsonCall('POST', path, body ?? {}),
  put: (path, body) => jsonCall('PUT', path, body),
  patch: (path, body) => jsonCall('PATCH', path, body),
  remove: (path) => jsonCall('DELETE', path),
  async form(path, data) {
    return (await send(path, { method: 'POST', body: data })).json();
  },
};

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
  calc(scheme, period, minLoad, settings = null) {
    return postJson('/api/calc', { scheme, period, min_load: minLoad, settings });
  },
  async settingsForm() {
    return (await send('/api/calc/settings')).json();
  },
  loadKind(scheme, typical, settings) {
    return postJson('/api/calc/load-kind', { scheme, typical, settings });
  },
  allowed(scheme, index, settings) {
    return postJson('/api/calc/allowed', { scheme, index, settings });
  },
  meter(scheme, pKw, qKvar, month, byAnnual, settings) {
    return postJson('/api/calc/meter', { scheme, p_kw: pKw, q_kvar: qKvar, month, by_annual: byAnnual, settings });
  },
  scenarios(scheme, settings, scenarios) {
    return postJson('/api/calc/scenarios', { scheme, settings, scenarios });
  },
  async excelPeriods(file) {
    const form = new FormData();
    form.append('file', file);
    return (await send('/api/calc/excel/periods', { method: 'POST', body: form })).json();
  },
  async excelApply(file, scheme, period, cosPhi, air, settings) {
    const form = new FormData();
    form.append('file', file);
    form.append('scheme', JSON.stringify(scheme));
    form.append('period', String(period));
    form.append('cos_phi', String(cosPhi));
    form.append('air', String(air));
    form.append('settings', JSON.stringify(settings || {}));
    return (await send('/api/calc/excel/apply', { method: 'POST', body: form })).json();
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

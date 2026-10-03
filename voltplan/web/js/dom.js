export const $ = (id) => document.getElementById(id);

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
    else if (value === true) el.setAttribute(key, '');
    else el.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child === undefined || child === null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

export function s(tag, attrs = {}, text) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null) continue;
    el.setAttribute(key, value);
  }
  if (text !== undefined) el.textContent = text;
  return el;
}

export function formatNumber(value, digits = 3) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '';
  return String(Number(number.toFixed(digits))).replace('.', ',');
}

export function formatExact(value) {
  const number = Number(value);
  if (value === null || value === undefined || value === '' || !Number.isFinite(number)) return '';
  if (Number.isInteger(number) && Math.abs(number) < 1e15) return String(number);
  const rounded = Number(number.toPrecision(15));
  const [mantissa, power] = rounded.toExponential(14).split('e');
  const exponent = Number(power);
  if (exponent < -4 || exponent >= 15) {
    const digits = mantissa.includes('.') ? mantissa.replace(/0+$/, '').replace(/\.$/, '') : mantissa;
    return `${digits}E${exponent}`.replace('.', ',');
  }
  return String(rounded).replace('.', ',');
}

export function parseNumber(text) {
  const cleaned = String(text).trim().replace(/\s+/g, '').replace(',', '.');
  if (!/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(cleaned)) return NaN;
  return Number(cleaned);
}

let toastTimer = null;

export function toast(message, kind = '') {
  const el = $('toast');
  el.textContent = message;
  el.className = 'toast' + (kind ? ' ' + kind : '');
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, kind === 'bad' ? 5200 : 3200);
}

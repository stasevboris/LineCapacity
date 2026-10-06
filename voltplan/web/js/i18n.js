const STORAGE_KEY = 'voltplan-language';

export const LANGUAGES = { ru: 'Русский', en: 'English', zh: '中文' };

let current = 'ru';
let words = {};
let patterns = [];

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function compile(dictionary) {
  const list = [];
  for (const [source, target] of Object.entries(dictionary)) {
    if (!/\{\w+\}/.test(source)) continue;
    const names = [];
    const body = source.split(/(\{\w+\})/).map((part) => {
      const match = part.match(/^\{(\w+)\}$/);
      if (!match) return escapeRegex(part);
      names.push(match[1]);
      return '(.*?)';
    }).join('');
    const literal = source.replace(/\{\w+\}/g, '').length;
    list.push({ regex: new RegExp(`^${body}$`, 's'), names, target, literal });
  }
  return list.sort((first, second) => second.literal - first.literal);
}

function fill(text, values) {
  if (!values) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name) => (name in values ? String(values[name]) : whole));
}

export function t(text, values) {
  if (text === undefined || text === null) return '';
  const source = String(text);
  if (current === 'ru') return fill(source, values);
  if (Object.prototype.hasOwnProperty.call(words, source)) return fill(words[source], values);
  if (!values) {
    for (const pattern of patterns) {
      const match = source.match(pattern.regex);
      if (!match) continue;
      const found = {};
      pattern.names.forEach((name, index) => {
        const part = match[index + 1];
        const core = part.trim();
        found[name] = core ? part.replace(core, t(core)) : part;
      });
      return fill(pattern.target, found);
    }
  }
  return fill(source, values);
}

export function language() {
  return current;
}

function stored() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    return null;
  }
}

export function remember(code) {
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch (error) {
    return;
  }
}

function guess() {
  const browser = (navigator.language || 'ru').slice(0, 2).toLowerCase();
  return browser in LANGUAGES ? browser : 'ru';
}

export async function loadLanguage(preferred) {
  const code = [stored(), preferred, guess()].find((item) => item && item in LANGUAGES) || 'ru';
  current = code;
  document.documentElement.lang = code === 'zh' ? 'zh-CN' : code;
  if (code === 'ru') {
    words = {};
    patterns = [];
    return code;
  }
  try {
    const response = await fetch(`/i18n/${code}.json`, { cache: 'no-cache' });
    words = response.ok ? await response.json() : {};
  } catch (error) {
    words = {};
  }
  patterns = compile(words);
  return code;
}

const ATTRIBUTES = ['title', 'placeholder', 'aria-label'];
const CYRILLIC = /[А-Яа-яЁё]/;
const SKIPPED = new Set(['SCRIPT', 'STYLE', 'TEXTAREA']);

function translateText(node) {
  const value = node.nodeValue;
  if (!value || !CYRILLIC.test(value)) return;
  const trimmed = value.trim();
  const core = trimmed.includes('\n') ? trimmed.replace(/\s+/g, ' ') : trimmed;
  const result = t(core);
  if (result === core) return;
  const lead = value.slice(0, value.length - value.trimStart().length);
  const tail = value.slice(value.trimEnd().length);
  node.nodeValue = lead + result + tail;
}

function translateAttributes(element) {
  for (const name of ATTRIBUTES) {
    const value = element.getAttribute && element.getAttribute(name);
    if (value && CYRILLIC.test(value)) {
      const result = t(value);
      if (result !== value) element.setAttribute(name, result);
    }
  }
}

function accept(node) {
  if (node.nodeType === Node.ELEMENT_NODE) {
    if (SKIPPED.has(node.tagName) || node.getAttribute('translate') === 'no') return NodeFilter.FILTER_REJECT;
    return NodeFilter.FILTER_SKIP;
  }
  return NodeFilter.FILTER_ACCEPT;
}

function translateTree(root) {
  if (root.nodeType === Node.TEXT_NODE) {
    const parent = root.parentElement;
    if (parent && !parent.closest('[translate="no"]') && !SKIPPED.has(parent.tagName)) translateText(root);
    return;
  }
  if (root.nodeType !== Node.ELEMENT_NODE || root.closest('[translate="no"]')) return;
  translateAttributes(root);
  root.querySelectorAll('[title], [placeholder], [aria-label]').forEach((element) => {
    if (!element.closest('[translate="no"]')) translateAttributes(element);
  });
  const shown = NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT;
  const walker = document.createTreeWalker(root, shown, { acceptNode: accept });
  for (let node = walker.nextNode(); node; node = walker.nextNode()) translateText(node);
}

export function translatePage(root = document.body) {
  if (current === 'ru' || !root) return;
  document.title = t(document.title);
  translateTree(root);
  const observer = new MutationObserver((changes) => {
    for (const change of changes) {
      if (change.type === 'characterData') translateTree(change.target);
      else if (change.type === 'attributes') translateAttributes(change.target);
      else change.addedNodes.forEach((node) => translateTree(node));
    }
  });
  observer.observe(root, { subtree: true, childList: true, characterData: true, attributes: true,
    attributeFilter: ATTRIBUTES });
}

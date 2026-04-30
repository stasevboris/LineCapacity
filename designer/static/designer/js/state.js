/**
 * state.js — центральное хранилище состояния редактора схем.
 *
 * Все остальные модули (canvas, nodes, lines, properties, catalog) работают
 * именно с window.App.state, не храня собственных копий переменных.
 *
 * Также здесь кешируются ссылки на ключевые DOM-узлы SVG-сцены (window.App.dom),
 * чтобы каждый модуль не искал их заново через getElementById.
 */
(function () {
    'use strict';

    const App = (window.App = window.App || {});

    App.config = {
        GRID: 50,
        HISTORY_LIMIT: 30,
        CATALOG_PAGE_SIZE: 50,
    };

    App.state = {
        // Отображение
        scale: 1,
        viewX: 0,
        viewY: 0,
        mode: 'SELECT',

        // Данные
        nodes: [],
        lines: [],
        history: [],

        // Выделение
        selectedNodeIds: [],
        selectedLineId: null,
        selectedElements: { nodeIds: new Set(), lineIds: new Set() },

        // Рисование линий
        isDrawing: false,
        currentLinePoints: [],
        startNodeId: null,
        pendingLineData: null,

        // Взаимодействие с холстом
        isPanning: false,
        isDragging: false,
        isSelecting: false,
        draggingHandle: null,
        hoveredNodeId: null,

        // Для группового перемещения
        startX: 0,
        startY: 0,
        initialNodes: [],
        initialLines: [],

        // Размещение узла, выбранного из каталога
        nodeToPlace: null,

        // Каталог
        currentCatalogCategory: '',
        currentCatalogPage: 1,

        // Загруженная схема (для перезаписи при последующем сохранении)
        currentLoadedSchemeId: null,
    };

    // DOM-ссылки заполняются после DOMContentLoaded в main.js
    App.dom = {};

    // Утилиты, используемые многими модулями
    App.snap = function (v) {
        return Math.round(v / App.config.GRID) * App.config.GRID;
    };

    App.getCoords = function (e) {
        const r = App.dom.scene.getBoundingClientRect();
        const { viewX, viewY, scale } = App.state;
        return {
            x: (e.clientX - r.left - viewX) / scale,
            y: (e.clientY - r.top - viewY) / scale,
        };
    };

    App.saveState = function () {
        const { nodes, lines, history } = App.state;
        history.push(JSON.stringify({ nodes, lines }));
        if (history.length > App.config.HISTORY_LIMIT) history.shift();
    };

    App.escapeHtml = function (s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    // Обратная совместимость: старый код (inline-handlers в шаблонах) читает window.nodes / window.lines.
    Object.defineProperty(window, 'nodes', {
        configurable: true,
        get: () => App.state.nodes,
        set: (v) => { App.state.nodes = v; },
    });
    Object.defineProperty(window, 'lines', {
        configurable: true,
        get: () => App.state.lines,
        set: (v) => { App.state.lines = v; },
    });
    Object.defineProperty(window, 'nodeToPlace', {
        configurable: true,
        get: () => App.state.nodeToPlace,
        set: (v) => { App.state.nodeToPlace = v; },
    });
    Object.defineProperty(window, 'currentLoadedSchemeId', {
        configurable: true,
        get: () => App.state.currentLoadedSchemeId,
        set: (v) => { App.state.currentLoadedSchemeId = v; },
    });
})();

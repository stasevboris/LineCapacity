/**
 * nodes.js — менеджер узлов (ТП, опоры, абоненты, текстовые блоки).
 *
 * NodeManager отвечает только за «жизнь» узлов:
 *   * отрисовку в слой nodesLayer
 *   * drag-and-drop из библиотеки в холст
 *   * проверку возможности подключения к опоре (canConnect)
 *   * мутацию параметров из панели свойств
 */
(function () {
    'use strict';

    const App = window.App;
    const SVG_NS = 'http://www.w3.org/2000/svg';

    class NodeManager {
        // --------------------------- рендер --------------------------- //
        renderAll() {
            const { nodes, selectedNodeIds, hoveredNodeId } = App.state;
            const layer = App.dom.nodesLayer;

            nodes.forEach((n) => {
                const g = document.createElementNS(SVG_NS, 'g');

                if (n.type === 'TEXT') {
                    const t = document.createElementNS(SVG_NS, 'text');
                    t.setAttribute('x', n.x);
                    t.setAttribute('y', n.y);
                    t.textContent = n.name;
                    t.classList.add('text-node');
                    t.style.fontSize = (n.fontSize || 16) + 'px';
                    if (selectedNodeIds.includes(n.id)) t.classList.add('selected');
                    g.appendChild(t);
                    layer.appendChild(g);
                    return;
                }

                const visuals = document.createElementNS(SVG_NS, 'g');
                visuals.classList.add('node');

                // Запасной круг с цветом по типу (если нет иконки)
                const fallbackColors = { 'ТП': '#e74c3c', 'Опора': '#3498db', 'Абонент': '#2ecc71' };
                const fallbackColor = fallbackColors[n.type] || '#7f8c8d';

                const fallbackCircle = document.createElementNS(SVG_NS, 'circle');
                fallbackCircle.setAttribute('cx', n.x);
                fallbackCircle.setAttribute('cy', n.y);
                fallbackCircle.setAttribute('r', 15);
                fallbackCircle.setAttribute('fill', '#1e1e1e');
                fallbackCircle.setAttribute('stroke', fallbackColor);
                fallbackCircle.setAttribute('stroke-width', '3');
                visuals.appendChild(fallbackCircle);

                const errorText = document.createElementNS(SVG_NS, 'text');
                errorText.setAttribute('x', n.x);
                errorText.setAttribute('y', n.y + 3);
                errorText.setAttribute('fill', '#e74c3c');
                errorText.setAttribute('font-size', '9px');
                errorText.setAttribute('text-anchor', 'middle');
                errorText.setAttribute('font-weight', 'bold');
                errorText.setAttribute('pointer-events', 'none');
                errorText.textContent = 'Нет фото';
                errorText.style.display = 'none';
                visuals.appendChild(errorText);

                const iconPaths = {
                    'ТП': '/static/designer/icons/tp.svg',
                    'Опора': '/static/designer/icons/pole.svg',
                    'Абонент': '/static/designer/icons/home.svg',
                };
                const iconPath = iconPaths[n.type] || '';

                if (iconPath) {
                    const iconSize = 40;
                    const offset = iconSize / 2;
                    const img = document.createElementNS(SVG_NS, 'image');
                    img.setAttribute('href', iconPath);
                    img.setAttribute('x', n.x - offset);
                    img.setAttribute('y', n.y - offset);
                    img.setAttribute('width', iconSize);
                    img.setAttribute('height', iconSize);
                    img.addEventListener('load', () => {
                        fallbackCircle.style.display = 'none';
                    });
                    img.addEventListener('error', () => {
                        img.style.display = 'none';
                        errorText.style.display = 'block';
                    });
                    if (selectedNodeIds.includes(n.id)) img.classList.add('selected');
                    if (hoveredNodeId === n.id) img.classList.add('can-attach');
                    visuals.appendChild(img);
                } else {
                    errorText.style.display = 'block';
                }

                if (selectedNodeIds.includes(n.id)) fallbackCircle.classList.add('selected');
                if (hoveredNodeId === n.id) fallbackCircle.classList.add('can-attach');

                g.appendChild(visuals);

                // Название под иконкой
                const label = document.createElementNS(SVG_NS, 'text');
                label.setAttribute('x', n.x);
                label.setAttribute('y', n.y + 35);
                label.textContent = n.name;
                label.classList.add('node-label');
                g.appendChild(label);

                layer.appendChild(g);
            });
        }

        // ------------------------ бизнес-логика ------------------------ //
        canConnectToNode(nodeId, lineIdToIgnore = null) {
            const node = App.state.nodes.find((n) => n.id === nodeId);
            if (!node || node.type === 'TEXT') return false;

            if (node.type === 'Опора') {
                const maxBranches = node.params?.branches_count || 0;
                const connected = App.state.lines.filter(
                    (l) =>
                        l.id !== lineIdToIgnore &&
                        (l.startNodeId === nodeId || l.endNodeId === nodeId)
                );
                return connected.length < maxBranches;
            }
            return true;
        }

        // ---------------------- drag-and-drop ---------------------- //
        initDragAndDrop() {
            const canvasCont = document.getElementById('canvas-container');
            canvasCont.ondragover = (e) => e.preventDefault();
            canvasCont.ondrop = (e) => {
                const raw = e.dataTransfer.getData('app/node-data');
                if (!raw) return;
                const nodeData = JSON.parse(raw);
                App.saveState();
                const c = App.getCoords(e);
                const newNode = {
                    id: Date.now(),
                    x: App.snap(c.x),
                    y: App.snap(c.y),
                    type: nodeData.type,
                    name: nodeData.name,
                    db_id: null,
                    params: {},
                };
                if (newNode.type === 'Опора') {
                    newNode.params.branches_count = 0;
                }
                App.state.nodes.push(newNode);
                App.render();
                App.propertyPanel.update();
            };

            document.querySelectorAll('.lib-item[data-type]').forEach((i) => {
                i.setAttribute('draggable', 'true');
                i.ondragstart = (e) => {
                    const cleanName = i.innerText
                        .replace('🗼 ', '')
                        .replace('⚡ ', '')
                        .replace('🏠 ', '')
                        .trim();
                    e.dataTransfer.setData(
                        'app/node-data',
                        JSON.stringify({ type: i.dataset.type, name: cleanName })
                    );
                };
            });
        }
    }

    App.nodeManager = new NodeManager();

    // ------------------ мутаторы, вызываемые из шаблонов ------------------ //
    window.updateNodeName = function (v) {
        App.saveState();
        const { selectedNodeIds, selectedLineId, nodes, lines } = App.state;
        if (selectedNodeIds.length === 1) {
            const n = nodes.find((n) => n.id === selectedNodeIds[0]);
            if (n) n.name = v;
        } else if (selectedLineId) {
            const l = lines.find((l) => l.id === selectedLineId);
            if (l) l.name = v;
        }
        App.render();
    };

    window.updateTextSize = function (v) {
        const { selectedNodeIds, nodes } = App.state;
        if (selectedNodeIds.length !== 1) return;
        App.saveState();
        const n = nodes.find((n) => n.id === selectedNodeIds[0]);
        if (n && n.type === 'TEXT') {
            n.fontSize = parseInt(v) || 16;
            App.render();
        }
    };

    window.updateNodeParam = function (param, value) {
        const { selectedNodeIds, nodes } = App.state;
        if (selectedNodeIds.length !== 1) return;
        App.saveState();
        const n = nodes.find((n) => n.id === selectedNodeIds[0]);
        if (n) {
            if (!n.params) n.params = {};
            n.params[param] = value;
        }
        App.render();
    };
})();

/**
 * lines.js — менеджер ЛЭП.
 *
 * LineManager рисует линии в linesLayer, ручки редактирования в handlesLayer,
 * и предоставляет точечные операции (modifyLink, manualMovePoint, update-параметр).
 */
(function () {
    'use strict';

    const App = window.App;
    const SVG_NS = 'http://www.w3.org/2000/svg';

    class LineManager {
        renderAll() {
            const { nodes, lines, selectedLineId, draggingHandle } = App.state;
            const linesLayer = App.dom.linesLayer;
            const handlesLayer = App.dom.handlesLayer;

            lines.forEach((line) => {
                // Прилипаем концевыми точками к координатам узлов
                const sn = nodes.find((n) => n.id === line.startNodeId);
                const en = nodes.find((n) => n.id === line.endNodeId);
                if (sn) { line.points[0].x = sn.x; line.points[0].y = sn.y; }
                if (en) {
                    const last = line.points.length - 1;
                    line.points[last].x = en.x;
                    line.points[last].y = en.y;
                }

                const ortho = App.canvas.getOrthogonalSegments(line.points);

                const poly = document.createElementNS(SVG_NS, 'polyline');
                poly.setAttribute('points', ortho.map((p) => `${p.x},${p.y}`).join(' '));
                poly.classList.add('line-path');

                // Подпись марки/имени посередине
                if (line.mark || line.name) {
                    const midIndex = Math.floor(ortho.length / 2);
                    const midPoint = ortho[midIndex];
                    const text = document.createElementNS(SVG_NS, 'text');
                    text.setAttribute('x', midPoint.x);
                    text.setAttribute('y', midPoint.y - 10);
                    text.setAttribute('fill', '#aaa');
                    text.setAttribute('font-size', '10');
                    text.setAttribute('text-anchor', 'middle');
                    text.textContent = line.mark || line.name;
                    text.style.pointerEvents = 'none';
                    linesLayer.appendChild(text);
                }

                if (selectedLineId === line.id) {
                    poly.classList.add('selected');
                    line.points.forEach((p, idx) => {
                        const h = document.createElementNS(SVG_NS, 'circle');
                        h.setAttribute('cx', p.x);
                        h.setAttribute('cy', p.y);
                        h.setAttribute('r', 6);
                        h.classList.add('line-handle');
                        if (
                            draggingHandle &&
                            draggingHandle.lineId === line.id &&
                            draggingHandle.index === idx
                        ) {
                            h.classList.add('active');
                        }
                        handlesLayer.appendChild(h);
                    });
                }

                linesLayer.appendChild(poly);
            });
        }

        // Отвязать конец ЛЭП от узла ('start' | 'end').
        modifyLink(side) {
            const { selectedLineId, lines } = App.state;
            if (!selectedLineId) return;
            App.saveState();
            const line = lines.find((l) => l.id === selectedLineId);
            if (!line) return;
            if (side === 'start') line.startNodeId = null;
            if (side === 'end') line.endNodeId = null;
            App.render();
            App.propertyPanel.update();
        }

        // Применить ручной ввод координат X/Y к текущей активной ручке линии.
        manualMovePoint() {
            const { draggingHandle, lines } = App.state;
            if (!draggingHandle) return;
            App.saveState();
            const line = lines.find((l) => l.id === draggingHandle.lineId);
            if (!line) return;
            const pt = line.points[draggingHandle.index];
            pt.x = App.snap(parseFloat(document.getElementById('prop-pt-x').value) || pt.x);
            pt.y = App.snap(parseFloat(document.getElementById('prop-pt-y').value) || pt.y);
            App.canvas.cleanUpOrthogonal();
            App.render();
        }
    }

    App.lineManager = new LineManager();

    // Мутатор одного параметра ЛЭП из правой панели свойств
    window.updateLineParam = function (param, value) {
        const { selectedLineId, lines } = App.state;
        if (!selectedLineId) return;
        App.saveState();
        const l = lines.find((l) => l.id === selectedLineId);
        if (l) {
            l[param] = value;
            if (param === 'mark') l.name = value;
        }
        App.render();
    };

    window.modifyLink = (side) => App.lineManager.modifyLink(side);
    window.manualMovePoint = () => App.lineManager.manualMovePoint();
})();

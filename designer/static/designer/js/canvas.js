/**
 * canvas.js — работа с SVG-сценой: преобразования, геометрия, режимы.
 *
 * CanvasView отвечает за:
 *   * масштаб/сдвиг viewport (translate + scale)
 *   * геометрические утилиты (ортогональные сегменты, попадание в линию)
 *   * переключение режимов (SELECT / DRAW / TEXT)
 *   * контекстное меню и колесо мыши
 *
 * Сами обработчики mousedown/move/up живут в main.js — это «клей»,
 * связывающий все менеджеры вместе.
 */
(function () {
    'use strict';

    const App = window.App;

    class CanvasView {
        updateTransform() {
            const { viewX, viewY, scale } = App.state;
            App.dom.viewport.setAttribute(
                'transform',
                `translate(${viewX},${viewY}) scale(${scale})`
            );
        }

        // Возвращает выпрямленную в ортогональные сегменты копию пути.
        getOrthogonalSegments(points) {
            if (!points || points.length === 0) return [];

            const res = [{ ...points[0] }];
            for (let i = 1; i < points.length; i++) {
                const prev = res[res.length - 1];
                const curr = points[i];
                if (prev.x !== curr.x && prev.y !== curr.y) {
                    res.push({ x: curr.x, y: prev.y });
                }
                res.push({ ...curr });
            }

            // Удаляем промежуточные точки, лежащие на одной прямой
            const cleaned = [res[0]];
            for (let i = 1; i < res.length - 1; i++) {
                const prev = cleaned[cleaned.length - 1];
                const curr = res[i];
                const next = res[i + 1];
                const sameX = prev.x === curr.x && curr.x === next.x;
                const sameY = prev.y === curr.y && curr.y === next.y;
                if (sameX || sameY) continue;
                cleaned.push(curr);
            }
            const last = res[res.length - 1];
            const prevCl = cleaned[cleaned.length - 1];
            if (last && prevCl && (last.x !== prevCl.x || last.y !== prevCl.y)) {
                cleaned.push(last);
            }
            return cleaned;
        }

        // Пересчитывает все линии сцены в ортогональные сегменты.
        cleanUpOrthogonal() {
            App.state.lines.forEach((line) => {
                if (line.points && line.points.length >= 2) {
                    line.points = this.getOrthogonalSegments(line.points);
                }
            });
        }

        // Поиск линии под координатой (клик по ЛЭП).
        findLineAt(x, y) {
            return App.state.lines.find((l) => {
                const ortho = this.getOrthogonalSegments(l.points);
                for (let i = 0; i < ortho.length - 1; i++) {
                    if (this._distToSeg({ x, y }, ortho[i], ortho[i + 1]) < 10) {
                        return true;
                    }
                }
                return false;
            });
        }

        // Расстояние от точки до отрезка v–w.
        _distToSeg(p, v, w) {
            const l2 = Math.pow(v.x - w.x, 2) + Math.pow(v.y - w.y, 2);
            if (l2 === 0) return Math.hypot(p.x - v.x, p.y - v.y);
            const t = Math.max(
                0,
                Math.min(1, ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2)
            );
            return Math.hypot(
                p.x - (v.x + t * (w.x - v.x)),
                p.y - (v.y + t * (w.y - v.y))
            );
        }

        // Переключение режима редактора (SELECT / DRAW / TEXT).
        setMode(m) {
            App.state.mode = m;
            App.state.isDrawing = false;
            App.state.currentLinePoints = [];
            App.state.draggingHandle = null;
            App.state.selectedLineId = null;
            App.state.hoveredNodeId = null;
            if (m !== 'DRAW') App.state.pendingLineData = null;

            document.querySelectorAll('.tool-btn').forEach((b) => b.classList.remove('active'));
            const btn = document.getElementById('btn-' + m);
            if (btn) btn.classList.add('active');

            App.dom.previewLayer.innerHTML = '';
            App.render();
            App.propertyPanel.update();
        }

        // --- Синхронизация выделенных элементов --- //
        updateSelectedElements() {
            const sel = App.state.selectedElements;
            sel.nodeIds.clear();
            sel.lineIds.clear();
            App.state.selectedNodeIds.forEach((id) => sel.nodeIds.add(id));
            if (App.state.selectedLineId) sel.lineIds.add(App.state.selectedLineId);
        }

        // Какие линии выделены «полностью» — явно либо по обоим концам.
        getFullySelectedLines() {
            const sel = App.state.selectedElements;
            const out = [];
            App.state.lines.forEach((line) => {
                const explicit = sel.lineIds.has(line.id);
                const startSel = !line.startNodeId || sel.nodeIds.has(line.startNodeId);
                const endSel = !line.endNodeId || sel.nodeIds.has(line.endNodeId);
                if (explicit || (startSel && endSel)) out.push(line);
            });
            return out;
        }

        // Перемещение группы выделенных объектов на (dx, dy) относительно initial-снимка.
        moveSelectedGroup(deltaX, deltaY) {
            const { nodes, lines, initialNodes, initialLines, selectedElements } = App.state;
            const selLines = this.getFullySelectedLines();
            const selNodes = nodes.filter((n) => selectedElements.nodeIds.has(n.id));

            selNodes.forEach((node) => {
                const init = initialNodes.find((n) => n.id === node.id);
                if (!init) return;
                node.x = App.snap(init.x + deltaX);
                node.y = App.snap(init.y + deltaY);
            });

            selLines.forEach((line) => {
                const init = initialLines.find((l) => l.id === line.id);
                if (!init) return;
                line.points = init.points.map((p) => ({
                    x: App.snap(p.x + deltaX),
                    y: App.snap(p.y + deltaY),
                }));
                if (line.startNodeId && selectedElements.nodeIds.has(line.startNodeId)) {
                    const s = nodes.find((n) => n.id === line.startNodeId);
                    if (s && line.points[0]) {
                        line.points[0].x = s.x;
                        line.points[0].y = s.y;
                    }
                }
                if (line.endNodeId && selectedElements.nodeIds.has(line.endNodeId)) {
                    const e = nodes.find((n) => n.id === line.endNodeId);
                    if (e && line.points[line.points.length - 1]) {
                        line.points[line.points.length - 1].x = e.x;
                        line.points[line.points.length - 1].y = e.y;
                    }
                }
                line.points = this.getOrthogonalSegments(line.points);
            });
        }
    }

    App.canvas = new CanvasView();

    // Обратная совместимость: inline-обработчики могут вызывать window.setMode.
    window.setMode = (m) => App.canvas.setMode(m);
})();

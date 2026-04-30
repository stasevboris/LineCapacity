/**
 * main.js — точка входа редактора схем.
 *
 * Склеивает все менеджеры вместе:
 *   * заполняет App.dom ссылками на SVG-слои
 *   * вешает обработчики мыши/клавиатуры на сцену
 *   * предоставляет App.render() — единственная точка перерисовки
 *   * регистрирует глобальные функции для inline-обработчиков
 *   * инициализирует drag-and-drop и первый рендер
 */
(function () {
    'use strict';

    const App = window.App;

    // ---------------------- RENDER (единая точка) ---------------------- //
    App.render = function () {
        App.dom.nodesLayer.innerHTML = '';
        App.dom.linesLayer.innerHTML = '';
        App.dom.handlesLayer.innerHTML = '';
        App.lineManager.renderAll();
        App.nodeManager.renderAll();
    };

    // ---------------------- История (Undo) ---------------------- //
    App.undo = function () {
        const { history } = App.state;
        if (history.length === 0) return;
        const snapshot = JSON.parse(history.pop());
        App.state.nodes = snapshot.nodes;
        App.state.lines = snapshot.lines;
        App.state.selectedLineId = null;
        App.state.draggingHandle = null;
        App.state.hoveredNodeId = null;
        App.canvas.updateSelectedElements();
        App.render();
        App.propertyPanel.update();
    };

    // ---------------------- Загрузка/сохранение ---------------------- //
    App.loadTopologyData = function (data) {
        App.saveState();
        App.state.nodes = data.nodes || [];
        App.state.lines = data.lines || [];
        App.state.selectedNodeIds = [];
        App.state.selectedLineId = null;
        App.state.draggingHandle = null;
        App.canvas.updateSelectedElements();
        App.render();
        App.propertyPanel.update();
    };

    App.saveToServerWithParams = async function (name, folderId, organizationId) {
        try {
            const result = await App.api.saveScheme({
                name,
                folder_id: folderId,
                organization_id: organizationId,
                nodes: App.state.nodes,
                lines: App.state.lines,
            });
            if (result.status === 'success') {
                alert('Схема успешно сохранена в реестр!');
                if (window.loadDesignerRegistry) window.loadDesignerRegistry();
            } else {
                alert('Ошибка: ' + result.message);
            }
        } catch (e) {
            alert('Ошибка сети при сохранении.');
        }
    };

    App.saveToServer = function () {
        if (window.openSaveModal) {
            window.openSaveModal();
            return;
        }
        App.api
            .saveScheme({ nodes: App.state.nodes, lines: App.state.lines })
            .then((result) => {
                if (result.status === 'success') alert('Схема сохранена успешно!');
                else alert('Ошибка: ' + result.message);
            })
            .catch(() => alert('Ошибка сети при сохранении.'));
    };

    App.openLoadModal = async function () {
        const listCont = document.getElementById('revisions-list-inner');
        if (!listCont) return;
        listCont.innerHTML = '<p>Загрузка списка...</p>';
        document.getElementById('modal-overlay').style.display = 'flex';
        try {
            const result = await App.api.listRevisions();
            if (result.status !== 'success') return;
            listCont.innerHTML = '';
            if (result.revisions.length === 0) {
                listCont.innerHTML = '<p>Нет сохраненных версий.</p>';
                return;
            }
            result.revisions.forEach((rev) => {
                const date = new Date(rev.created_at).toLocaleString();
                const div = document.createElement('div');
                div.className = 'rev-item';
                div.innerHTML = `<span><strong>${rev.label}</strong></span> <small style="color:var(--text-sec)">${date}</small>`;
                div.onclick = async () => {
                    const r = await App.api.loadRevision(rev.id);
                    if (r.status === 'success') {
                        App.loadTopologyData(r.topology_data);
                        document.getElementById('modal-overlay').style.display = 'none';
                    }
                };
                listCont.appendChild(div);
            });
        } catch (e) {
            listCont.innerHTML = 'Ошибка загрузки списка.';
        }
    };

    App.deleteSelected = function () {
        App.saveState();
        const { selectedNodeIds, selectedLineId } = App.state;
        App.state.nodes = App.state.nodes.filter((n) => !selectedNodeIds.includes(n.id));
        App.state.lines = App.state.lines.filter(
            (l) =>
                l.id !== selectedLineId &&
                !selectedNodeIds.includes(l.startNodeId) &&
                !selectedNodeIds.includes(l.endNodeId)
        );
        App.state.selectedNodeIds = [];
        App.state.selectedLineId = null;
        App.state.draggingHandle = null;
        App.canvas.updateSelectedElements();
        if (App.dom.ctxMenu) App.dom.ctxMenu.style.display = 'none';
        App.dom.sidebarRight.style.display = 'none';
        App.render();
    };

    // ---------------------- Обработчики мыши на сцене ---------------------- //
    function installSceneHandlers() {
        const scene = App.dom.scene;
        const ctxMenu = App.dom.ctxMenu;
        const previewLayer = App.dom.previewLayer;
        const selectRect = App.dom.selectRect;

        scene.onmousedown = (e) => {
            if (ctxMenu) ctxMenu.style.display = 'none';
            const c = App.getCoords(e);
            const s = App.state;

            // Режим рисования линий
            if (s.mode === 'DRAW') {
                if (e.button === 2) {
                    s.pendingLineData = null;
                    App.canvas.setMode('SELECT');
                    scene.style.cursor = 'default';
                    s.isDrawing = false;
                    s.currentLinePoints = [];
                    previewLayer.innerHTML = '';
                    return;
                }
                const hitNode = s.nodes.find((n) => Math.hypot(n.x - c.x, n.y - c.y) < 25);

                if (!s.isDrawing && hitNode && hitNode.type !== 'TEXT') {
                    if (!App.nodeManager.canConnectToNode(hitNode.id)) {
                        alert(`Невозможно начать ЛЭП от "${hitNode.name}" (достигнут лимит подключений для опоры).`);
                        return;
                    }
                    App.saveState();
                    s.isDrawing = true;
                    s.startNodeId = hitNode.id;
                    s.currentLinePoints = [{ x: hitNode.x, y: hitNode.y }];
                } else if (s.isDrawing) {
                    s.currentLinePoints.push({ x: App.snap(c.x), y: App.snap(c.y) });
                    if (hitNode && hitNode.id !== s.startNodeId && hitNode.type !== 'TEXT') {
                        if (!App.nodeManager.canConnectToNode(hitNode.id)) {
                            alert(`Невозможно завершить ЛЭП на "${hitNode.name}" (достигнут лимит подключений для опоры).`);
                            return;
                        }
                        const p = s.pendingLineData;
                        const newLine = {
                            id: Date.now(),
                            name: p ? p.name : 'ЛЭП',
                            points: [...s.currentLinePoints],
                            startNodeId: s.startNodeId,
                            endNodeId: hitNode.id,
                            type: 'ЛЭП',
                            db_id: p ? p.db_id : null,
                            mark: p ? (p.params['Марка ЛЭП'] || p.name) : '',
                            material: p ? (p.params['Материал провода'] || '') : '',
                            insulation: p ? (p.params['Материал изоляции'] || '') : '',
                            cores_count: p ? (p.params['Количество жил'] || '') : '',
                            cross_section: p ? (p.params['Сечение фазного провода, мм²'] || '') : '',
                            r_phase_ohm_km: p ? (p.params['Сопротивление фазного, Ом/км'] || '') : '',
                            r_null_ohm_km: p ? (p.params['Сопротивление нулевого, Ом/км'] || '') : '',
                            r_add_ohm_km: p ? (p.params['Сопротивление доп. провода, Ом/км'] || '') : '',
                        };
                        s.lines.push(newLine);
                        App.canvas.cleanUpOrthogonal();
                        s.isDrawing = false;
                        s.startNodeId = null;
                        s.currentLinePoints = [];
                        s.pendingLineData = null;
                        App.canvas.setMode('SELECT');
                        scene.style.cursor = 'default';
                    }
                }
                App.render();
                App.propertyPanel.update();
                return;
            }

            // Размещение узла, выбранного из каталога
            if (s.nodeToPlace) {
                if (e.button === 2) {
                    s.nodeToPlace = null;
                    previewLayer.innerHTML = '';
                    scene.style.cursor = 'default';
                    return;
                }
                App.saveState();
                const nd = s.nodeToPlace;
                const newNode = {
                    id: Date.now(),
                    x: App.snap(c.x),
                    y: App.snap(c.y),
                    type: nd.type,
                    name: nd.name,
                    db_id: nd.db_id,
                    params: nd.params || {},
                };
                if (newNode.type === 'Опора' && newNode.params.branches_count === undefined) {
                    newNode.params.branches_count = 0;
                }
                s.nodes.push(newNode);
                s.nodeToPlace = null;
                scene.style.cursor = 'default';
                previewLayer.innerHTML = '';
                s.selectedNodeIds = [newNode.id];
                s.selectedLineId = null;
                App.canvas.updateSelectedElements();
                App.render();
                App.propertyPanel.update();
                return;
            }

            const hitNode = s.nodes.find((n) => Math.hypot(n.x - c.x, n.y - c.y) < 25);

            // Панорамирование правой/средней кнопкой
            if (e.button === 2 || e.button === 1) {
                s.isPanning = true;
                s.startX = e.clientX - s.viewX;
                s.startY = e.clientY - s.viewY;
                return;
            }

            // Ручка на выделенной линии?
            if (s.selectedLineId && s.mode === 'SELECT') {
                const line = s.lines.find((l) => l.id === s.selectedLineId);
                if (line) {
                    const hIdx = line.points.findIndex(
                        (p) => Math.hypot(p.x - c.x, p.y - c.y) < 15
                    );
                    if (hIdx !== -1) {
                        App.saveState();
                        s.draggingHandle = { lineId: s.selectedLineId, index: hIdx };
                        App.propertyPanel.update();
                        return;
                    }
                }
            }

            if (s.mode === 'SELECT') {
                if (hitNode) {
                    App.saveState();
                    s.selectedLineId = null;
                    s.draggingHandle = null;

                    if (!e.shiftKey) {
                        s.selectedNodeIds = [hitNode.id];
                    } else {
                        if (!s.selectedNodeIds.includes(hitNode.id)) {
                            s.selectedNodeIds.push(hitNode.id);
                        } else {
                            s.selectedNodeIds = s.selectedNodeIds.filter((id) => id !== hitNode.id);
                        }
                    }

                    App.canvas.updateSelectedElements();
                    s.isDragging = true;
                    s.initialNodes = s.nodes.map((n) => ({ ...n }));
                    s.initialLines = s.lines.map((l) => ({
                        ...l,
                        points: l.points.map((p) => ({ ...p })),
                    }));
                    s.startX = c.x;
                    s.startY = c.y;
                } else {
                    const hitLine = App.canvas.findLineAt(c.x, c.y);
                    if (hitLine) {
                        if (!e.shiftKey) {
                            s.selectedLineId = hitLine.id;
                            s.selectedNodeIds = [];
                        } else {
                            s.selectedLineId = s.selectedLineId === hitLine.id ? null : hitLine.id;
                        }
                        App.canvas.updateSelectedElements();

                        if (!e.shiftKey || s.selectedLineId) {
                            s.isDragging = true;
                            s.initialNodes = s.nodes.map((n) => ({ ...n }));
                            s.initialLines = s.lines.map((l) => ({
                                ...l,
                                points: l.points.map((p) => ({ ...p })),
                            }));
                            s.startX = c.x;
                            s.startY = c.y;
                        }
                    } else {
                        s.isSelecting = true;
                        if (!e.shiftKey) {
                            s.selectedNodeIds = [];
                            s.selectedLineId = null;
                            App.canvas.updateSelectedElements();
                        }
                        s.startX = c.x;
                        s.startY = c.y;
                        if (selectRect) selectRect.style.display = 'block';
                    }
                }
            } else if (s.mode === 'TEXT') {
                App.saveState();
                const textNode = {
                    id: Date.now(),
                    x: App.snap(c.x),
                    y: App.snap(c.y),
                    type: 'TEXT',
                    name: 'Ваш текст',
                    fontSize: 16,
                };
                s.nodes.push(textNode);
                s.selectedNodeIds = [textNode.id];
                App.canvas.updateSelectedElements();
                App.canvas.setMode('SELECT');
            }

            App.render();
            App.propertyPanel.update();
        };

        window.onmousemove = (e) => {
            const c = App.getCoords(e);
            const s = App.state;

            if (s.nodeToPlace) {
                previewLayer.innerHTML = `
                    <circle cx="${App.snap(c.x)}" cy="${App.snap(c.y)}" r="15"
                        fill="rgba(46,204,113,0.4)" stroke="#2ecc71" stroke-width="2" stroke-dasharray="4"/>
                    <text x="${App.snap(c.x)}" y="${App.snap(c.y) + 35}" fill="#fff"
                        font-size="11" text-anchor="middle">${s.nodeToPlace.name}</text>`;
                return;
            }

            if (s.mode === 'DRAW' && s.isDrawing) {
                const tempPts = [...s.currentLinePoints, { x: App.snap(c.x), y: App.snap(c.y) }];
                const ortho = App.canvas.getOrthogonalSegments(tempPts);
                previewLayer.innerHTML = `<polyline points="${ortho
                    .map((p) => `${p.x},${p.y}`)
                    .join(' ')}" class="drawing-line"/>`;
                return;
            }

            if (s.isPanning) {
                s.viewX = e.clientX - s.startX;
                s.viewY = e.clientY - s.startY;
                App.canvas.updateTransform();
                return;
            }

            if (s.draggingHandle) {
                const line = s.lines.find((l) => l.id === s.draggingHandle.lineId);
                if (!line) return;
                const pt = line.points[s.draggingHandle.index];
                pt.x = App.snap(c.x);
                pt.y = App.snap(c.y);
                s.hoveredNodeId = null;

                if (
                    s.draggingHandle.index === 0 ||
                    s.draggingHandle.index === line.points.length - 1
                ) {
                    const nearNode = s.nodes.find(
                        (n) => n.type !== 'TEXT' && Math.hypot(n.x - pt.x, n.y - pt.y) < 40
                    );
                    if (nearNode && App.nodeManager.canConnectToNode(nearNode.id, line.id)) {
                        pt.x = nearNode.x;
                        pt.y = nearNode.y;
                        s.hoveredNodeId = nearNode.id;
                    }
                }

                const xEl = document.getElementById('prop-pt-x');
                const yEl = document.getElementById('prop-pt-y');
                if (xEl && yEl) {
                    xEl.value = pt.x;
                    yEl.value = pt.y;
                }
                App.render();
                return;
            }

            if (s.isSelecting) {
                const x = Math.min(c.x, s.startX);
                const y = Math.min(c.y, s.startY);
                const w = Math.abs(c.x - s.startX);
                const h = Math.abs(c.y - s.startY);
                selectRect.setAttribute('x', x);
                selectRect.setAttribute('y', y);
                selectRect.setAttribute('width', w);
                selectRect.setAttribute('height', h);

                s.selectedNodeIds = s.nodes
                    .filter((n) => n.x >= x && n.x <= x + w && n.y >= y && n.y <= y + h)
                    .map((n) => n.id);
                s.selectedLineId = null;
                App.canvas.updateSelectedElements();
                App.render();
            }

            if (s.isDragging && !s.draggingHandle) {
                const dx = c.x - s.startX;
                const dy = c.y - s.startY;
                App.canvas.moveSelectedGroup(dx, dy);
                App.render();
            }
        };

        window.onmouseup = () => {
            const s = App.state;
            if (s.draggingHandle) {
                const line = s.lines.find((l) => l.id === s.draggingHandle.lineId);
                if (line) {
                    const pt = line.points[s.draggingHandle.index];
                    const nearNode = s.nodes.find(
                        (n) => n.type !== 'TEXT' && Math.hypot(n.x - pt.x, n.y - pt.y) < 40
                    );
                    if (nearNode && App.nodeManager.canConnectToNode(nearNode.id, line.id)) {
                        if (s.draggingHandle.index === 0) line.startNodeId = nearNode.id;
                        else if (s.draggingHandle.index === line.points.length - 1)
                            line.endNodeId = nearNode.id;
                    } else {
                        if (s.draggingHandle.index === 0) line.startNodeId = null;
                        else if (s.draggingHandle.index === line.points.length - 1)
                            line.endNodeId = null;
                    }
                }
            }
            s.isPanning = false;
            s.isSelecting = false;
            s.isDragging = false;
            s.draggingHandle = null;
            s.hoveredNodeId = null;
            if (selectRect) selectRect.style.display = 'none';
            App.canvas.cleanUpOrthogonal();
            App.render();
            App.propertyPanel.update();
        };

        scene.ondblclick = () => {
            const s = App.state;
            if (s.mode === 'DRAW' && s.isDrawing) {
                s.isDrawing = false;
                s.currentLinePoints = [];
                previewLayer.innerHTML = '';
                s.pendingLineData = null;
                App.canvas.setMode('SELECT');
            }
        };

        scene.onwheel = (e) => {
            e.preventDefault();
            App.state.scale *= e.deltaY > 0 ? 0.9 : 1.1;
            App.canvas.updateTransform();
        };

        scene.oncontextmenu = (e) => {
            e.preventDefault();
            if (App.state.selectedNodeIds.length > 0 || App.state.selectedLineId) {
                ctxMenu.style.display = 'block';
                ctxMenu.style.left = e.clientX + 'px';
                ctxMenu.style.top = e.clientY + 'px';
            }
        };
    }

    // ---------------------- Глобальные клавиши ---------------------- //
    function installKeyboardHandlers() {
        window.addEventListener('keydown', (e) => {
            const s = App.state;
            if (e.code === 'Escape') {
                if (s.nodeToPlace) {
                    s.nodeToPlace = null;
                    App.dom.previewLayer.innerHTML = '';
                    App.dom.scene.style.cursor = 'default';
                }
                if (s.pendingLineData) {
                    s.pendingLineData = null;
                    if (s.mode === 'DRAW') App.canvas.setMode('SELECT');
                    s.isDrawing = false;
                    s.currentLinePoints = [];
                    App.dom.previewLayer.innerHTML = '';
                    App.dom.scene.style.cursor = 'default';
                }
                return;
            }
            if (e.ctrlKey && e.code === 'KeyZ') {
                e.preventDefault();
                App.undo();
            }
            if (e.code === 'Delete') App.deleteSelected();
        });
    }

    // ---------------------- Инициализация ---------------------- //
    function cacheDom() {
        App.dom.scene = document.getElementById('scene');
        App.dom.viewport = document.getElementById('viewport');
        App.dom.nodesLayer = document.getElementById('nodes-layer');
        App.dom.linesLayer = document.getElementById('lines-layer');
        App.dom.handlesLayer = document.getElementById('handles-layer');
        App.dom.previewLayer = document.getElementById('preview-layer');
        App.dom.selectRect = document.getElementById('selection-rect');
        App.dom.ctxMenu = document.getElementById('context-menu');
        App.dom.sidebarRight = document.getElementById('sidebar-right');
    }

    function exportGlobals() {
        window.saveToServer = App.saveToServer;
        window.saveToServerWithParams = App.saveToServerWithParams;
        window.loadTopologyData = App.loadTopologyData;
        window.openLoadModal = App.openLoadModal;
        window.undo = App.undo;
        window.deleteSelected = App.deleteSelected;
    }

    document.addEventListener('DOMContentLoaded', () => {
        cacheDom();
        exportGlobals();
        installSceneHandlers();
        installKeyboardHandlers();
        App.canvas.updateTransform();
        App.nodeManager.initDragAndDrop();
        App.render();
        App.propertyPanel.update();
    });
})();

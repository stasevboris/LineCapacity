// ==========================================
// ИНИЦИАЛИЗАЦИЯ И ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
// ==========================================

const scene = document.getElementById('scene');
const viewport = document.getElementById('viewport');
const nodesLayer = document.getElementById('nodes-layer');
const linesLayer = document.getElementById('lines-layer');
const handlesLayer = document.getElementById('handles-layer');
const previewLayer = document.getElementById('preview-layer');
const selectRect = document.getElementById('selection-rect');
const ctxMenu = document.getElementById('context-menu');
const sidebarRight = document.getElementById('sidebar-right');

const GRID = 50;
let scale = 1;
let viewX = 0;
let viewY = 0;
let mode = 'SELECT';

let nodes = [];
let lines = [];
let selectedNodeIds = [];
let selectedLineId = null;
let history = [];

let isDrawing = false;
let currentLinePoints = [];
let startNodeId = null;
let pendingLineData = null; // Данные ЛЭП из каталога

let isPanning = false;
let isDragging = false;
let isSelecting = false;
let startX, startY;
let initialNodes = [];

let draggingHandle = null;
let hoveredNodeId = null;

// ПЕРЕМЕННАЯ ДЛЯ ЭЛЕМЕНТА ИЗ КАТАЛОГА
window.nodeToPlace = null;

// Функция привязки к сетке
const snap = v => Math.round(v / GRID) * GRID;

// Получение координат мыши с учетом зума и панорамирования
const getCoords = e => {
    const r = scene.getBoundingClientRect();
    return {
        x: (e.clientX - r.left - viewX) / scale,
        y: (e.clientY - r.top - viewY) / scale
    };
};

// ==========================================
// API ЛОГИКА (Сохранение и Загрузка)
// ==========================================

async function saveToServer() {
    const payload = { nodes, lines };
    try {
        const response = await fetch('/api/save/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (result.status === 'success') {
            alert('Схема сохранена успешно!');
        } else {
            alert('Ошибка: ' + result.message);
        }
    } catch (e) {
        alert('Ошибка сети при сохранении.');
    }
}

async function openLoadModal() {
    const listCont = document.getElementById('revisions-list');
    listCont.innerHTML = '<p style="color:var(--text-sec)">Загрузка списка...</p>';
    document.getElementById('modal-overlay').style.display = 'flex';

    try {
        const response = await fetch('/api/list/');
        const result = await response.json();
        if (result.status === 'success') {
            listCont.innerHTML = '';
            if (result.revisions.length === 0) {
                listCont.innerHTML = '<p>Нет сохраненных версий.</p>';
                return;
            }
            result.revisions.forEach(rev => {
                const date = new Date(rev.created_at).toLocaleString();
                const div = document.createElement('div');
                div.className = 'rev-item';
                div.innerHTML = `<span><strong>${rev.label}</strong></span><small style="color:var(--text-sec)">${date}</small>`;
                div.onclick = () => loadSpecificVersion(rev.id);
                listCont.appendChild(div);
            });
        }
    } catch (e) {
        listCont.innerHTML = 'Ошибка загрузки списка.';
    }
}

async function loadSpecificVersion(id) {
    try {
        const response = await fetch(`/api/load/${id}/`);
        const result = await response.json();
        if (result.status === 'success') {
            saveState();
            nodes = result.topology_data.nodes || [];
            lines = result.topology_data.lines || [];
            selectedNodeIds = [];
            selectedLineId = null;
            render();
            closeModal();
        }
    } catch (e) {
        alert('Ошибка при загрузке данных.');
    }
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

// ==========================================
// ЛОГИКА КАТАЛОГА
// ==========================================

window.currentCatalogCategory = '';
window.currentCatalogPage = 1;

window.openCatalogModal = function(category, title) {
    window.currentCatalogCategory = category;
    window.currentCatalogPage = 1;
    document.getElementById('catalog-title').innerText = `Каталог: ${title}`;
    document.getElementById('catalog-search').value = '';
    document.getElementById('catalog-modal').style.display = 'flex';
    window.fetchCatalogData();
};

window.closeCatalogModal = function() {
    document.getElementById('catalog-modal').style.display = 'none';
};

window.performCatalogSearch = function() {
    window.currentCatalogPage = 1;
    window.fetchCatalogData();
};

window.changeCatalogPage = function(delta) {
    window.currentCatalogPage += delta;
    window.fetchCatalogData();
};

window.fetchCatalogData = function() {
    const tbody = document.getElementById('catalog-table-body');
    const search = document.getElementById('catalog-search').value;

    tbody.innerHTML = '\\<td colspan="2" style="text-align:center; padding: 40px; color: #888;">Загрузка данных...\\';

    fetch(`/get_catalog_nodes/?category=${window.currentCatalogCategory}&page=${window.currentCatalogPage}&search=${encodeURIComponent(search)}`)
        .then(res => res.json())
        .then(data => {
            tbody.innerHTML = '';
            if (!data.items || data.items.length === 0) {
                tbody.innerHTML = '\\<td colspan="2" style="text-align:center; padding: 40px; color: #888;">По вашему запросу ничего не найдено.\\';
                return;
            }

            data.items.forEach(item => {
                const tr = document.createElement('tr');
                const itemName = item.name || 'Без названия';
                tr.innerHTML = `
                    <td style="font-weight: 500;">${itemName} ${item.power ? `(${item.power} кВА)` : ''}${item.type === 'ЛЭП' && item.cross_section ? ` (${item.cross_section} мм²)` : ''}</td>
                    <td style="text-align: center;">
                        <button class="btn-select-item" onclick="window.selectItemFromCatalog(${item.id}, '${itemName.replace(/'/g, "\\'")}', '${item.type}', '${item.power}')">
                            Выбрать
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById('cat-page-info').innerText = `Страница ${data.current_page} из ${data.total_pages}`;
            document.getElementById('btn-cat-prev').disabled = data.current_page <= 1;
            document.getElementById('btn-cat-next').disabled = data.current_page >= data.total_pages;
        })
        .catch(err => {
            console.error(err);
            tbody.innerHTML = '\\<td colspan="2" style="text-align:center; color:#ff5252; padding: 40px;">Ошибка соединения с сервером базы данных.\\';
        });
};

window.selectItemFromCatalog = function(id, name, type, power) {
    window.closeCatalogModal();

    // Для ЛЭП - активируем режим рисования
    if (type === 'ЛЭП') {
        fetch(`/api/get_node_details/?db_id=${id}&type=ЛЭП`)
            .then(res => res.json())
            .then(data => {
                pendingLineData = {
                    db_id: id,
                    name: name,
                    type: type,
                    params: data.details || {}
                };
                setMode('DRAW');
                document.getElementById('scene').style.cursor = 'crosshair';
            });
        return;
    }

    // Для ТП и Абонента - загружаем параметры и создаем узел
    fetch(`/api/get_node_details/?db_id=${id}&type=${type}`)
        .then(res => res.json())
        .then(data => {
            const nodeData = {
                db_id: id,
                name: name,
                type: type,
                power: power,
                params: data.details || {}
            };

            window.nodeToPlace = nodeData;
            document.getElementById('scene').style.cursor = 'crosshair';

            const updatePreview = (e) => {
                const c = getCoords(e);
                previewLayer.innerHTML = `
                    <circle cx="${snap(c.x)}" cy="${snap(c.y)}" r="15" fill="rgba(46,204,113,0.4)" stroke="#2ecc71" stroke-width="2" stroke-dasharray="4"/>
                    <text x="${snap(c.x)}" y="${snap(c.y) + 35}" fill="#fff" font-size="11" text-anchor="middle">${name}</text>
                `;
            };

            const moveHandler = (e) => updatePreview(e);
            const clickHandler = () => {
                document.removeEventListener('mousemove', moveHandler);
                document.removeEventListener('click', clickHandler);
                previewLayer.innerHTML = '';
            };

            document.addEventListener('mousemove', moveHandler);
            document.addEventListener('click', clickHandler);
        });
};

// ==========================================
// ГЛОБАЛЬНЫЕ КЛАВИШИ (ОТМЕНА И УДАЛЕНИЕ)
// ==========================================

window.addEventListener('keydown', e => {
    if (e.code === 'Escape') {
        if (window.nodeToPlace) {
            window.nodeToPlace = null;
            previewLayer.innerHTML = '';
            document.getElementById('scene').style.cursor = 'default';
        }
        if (pendingLineData) {
            pendingLineData = null;
            if (mode === 'DRAW') setMode('SELECT');
            isDrawing = false;
            currentLinePoints = [];
            previewLayer.innerHTML = '';
            document.getElementById('scene').style.cursor = 'default';
        }
        return;
    }
    if (e.ctrlKey && e.code === 'KeyZ') {
        e.preventDefault();
        window.undo();
    }
    if (e.code === 'Delete') {
        window.deleteSelected();
    }
});

// ==========================================
// ОРИГИНАЛЬНАЯ ЛОГИКА РЕДАКТОРА ХОЛСТА
// ==========================================

function getOrthogonalSegments(points) {
    if (!points || points.length === 0) return [];
    let res = [{...points[0]}];
    for (let i = 1; i < points.length; i++) {
        let prev = res[res.length - 1];
        let curr = points[i];
        if (prev.x !== curr.x && prev.y !== curr.y) {
            res.push({x: curr.x, y: prev.y});
        }
        res.push({...curr});
    }

    let cleaned = [res[0]];
    for (let i = 1; i < res.length - 1; i++) {
        let prev = cleaned[cleaned.length - 1];
        let curr = res[i];
        let next = res[i + 1];
        if ((prev.x === curr.x && curr.x === next.x) || (prev.y === curr.y && curr.y === next.y)) {
            continue;
        }
        cleaned.push(curr);
    }

    let last = res[res.length - 1];
    let prevCl = cleaned[cleaned.length - 1];
    if (last && prevCl && (last.x !== prevCl.x || last.y !== prevCl.y)) {
        cleaned.push(last);
    }
    return cleaned;
}

function saveState() {
    history.push(JSON.stringify({ nodes, lines }));
    if (history.length > 30) history.shift();
}

window.undo = function() {
    if (history.length > 0) {
        const state = JSON.parse(history.pop());
        nodes = state.nodes;
        lines = state.lines;
        selectedLineId = null;
        draggingHandle = null;
        hoveredNodeId = null;
        render();
        updateSidebar();
    }
}

window.setMode = function(m) {
    mode = m;
    isDrawing = false;
    currentLinePoints = [];
    draggingHandle = null;
    selectedLineId = null;
    hoveredNodeId = null;

    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));

    if (m !== 'PLACE') {
        const btn = document.getElementById('btn-' + m);
        if (btn) btn.classList.add('active');
        window.nodeToPlace = null;
        document.getElementById('scene').style.cursor = 'default';
    } else {
        document.getElementById('scene').style.cursor = 'crosshair';
    }

    previewLayer.innerHTML = '';
    render();
    updateSidebar();
}

window.modifyLink = function(side) {
    if (!selectedLineId) return;
    saveState();
    const line = lines.find(l => l.id === selectedLineId);
    if (side === 'start') line.startNodeId = null;
    if (side === 'end') line.endNodeId = null;
    render();
    updateSidebar();
}

window.manualMovePoint = function() {
    if (!draggingHandle) return;
    saveState();
    const line = lines.find(l => l.id === draggingHandle.lineId);
    const pt = line.points[draggingHandle.index];

    pt.x = snap(parseFloat(document.getElementById('prop-pt-x').value) || pt.x);
    pt.y = snap(parseFloat(document.getElementById('prop-pt-y').value) || pt.y);

    cleanUpOrthogonal();
    render();
}

function cleanUpOrthogonal() {
    lines.forEach(line => {
        if (line.points && line.points.length >= 2) {
            line.points = getOrthogonalSegments(line.points);
        }
    });
}

// ==========================================
// ОБНОВЛЕНИЕ ПАРАМЕТРОВ (РЕДАКТИРУЕМЫЕ ПОЛЯ)
// ==========================================

window.updateNodeName = function(value) {
    if (selectedNodeIds.length !== 1) return;
    saveState();
    const node = nodes.find(n => n.id === selectedNodeIds[0]);
    if (node) node.name = value;
    render();
};

window.updateNodeParam = function(param, value) {
    if (selectedNodeIds.length !== 1) return;
    saveState();
    const node = nodes.find(n => n.id === selectedNodeIds[0]);
    if (node) {
        if (!node.params) node.params = {};
        node.params[param] = value;
        render();
    }
};

window.updateLineParam = function(param, value) {
    if (!selectedLineId) return;
    saveState();
    const line = lines.find(l => l.id === selectedLineId);
    if (line) {
        line[param] = value;
        if (param === 'mark') line.name = value;
        render();
    }
};

window.updateLineName = function(value) {
    if (!selectedLineId) return;
    saveState();
    const line = lines.find(l => l.id === selectedLineId);
    if (line) line.name = value;
    render();
};

window.updateTextSize = function(v) {
    saveState();
    if (selectedNodeIds.length === 1) {
        const n = nodes.find(node => node.id === selectedNodeIds[0]);
        if (n && n.type === 'TEXT') {
            n.fontSize = parseInt(v) || 16;
            render();
        }
    }
}

window.updateLineType = function(v) {
    saveState();
    if (selectedLineId) {
        lines.find(l => l.id === selectedLineId).type = v;
    }
}

// Проверка лимита подключений к опоре
function checkPoleConnections(poleId) {
    const pole = nodes.find(n => n.id === poleId && n.type === 'Опора');
    if (!pole) return true;

    const maxBranches = pole.params?.branches_count || 0;
    const connectedLines = lines.filter(l => l.startNodeId === poleId || l.endNodeId === poleId);

    if (connectedLines.length > maxBranches) {
        alert(`Опора "${pole.name}" может иметь не более ${maxBranches} подключений!`);
        return false;
    }
    return true;
}

// Обновление информации о подключениях в панели свойств
function updateConnectionsInfo(poleId) {
    const pole = nodes.find(n => n.id === poleId);
    if (!pole || pole.type !== 'Опора') return;

    const maxBranches = pole.params?.branches_count || 0;
    const connectedLines = lines.filter(l => l.startNodeId === poleId || l.endNodeId === poleId);
    const connectionsList = document.getElementById('connections-list');

    if (connectionsList) {
        if (connectedLines.length === 0) {
            connectionsList.innerHTML = '<span style="color: #888;">Нет подключений</span>';
        } else {
            connectionsList.innerHTML = `<span style="color: ${connectedLines.length > maxBranches ? '#ff5252' : '#2ecc71'}">
                Подключено: ${connectedLines.length} / ${maxBranches}
            </span>`;

            if (connectedLines.length > maxBranches) {
                connectionsList.innerHTML += '<div style="color: #ff5252; margin-top: 5px;">⚠️ Превышен лимит подключений!</div>';
            }
        }
    }
}

// ==========================================
// СОБЫТИЯ МЫШИ НА ХОЛСТЕ
// ==========================================

scene.onmousedown = (e) => {
    ctxMenu.style.display = 'none';
    const c = getCoords(e);

    // Режим рисования ЛЭП
    if (mode === 'DRAW') {
        if (e.button === 2) {
            pendingLineData = null;
            setMode('SELECT');
            document.getElementById('scene').style.cursor = 'default';
            isDrawing = false;
            currentLinePoints = [];
            previewLayer.innerHTML = '';
            return;
        }

        const hitNode = nodes.find(n => Math.hypot(n.x - c.x, n.y - c.y) < 25);

        if (!isDrawing && hitNode && hitNode.type !== 'TEXT') {
            saveState();
            isDrawing = true;
            startNodeId = hitNode.id;
            currentLinePoints = [{ x: hitNode.x, y: hitNode.y }];
        } else if (isDrawing) {
            currentLinePoints.push({ x: snap(c.x), y: snap(c.y) });
            if (hitNode && hitNode.id !== startNodeId && hitNode.type !== 'TEXT') {
                // Проверка лимита подключений для опор
                const startPole = nodes.find(n => n.id === startNodeId && n.type === 'Опора');
                const endPole = nodes.find(n => n.id === hitNode.id && n.type === 'Опора');

                if (startPole) {
                    const startConnections = lines.filter(l => l.startNodeId === startNodeId || l.endNodeId === startNodeId).length;
                    const maxStart = startPole.params?.branches_count || 0;
                    if (startConnections >= maxStart) {
                        alert(`Опора "${startPole.name}" достигла лимита подключений (${maxStart})!`);
                        isDrawing = false;
                        startNodeId = null;
                        currentLinePoints = [];
                        previewLayer.innerHTML = '';
                        return;
                    }
                }

                if (endPole) {
                    const endConnections = lines.filter(l => l.startNodeId === hitNode.id || l.endNodeId === hitNode.id).length;
                    const maxEnd = endPole.params?.branches_count || 0;
                    if (endConnections >= maxEnd) {
                        alert(`Опора "${endPole.name}" достигла лимита подключений (${maxEnd})!`);
                        isDrawing = false;
                        startNodeId = null;
                        currentLinePoints = [];
                        previewLayer.innerHTML = '';
                        return;
                    }
                }

                lines.push({
                    id: Date.now(),
                    name: pendingLineData ? pendingLineData.name : "ЛЭП #" + (lines.length+1),
                    points: [...currentLinePoints],
                    startNodeId,
                    endNodeId: hitNode.id,
                    type: 'ЛЭП',
                    db_id: pendingLineData ? pendingLineData.db_id : null,
                    mark: pendingLineData ? (pendingLineData.params['Марка ЛЭП'] || pendingLineData.name) : '',
                    material: pendingLineData ? (pendingLineData.params['Материал провода'] || '') : '',
                    insulation: pendingLineData ? (pendingLineData.params['Материал изоляции'] || '') : '',
                    cores_count: pendingLineData ? (pendingLineData.params['Количество жил'] || '') : '',
                    cross_section: pendingLineData ? (pendingLineData.params['Сечение фазного провода, мм²'] || '') : '',
                    r_phase_ohm_km: pendingLineData ? (pendingLineData.params['Сопротивление фазного, Ом/км'] || '') : '',
                    r_null_ohm_km: pendingLineData ? (pendingLineData.params['Сопротивление нулевого, Ом/км'] || '') : '',
                    r_add_ohm_km: pendingLineData ? (pendingLineData.params['Сопротивление доп. провода, Ом/км'] || '') : ''
                });
                cleanUpOrthogonal();
                isDrawing = false;
                startNodeId = null;
                currentLinePoints = [];
                pendingLineData = null;
                setMode('SELECT');
                document.getElementById('scene').style.cursor = 'default';
            }
        }
        render();
        updateSidebar();
        return;
    }

    // Размещение узла из каталога (PLACE режим)
    if (mode === 'PLACE' && window.nodeToPlace) {
        if (e.button === 2) {
            window.nodeToPlace = null;
            setMode('SELECT');
            return;
        }

        saveState();

        const newNode = {
            id: Date.now(),
            x: snap(c.x),
            y: snap(c.y),
            ...window.nodeToPlace
        };

        nodes.push(newNode);
        window.nodeToPlace = null;
        setMode('SELECT');

        selectedNodeIds = [newNode.id];
        selectedLineId = null;

        render();
        updateSidebar();
        return;
    }

    const hitNode = nodes.find(n => Math.hypot(n.x - c.x, n.y - c.y) < 25);

    if (e.button === 2 || e.button === 1) {
        isPanning = true;
        startX = e.clientX - viewX;
        startY = e.clientY - viewY;
        return;
    }

    if (selectedLineId && mode === 'SELECT') {
        const line = lines.find(l => l.id === selectedLineId);
        const hIdx = line.points.findIndex(p => Math.hypot(p.x - c.x, p.y - c.y) < 15);
        if (hIdx !== -1) {
            saveState();
            draggingHandle = { lineId: selectedLineId, index: hIdx };
            updateSidebar();
            return;
        }
    }

    if (mode === 'SELECT') {
        if (hitNode) {
            saveState();
            selectedLineId = null;
            draggingHandle = null;

            if (!selectedNodeIds.includes(hitNode.id)) {
                selectedNodeIds = e.shiftKey ? [...selectedNodeIds, hitNode.id] : [hitNode.id];
            }

            isDragging = true;
            initialNodes = nodes.map(n => ({...n}));
            startX = c.x;
            startY = c.y;
        } else {
            const hitLine = findLineAt(c.x, c.y);
            if (hitLine) {
                selectedLineId = hitLine.id;
                selectedNodeIds = [];
                draggingHandle = null;
            } else {
                isSelecting = true;
                selectedNodeIds = [];
                selectedLineId = null;
                draggingHandle = null;
                startX = c.x;
                startY = c.y;
                selectRect.style.display = 'block';
            }
        }
    }
    else if (mode === 'TEXT') {
        saveState();
        const textNode = {
            id: Date.now(),
            x: snap(c.x),
            y: snap(c.y),
            type: 'TEXT',
            name: 'Ваш текст',
            fontSize: 16
        };
        nodes.push(textNode);
        selectedNodeIds = [textNode.id];
        setMode('SELECT');
    }

    render();
    updateSidebar();
};

window.onmousemove = (e) => {
    const c = getCoords(e);

    if (mode === 'PLACE' && window.nodeToPlace) {
        while (previewLayer.firstChild) {
            previewLayer.removeChild(previewLayer.firstChild);
        }
        const cx = snap(c.x);
        const cy = snap(c.y);
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute('cx', cx);
        circle.setAttribute('cy', cy);
        circle.setAttribute('r', 15);
        circle.setAttribute('fill', 'rgba(46, 204, 113, 0.4)');
        circle.setAttribute('stroke', '#2ecc71');
        circle.setAttribute('stroke-width', '2');
        circle.setAttribute('stroke-dasharray', '4');
        circle.style.pointerEvents = 'none';

        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute('x', cx);
        text.setAttribute('y', cy + 35);
        text.setAttribute('fill', '#fff');
        text.setAttribute('font-size', '11');
        text.setAttribute('text-anchor', 'middle');
        text.style.pointerEvents = 'none';
        text.textContent = window.nodeToPlace.name;

        previewLayer.appendChild(circle);
        previewLayer.appendChild(text);
        return;
    }

    if (mode === 'DRAW' && isDrawing) {
        const tempPts = [...currentLinePoints, {x: snap(c.x), y: snap(c.y)}];
        const orthoPts = getOrthogonalSegments(tempPts);
        previewLayer.innerHTML = `<polyline points="${orthoPts.map(p=>`${p.x},${p.y}`).join(' ')}" class="drawing-line" />`;
        return;
    }

    if (isPanning) {
        viewX = e.clientX - startX;
        viewY = e.clientY - startY;
        updateTransform();
        return;
    }

    if (draggingHandle) {
        const line = lines.find(l => l.id === draggingHandle.lineId);
        const pt = line.points[draggingHandle.index];

        pt.x = snap(c.x);
        pt.y = snap(c.y);

        hoveredNodeId = null;
        if (draggingHandle.index === 0 || draggingHandle.index === line.points.length - 1) {
            const nearNode = nodes.find(n => n.type !== 'TEXT' && Math.hypot(n.x - pt.x, n.y - pt.y) < 40);
            if (nearNode) {
                pt.x = nearNode.x;
                pt.y = nearNode.y;
                hoveredNodeId = nearNode.id;
            }
        }

        if(document.getElementById('prop-pt-x')){
            document.getElementById('prop-pt-x').value = pt.x;
            document.getElementById('prop-pt-y').value = pt.y;
        }
        render();
        return;
    }

    if (isSelecting) {
        const x = Math.min(c.x, startX);
        const y = Math.min(c.y, startY);
        const w = Math.abs(c.x - startX);
        const h = Math.abs(c.y - startY);

        selectRect.setAttribute('x', x);
        selectRect.setAttribute('y', y);
        selectRect.setAttribute('width', w);
        selectRect.setAttribute('height', h);

        selectedNodeIds = nodes.filter(n => n.x >= x && n.x <= x+w && n.y >= y && n.y <= y+h).map(n => n.id);
        render();
    }

    if (isDragging) {
        const dx = c.x - startX;
        const dy = c.y - startY;

        nodes.forEach(n => {
            if (selectedNodeIds.includes(n.id)) {
                const old = initialNodes.find(i => i.id === n.id);
                n.x = snap(old.x + dx);
                n.y = snap(old.y + dy);
            }
        });

        lines.forEach(l => {
            if (selectedNodeIds.includes(l.startNodeId)) {
                const sn = nodes.find(n => n.id === l.startNodeId);
                if (sn && l.points[0]) { l.points[0].x = sn.x; l.points[0].y = sn.y; }
            }
            if (selectedNodeIds.includes(l.endNodeId)) {
                const en = nodes.find(n => n.id === l.endNodeId);
                if (en && l.points[l.points.length-1]) { l.points[l.points.length-1].x = en.x; l.points[l.points.length-1].y = en.y; }
            }
        });
        render();
    }
};

window.onmouseup = () => {
    if (draggingHandle) {
        const line = lines.find(l => l.id === draggingHandle.lineId);
        if (line && line.points) {
            const pt = line.points[draggingHandle.index];
            if (pt) {
                const nearNode = nodes.find(n => n.type !== 'TEXT' && Math.hypot(n.x - pt.x, n.y - pt.y) < 40);
                if (draggingHandle.index === 0) {
                    line.startNodeId = nearNode ? nearNode.id : null;
                } else if (draggingHandle.index === line.points.length - 1) {
                    line.endNodeId = nearNode ? nearNode.id : null;
                }
            }
        }
    }

    isPanning = false;
    isSelecting = false;
    isDragging = false;
    draggingHandle = null;
    hoveredNodeId = null;
    if(selectRect) selectRect.style.display = 'none';

    cleanUpOrthogonal();
    render();
    updateSidebar();
};

scene.ondblclick = () => {
    if (mode === 'DRAW' && isDrawing) {
        isDrawing = false;
        currentLinePoints = [];
        previewLayer.innerHTML = '';
        pendingLineData = null;
        setMode('SELECT');
    }
};

// ==========================================
// ОТРИСОВКА (RENDER)
// ==========================================

function render() {
    nodesLayer.innerHTML = '';
    linesLayer.innerHTML = '';
    handlesLayer.innerHTML = '';

    lines.forEach(line => {
        const sn = nodes.find(n => n.id === line.startNodeId);
        const en = nodes.find(n => n.id === line.endNodeId);

        if (sn) { line.points[0].x = sn.x; line.points[0].y = sn.y; }
        if (en) { line.points[line.points.length-1].x = en.x; line.points[line.points.length-1].y = en.y; }

        const orthoPts = getOrthogonalSegments(line.points);
        const poly = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        poly.setAttribute('points', orthoPts.map(p => `${p.x},${p.y}`).join(' '));
        poly.classList.add('line-path');

        // Добавляем подпись для ЛЭП (марка)
        if (line.mark || line.name) {
            const midIndex = Math.floor(orthoPts.length / 2);
            const midPoint = orthoPts[midIndex];
            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
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
                const h = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                h.setAttribute('cx', p.x);
                h.setAttribute('cy', p.y);
                h.setAttribute('r', 6);
                h.classList.add('line-handle');
                if (draggingHandle && draggingHandle.lineId === line.id && draggingHandle.index === idx) {
                    h.classList.add('active');
                }
                handlesLayer.appendChild(h);
            });
        }
        linesLayer.appendChild(poly);
    });

    nodes.forEach(n => {
        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

        if (n.type === 'TEXT') {
            const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
            t.setAttribute('x', n.x);
            t.setAttribute('y', n.y);
            t.textContent = n.name;
            t.classList.add('text-node');
            t.style.fontSize = (n.fontSize || 16) + 'px';
            if (selectedNodeIds.includes(n.id)) {
                t.classList.add('selected');
            }
            g.appendChild(t);
            nodesLayer.appendChild(g);
            return;
        }

        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute('cx', n.x);
        c.setAttribute('cy', n.y);
        c.setAttribute('r', 15);
        c.classList.add('node');

        if (selectedNodeIds.includes(n.id)) {
            c.classList.add('selected');
        }
        if (hoveredNodeId === n.id) {
            c.classList.add('can-attach');
        }

        const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
        t.setAttribute('x', n.x);
        t.setAttribute('y', n.y + 35);
        t.textContent = n.name;
        t.classList.add('node-label');

        g.appendChild(c);
        g.appendChild(t);
        nodesLayer.appendChild(g);
    });
}

function findLineAt(x, y) {
    return lines.find(l => {
        const orthoPts = getOrthogonalSegments(l.points);
        for(let i=0; i < orthoPts.length-1; i++) {
            if (distToSeg({x, y}, orthoPts[i], orthoPts[i+1]) < 10) return true;
        }
        return false;
    });
}

function distToSeg(p, v, w) {
    const l2 = Math.pow(v.x - w.x, 2) + Math.pow(v.y - w.y, 2);
    if(l2 === 0) return Math.hypot(p.x - v.x, p.y - v.y);
    let t = Math.max(0, Math.min(1, ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2));
    return Math.hypot(p.x - (v.x + t * (w.x - v.x)), p.y - (v.y + t * (w.y - v.y)));
}

// ==========================================
// ПРАВАЯ ПАНЕЛЬ СВОЙСТВ (С ЗАПОЛНЕНИЕМ ПАРАМЕТРОВ)
// ==========================================

function updateSidebar() {
    sidebarRight.style.display = 'none';

    // Прячем все под-блоки
    if(document.getElementById('transformer-props')) document.getElementById('transformer-props').style.display = 'none';
    if(document.getElementById('consumer-props')) document.getElementById('consumer-props').style.display = 'none';
    if(document.getElementById('pole-props')) document.getElementById('pole-props').style.display = 'none';
    if(document.getElementById('line-props')) document.getElementById('line-props').style.display = 'none';
    if(document.getElementById('text-props')) document.getElementById('text-props').style.display = 'none';
    if(document.getElementById('point-editor')) document.getElementById('point-editor').style.display = 'none';

    if (selectedNodeIds.length === 1) {
        const n = nodes.find(node => node.id === selectedNodeIds[0]);
        if (n) {
            sidebarRight.style.display = 'block';
            document.getElementById('props-title').innerText = "Свойства объекта";
            document.getElementById('lbl-name').innerText = "Имя на схеме";
            document.getElementById('prop-name').value = n.name || '';

            // Для Трансформатора
            if (n.type === 'ТП') {
                const propsDiv = document.getElementById('transformer-props');
                if (propsDiv) propsDiv.style.display = 'block';
                document.getElementById('trans-type-name').value = n.name || '';
                document.getElementById('trans-db-id').value = n.db_id || '';
                document.getElementById('trans-nominal-power').value = n.params?.nominal_power || '';
                document.getElementById('trans-losses-xx').value = n.params?.losses_no_load || '';
                document.getElementById('trans-losses-kz').value = n.params?.losses_short_circuit || '';
                document.getElementById('trans-voltage-hv').value = n.params?.voltage_hv || '';
                document.getElementById('trans-voltage-lv').value = n.params?.voltage_lv || '';
                document.getElementById('trans-voltage-kz').value = n.params?.voltage_short_circuit_pct || '';
                document.getElementById('trans-pbv-stages').value = n.params?.pbv_stages_count || '';
                document.getElementById('trans-pbv-step').value = n.params?.pbv_step_pct || '';
            }
            // Для Потребителя
            else if (n.type === 'Абонент') {
                const propsDiv = document.getElementById('consumer-props');
                if (propsDiv) propsDiv.style.display = 'block';
                document.getElementById('consumer-type-name').value = n.name || '';
                document.getElementById('consumer-db-id').value = n.db_id || '';
                document.getElementById('consumer-usage').value = n.params?.usage_character || '';
                document.getElementById('consumer-address').value = n.params?.address || '';
                document.getElementById('consumer-extra').value = n.params?.additional_data || '';
                document.getElementById('consumer-supply').value = n.params?.supply_type || '';
                document.getElementById('consumer-phase').value = n.params?.phase_number || '';
                document.getElementById('consumer-calc-method').value = n.params?.calc_method || '';
                document.getElementById('consumer-yearly').value = n.params?.yearly_consumption_kwh || '';
                document.getElementById('consumer-power').value = n.params?.calculated_active_power_kw || '';
                document.getElementById('consumer-cosphi').value = n.params?.cos_phi || '';
            }
            // Для Опоры
            else if (n.type === 'Опора') {
                const propsDiv = document.getElementById('pole-props');
                if (propsDiv) propsDiv.style.display = 'block';
                document.getElementById('pole-branches').value = n.params?.branches_count || 0;
                updateConnectionsInfo(n.id);
            }
            // Для Текста
            else if (n.type === 'TEXT') {
                const propsDiv = document.getElementById('text-props');
                if (propsDiv) propsDiv.style.display = 'block';
                document.getElementById('prop-text-size').value = n.fontSize || 16;
            }
        }
    }
    else if (selectedLineId) {
        const l = lines.find(line => line.id === selectedLineId);
        if (l) {
            sidebarRight.style.display = 'block';
            if(document.getElementById('line-props')) document.getElementById('line-props').style.display = 'block';
            document.getElementById('props-title').innerText = "ЛЭП";
            document.getElementById('lbl-name').innerText = "Наименование";
            document.getElementById('prop-name').value = l.name || '';
            document.getElementById('prop-mark').value = l.mark || '';
            document.getElementById('prop-material').value = l.material || '';
            document.getElementById('prop-insulation').value = l.insulation || '';
            document.getElementById('prop-cores').value = l.cores_count || '';
            document.getElementById('prop-cross-section').value = l.cross_section || '';
            document.getElementById('prop-r-phase').value = l.r_phase_ohm_km || '';
            document.getElementById('prop-r-null').value = l.r_null_ohm_km || '';
            document.getElementById('prop-r-add').value = l.r_add_ohm_km || '';

            if (draggingHandle && draggingHandle.lineId === selectedLineId) {
                document.getElementById('point-editor').style.display = 'block';
                document.getElementById('prop-pt-x').value = l.points[draggingHandle.index].x;
                document.getElementById('prop-pt-y').value = l.points[draggingHandle.index].y;
            }

            if (document.getElementById('btn-unlink-start')) {
                document.getElementById('btn-unlink-start').disabled = !l.startNodeId;
                document.getElementById('btn-unlink-end').disabled = !l.endNodeId;
            }
        }
    }
}

window.updateElementName = function(v) {
    saveState();
    if (selectedNodeIds.length === 1) {
        nodes.find(n => n.id === selectedNodeIds[0]).name = v;
    } else if (selectedLineId) {
        lines.find(l => l.id === selectedLineId).name = v;
    }
    render();
}

window.deleteSelected = function() {
    saveState();
    nodes = nodes.filter(n => !selectedNodeIds.includes(n.id));
    lines = lines.filter(l => l.id !== selectedLineId && !selectedNodeIds.includes(l.startNodeId) && !selectedNodeIds.includes(l.endNodeId));
    selectedNodeIds = [];
    selectedLineId = null;
    draggingHandle = null;
    ctxMenu.style.display = 'none';
    sidebarRight.style.display = 'none';
    render();
}

// ==========================================
// DRAG & DROP (Опора)
// ==========================================

const canvasCont = document.getElementById('canvas-container');
canvasCont.ondragover = e => e.preventDefault();

canvasCont.ondrop = e => {
    const rawData = e.dataTransfer.getData('app/node-data');
    if (!rawData) return;

    const nodeData = JSON.parse(rawData);
    saveState();

    const c = getCoords(e);
    const newNode = {
        id: Date.now(),
        x: snap(c.x),
        y: snap(c.y),
        type: nodeData.type,
        name: nodeData.name,
        db_id: null,
        params: {}
    };

    // Для опоры добавляем branches_count по умолчанию
    if (nodeData.type === 'Опора') {
        newNode.params.branches_count = 0;
    }

    nodes.push(newNode);
    render();
};

window.initDragAndDrop = function() {
    document.querySelectorAll('.lib-item').forEach(i => {
        i.ondragstart = e => {
            let cleanName = i.innerText.replace('🗼 ', '').trim();
            const dataToTransfer = {
                type: i.dataset.type,
                name: cleanName
            };
            e.dataTransfer.setData('app/node-data', JSON.stringify(dataToTransfer));
        };
    });
}

// ==========================================
// ЗУМ И ТРАНСФОРМАЦИЯ
// ==========================================

scene.onwheel = e => {
    e.preventDefault();
    scale *= (e.deltaY > 0 ? 0.9 : 1.1);
    updateTransform();
};

function updateTransform() {
    viewport.setAttribute('transform', `translate(${viewX},${viewY}) scale(${scale})`);
    const smallGrid = document.getElementById('smallGridPath');

    if (scale > 1.2) {
        let opacity = Math.min((scale - 1.2) * 2, 0.6);
        if(smallGrid) smallGrid.setAttribute('stroke-opacity', opacity.toString());
    } else {
        if(smallGrid) smallGrid.setAttribute('stroke-opacity', '0');
    }
}

scene.oncontextmenu = e => {
    e.preventDefault();
    if (selectedNodeIds.length > 0 || selectedLineId) {
        ctxMenu.style.display = 'block';
        ctxMenu.style.left = e.clientX + 'px';
        ctxMenu.style.top = e.clientY + 'px';
    }
};

// ==========================================
// ЭКСПОРТ ФУНКЦИЙ
// ==========================================

window.saveToServer = saveToServer;
window.openLoadModal = openLoadModal;
window.undo = undo;
window.setMode = setMode;
window.modifyLink = modifyLink;
window.manualMovePoint = manualMovePoint;
window.updateElementName = updateElementName;
window.updateTextSize = updateTextSize;
window.updateLineType = updateLineType;
window.deleteSelected = deleteSelected;
window.openCatalogModal = openCatalogModal;
window.closeCatalogModal = closeCatalogModal;
window.performCatalogSearch = performCatalogSearch;
window.changeCatalogPage = changeCatalogPage;
window.fetchCatalogData = fetchCatalogData;
window.selectItemFromCatalog = selectItemFromCatalog;
window.updateNodeName = updateNodeName;
window.updateNodeParam = updateNodeParam;
window.updateLineParam = updateLineParam;
window.updateLineName = updateLineName;

updateTransform();
document.addEventListener('DOMContentLoaded', window.initDragAndDrop);
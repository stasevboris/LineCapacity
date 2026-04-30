/**
 * properties.js — правая панель свойств.
 *
 * PropertyPanel.update() — основной метод, вызывается после любого изменения
 * выделения или состояния. Показывает/прячет соответствующие блоки,
 * подтягивает динамические свойства из БД, если их нет локально.
 */
(function () {
    'use strict';

    const App = window.App;

    class PropertyPanel {
        // Главный вход — определяет что показывать.
        update() {
            const sidebar = App.dom.sidebarRight;
            sidebar.style.display = 'none';

            const blocks = ['text-props', 'pole-props', 'line-props', 'transformer-props', 'consumer-props'];
            blocks.forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            const dynContainer = document.getElementById('dynamic-props-container');
            if (dynContainer) dynContainer.innerHTML = '';

            const { selectedNodeIds, selectedLineId, nodes, lines, draggingHandle } = App.state;

            if (selectedNodeIds.length === 1) {
                const n = nodes.find((node) => node.id === selectedNodeIds[0]);
                if (!n) return;
                sidebar.style.display = 'block';
                this._renderNode(n, dynContainer);
                return;
            }

            if (selectedLineId) {
                const l = lines.find((line) => line.id === selectedLineId);
                if (!l) return;
                sidebar.style.display = 'block';
                this._renderLine(l, draggingHandle);
            }
        }

        // -------------------- Подблоки -------------------- //
        _renderNode(n, dynContainer) {
            document.getElementById('props-title').innerText = `Свойства: ${n.type || 'объект'}`;
            document.getElementById('lbl-name').innerText = 'Наименование';
            document.getElementById('prop-name').value = n.name || '';

            if (n.type === 'TEXT') {
                document.getElementById('text-props').style.display = 'block';
                document.getElementById('props-title').innerText = 'Текст';
                document.getElementById('lbl-name').innerText = 'Содержимое';
                document.getElementById('prop-text-size').value = n.fontSize || 16;
                return;
            }

            if (n.type === 'Опора') {
                document.getElementById('pole-props').style.display = 'block';
                document.getElementById('props-title').innerText = 'Свойства опоры';
                document.getElementById('pole-branches').value = n.params?.branches_count || 0;
                this._updateConnectionsInfo(n.id);
                return;
            }

            const hasLocalParams =
                n.params && Object.keys(n.params).filter((k) => k !== 'branches_count').length > 0;

            if (hasLocalParams || !n.db_id) {
                this._renderDynamicProps(n, dynContainer);
                return;
            }

            // Параметров нет — подтягиваем из БД и кешируем в n.params
            dynContainer.innerHTML =
                '<div style="color:#888;font-size:12px;padding:10px;">Загрузка свойств из БД...</div>';
            const selectedAtFetch = n.id;
            App.api
                .getNodeDetails(n.db_id, n.type)
                .then((data) => {
                    if (data.details && Object.keys(data.details).length > 0) {
                        n.params = { ...(n.params || {}), ...data.details };
                    }
                    if (
                        App.state.selectedNodeIds.length === 1 &&
                        App.state.selectedNodeIds[0] === selectedAtFetch
                    ) {
                        this._renderDynamicProps(n, dynContainer);
                    }
                })
                .catch(() => {
                    if (
                        App.state.selectedNodeIds.length === 1 &&
                        App.state.selectedNodeIds[0] === selectedAtFetch
                    ) {
                        dynContainer.innerHTML =
                            '<div style="color:#ff5252;">Ошибка связи с БД</div>';
                    }
                });
        }

        _renderLine(l, draggingHandle) {
            document.getElementById('line-props').style.display = 'block';
            document.getElementById('props-title').innerText = 'Свойства ЛЭП';
            document.getElementById('lbl-name').innerText = 'Наименование';
            document.getElementById('prop-name').value = l.name || '';

            const fields = [
                ['prop-mark', 'mark'],
                ['prop-material', 'material'],
                ['prop-insulation', 'insulation'],
                ['prop-cores', 'cores_count'],
                ['prop-cross-section', 'cross_section'],
                ['prop-r-phase', 'r_phase_ohm_km'],
                ['prop-r-null', 'r_null_ohm_km'],
                ['prop-r-add', 'r_add_ohm_km'],
            ];
            fields.forEach(([id, key]) => {
                const el = document.getElementById(id);
                if (el) el.value = l[key] || '';
            });

            if (draggingHandle && draggingHandle.lineId === l.id) {
                document.getElementById('point-editor').style.display = 'block';
                document.getElementById('prop-pt-x').value = l.points[draggingHandle.index].x;
                document.getElementById('prop-pt-y').value = l.points[draggingHandle.index].y;
            } else {
                const pe = document.getElementById('point-editor');
                if (pe) pe.style.display = 'none';
            }

            const btnStart = document.getElementById('btn-unlink-start');
            const btnEnd = document.getElementById('btn-unlink-end');
            if (btnStart) btnStart.disabled = !l.startNodeId;
            if (btnEnd) btnEnd.disabled = !l.endNodeId;
        }

        _renderDynamicProps(n, container) {
            if (!container) return;
            let html = `
                <div class="prop-group">
                    <label>Тип объекта</label>
                    <input type="text" value="${App.escapeHtml(n.type || 'Неизвестно')}" readonly
                        style="color: var(--text-sec); background: #242424; cursor: default;">
                </div>`;
            if (n.db_id) {
                html += `
                    <div class="prop-group">
                        <label>ID в Базе Данных</label>
                        <input type="text" value="${App.escapeHtml(n.db_id)}" readonly
                            style="color: var(--text-sec); font-family: monospace; background: #242424; cursor: default;">
                    </div>`;
            }
            if (n.params && Object.keys(n.params).length > 0) {
                for (const [key, value] of Object.entries(n.params)) {
                    if (value === null || value === undefined || value === '') continue;
                    html += `
                        <div class="prop-group">
                            <label>${App.escapeHtml(key)}</label>
                            <input type="text" value="${App.escapeHtml(value)}" readonly
                                style="color: var(--text-sec); background: #242424; font-weight: bold; font-size: 12px; cursor: default;">
                        </div>`;
                }
            } else if (!n.db_id) {
                html += `<div style="color:#888;font-size:11px;padding:10px;">Объект не привязан к справочнику</div>`;
            }
            container.innerHTML = html;
        }

        _updateConnectionsInfo(poleId) {
            const pole = App.state.nodes.find((n) => n.id === poleId && n.type === 'Опора');
            if (!pole) return;
            const maxBranches = pole.params?.branches_count || 0;
            const connectedLines = App.state.lines.filter(
                (l) => l.startNodeId === poleId || l.endNodeId === poleId
            );
            const listEl = document.getElementById('connections-list');
            if (!listEl) return;

            if (connectedLines.length === 0) {
                listEl.innerHTML = '<span style="color:#888;">Нет подключений</span>';
                return;
            }
            const color = connectedLines.length > maxBranches ? '#ff5252' : '#2ecc71';
            listEl.innerHTML = `<span style="color:${color}">Подключено: ${connectedLines.length} / ${maxBranches}</span>`;
            if (connectedLines.length > maxBranches) {
                listEl.innerHTML +=
                    '<div style="color:#ff5252;margin-top:5px;">⚠️ Превышен лимит подключений!</div>';
            }
        }
    }

    App.propertyPanel = new PropertyPanel();
})();

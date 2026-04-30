/**
 * catalog.js — модальное окно выбора объекта из справочника.
 *
 * CatalogModal открывается из index.html кнопками «Каталог ТП/ЛЭП/Абонент».
 * Экспортирует в window глобальные функции, которые использует шаблон
 * catalog_modal.html (inline onclick).
 */
(function () {
    'use strict';

    const App = window.App;

    class CatalogModal {
        open(category, title) {
            App.state.currentCatalogCategory = category;
            App.state.currentCatalogPage = 1;
            document.getElementById('catalog-title').innerText = `Каталог: ${title}`;
            document.getElementById('catalog-search').value = '';
            document
                .getElementById('catalog-modal')
                .style.setProperty('display', 'flex', 'important');
            this.fetch();
        }

        close() {
            document
                .getElementById('catalog-modal')
                .style.setProperty('display', 'none', 'important');
        }

        search() {
            App.state.currentCatalogPage = 1;
            this.fetch();
        }

        changePage(delta) {
            App.state.currentCatalogPage += delta;
            this.fetch();
        }

        fetch() {
            const tbody = document.getElementById('catalog-table-body');
            const search = document.getElementById('catalog-search').value;
            tbody.innerHTML =
                '<tr><td colspan="2" style="text-align:center;padding:40px;color:#888;">Загрузка данных...</td></tr>';

            App.api
                .getCatalog(App.state.currentCatalogCategory, App.state.currentCatalogPage, search)
                .then((data) => {
                    tbody.innerHTML = '';
                    if (!data.items || data.items.length === 0) {
                        tbody.innerHTML =
                            '<tr><td colspan="2" style="text-align:center;padding:40px;color:#888;">По вашему запросу ничего не найдено.</td></tr>';
                        return;
                    }
                    data.items.forEach((item) => {
                        const tr = document.createElement('tr');
                        const itemName = item.name || 'Без названия';
                        const safeName = itemName.replace(/'/g, "\\'");
                        const power = item.power || '';
                        tr.innerHTML = `
                            <td style="font-weight:500;">${App.escapeHtml(itemName)}${power ? ` (${App.escapeHtml(power)} кВА)` : ''}</td>
                            <td style="text-align:center;">
                                <button class="btn-select-item"
                                    onclick="window.selectItemFromCatalog(${item.id}, '${safeName}', '${item.type}', '${power}')">
                                    Выбрать
                                </button>
                            </td>`;
                        tbody.appendChild(tr);
                    });
                    document.getElementById('cat-page-info').innerText =
                        `Страница ${data.current_page} из ${data.total_pages}`;
                    document.getElementById('btn-cat-prev').disabled = data.current_page <= 1;
                    document.getElementById('btn-cat-next').disabled =
                        data.current_page >= data.total_pages;
                })
                .catch((err) => {
                    console.error(err);
                    tbody.innerHTML =
                        '<tr><td colspan="2" style="text-align:center;color:#ff5252;padding:40px;">Ошибка соединения с сервером.</td></tr>';
                });
        }

        selectItem(id, name, type, power) {
            this.close();

            if (type === 'ЛЭП') {
                App.api.getNodeDetails(id, 'ЛЭП').then((data) => {
                    App.state.pendingLineData = {
                        db_id: id,
                        name,
                        type,
                        params: data.details || {},
                    };
                    App.canvas.setMode('DRAW');
                    App.dom.scene.style.cursor = 'crosshair';
                });
                return;
            }

            App.api.getNodeDetails(id, type).then((data) => {
                App.state.nodeToPlace = {
                    db_id: id,
                    name,
                    type,
                    power,
                    params: data.details || {},
                };
                App.dom.scene.style.cursor = 'crosshair';
            });
        }
    }

    App.catalog = new CatalogModal();

    // ---- Глобальные функции для inline-обработчиков в шаблоне ---- //
    window.openCatalogModal = (cat, title) => App.catalog.open(cat, title);
    window.closeCatalogModal = () => App.catalog.close();
    window.performCatalogSearch = () => App.catalog.search();
    window.changeCatalogPage = (d) => App.catalog.changePage(d);
    window.fetchCatalogData = () => App.catalog.fetch();
    window.selectItemFromCatalog = (id, name, type, power) =>
        App.catalog.selectItem(id, name, type, power);
})();

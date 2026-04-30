/**
 * api.js — единая точка общения с бэкендом.
 *
 * ApiClient — тонкий класс-обёртка над fetch, возвращает Promise<json>.
 * Вместо разбросанных по коду fetch('/api/save/', ...) теперь:
 *     App.api.saveScheme(payload)
 *     App.api.getCatalog('ЛЭП', 1, 'АС-35')
 *     App.api.getNodeDetails(42, 'ТП')
 */
(function () {
    'use strict';

    class ApiClient {
        async _json(url, options = {}) {
            const opts = { headers: { 'Content-Type': 'application/json' }, ...options };
            const res = await fetch(url, opts);
            return res.json();
        }

        // ----- Схемы ----- //
        saveScheme(payload) {
            return this._json('/api/save/', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
        }

        listRevisions() {
            return this._json('/api/list/');
        }

        loadRevision(revId) {
            return this._json(`/api/load/${revId}/`);
        }

        loadSchemeById(schemeId) {
            return this._json(`/api/load_scheme_by_id/${schemeId}/`);
        }

        // ----- Каталог / справочники ----- //
        getCatalog(category, page = 1, search = '') {
            const params = new URLSearchParams({
                category,
                page: String(page),
                search,
            });
            return this._json(`/get_catalog_nodes/?${params.toString()}`);
        }

        getNodeDetails(dbId, type) {
            const params = new URLSearchParams({ db_id: dbId, type });
            return this._json(`/api/get_node_details/?${params.toString()}`);
        }

        // ----- Реестр ----- //
        getRegistry() {
            return this._json('/api/registry/');
        }
    }

    window.App = window.App || {};
    window.App.api = new ApiClient();
})();

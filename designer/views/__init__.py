"""
Пакет представлений (views) приложения designer.

Файл views.py исторически содержал всю серверную логику одним листом (1146 строк
с дублями функций). Здесь мы разносим её на доменные модули:

    base                — общие хелперы и декораторы прав
    pages               — HTML-страницы (editor, admin_panel, logout)
    schemes             — сохранение/загрузка схем, реестр папок
    catalog             — справочники для модального каталога в редакторе
    admin_transformers  — CRUD справочника трансформаторов
    admin_lines         — CRUD справочника ЛЭП
    admin_consumers     — CRUD справочника потребителей
    admin_organizations — CRUD организаций
    admin_users         — CRUD пользователей (+ создание организаций)

urls.py импортирует всё как `from . import views`, поэтому здесь мы
реэкспортируем все нужные имена, чтобы старые маршруты продолжили работать.
"""

from .pages import (
    editor_view,
    admin_panel_view,
    logout_view,
    login_view,
)
from .schemes import (
    save_scheme_api,
    list_revisions_api,
    load_scheme_api,
    load_scheme_by_id_api,
    api_get_registry,
    api_create_folder,
    api_edit_folder,
    api_delete_folder,
    api_delete_scheme,
)
from .catalog import (
    get_catalog_nodes,
    get_node_details,
)
from .admin_transformers import (
    api_transformers_list,
    api_transformer_create,
    api_transformer_update,
    api_transformer_delete,
)
from .admin_lines import (
    api_lines_list,
    api_line_create,
    api_line_update,
    api_line_delete,
)
from .admin_consumers import (
    api_consumers_list,
    api_consumer_create,
    api_consumer_update,
    api_consumer_delete,
)
from .admin_organizations import (
    api_organizations_list,
    api_organization_update,
    api_organization_delete,
    api_create_organization,
)
from .admin_users import (
    api_users_list,
    api_user_update,
    api_user_delete,
    api_create_user,
    api_permissions_list,
)

__all__ = [
    'editor_view', 'admin_panel_view', 'logout_view', 'login_view',
    'save_scheme_api', 'list_revisions_api', 'load_scheme_api',
    'load_scheme_by_id_api', 'api_get_registry', 'api_create_folder',
    'api_edit_folder', 'api_delete_folder', 'api_delete_scheme',
    'get_catalog_nodes', 'get_node_details',
    'api_transformers_list', 'api_transformer_create',
    'api_transformer_update', 'api_transformer_delete',
    'api_lines_list', 'api_line_create', 'api_line_update', 'api_line_delete',
    'api_consumers_list', 'api_consumer_create',
    'api_consumer_update', 'api_consumer_delete',
    'api_organizations_list', 'api_organization_update',
    'api_organization_delete', 'api_create_organization',
    'api_users_list', 'api_user_update', 'api_user_delete', 'api_create_user',
    'api_permissions_list',
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.editor_view, name='editor'),
    path('api/save/', views.save_scheme_api, name='save_scheme_api'),
    path('api/list/', views.list_revisions_api, name='list_revisions_api'),
    path('api/load/<int:rev_id>/', views.load_scheme_api, name='load_scheme_api'),
    path('api/load_scheme_by_id/<int:scheme_id>/', views.load_scheme_by_id_api, name='load_scheme_by_id_api'),
    path('get_catalog_nodes/', views.get_catalog_nodes, name='get_catalog_nodes'),
    path('api/get_node_details/', views.get_node_details, name='get_node_details'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('api/admin/create_org/', views.api_create_organization, name='api_create_org'),
    path('api/admin/create_user/', views.api_create_user, name='api_create_user'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),

    # ==========================================
    # НОВЫЕ API ДЛЯ УПРАВЛЕНИЯ СПРАВОЧНИКАМИ
    # ==========================================
    path('api/admin/transformers/', views.api_transformers_list, name='api_transformers_list'),
    path('api/admin/transformers/create/', views.api_transformer_create, name='api_transformer_create'),
    path('api/admin/transformers/<int:obj_id>/', views.api_transformer_update, name='api_transformer_update'),
    path('api/admin/transformers/<int:obj_id>/delete/', views.api_transformer_delete, name='api_transformer_delete'),

    path('api/admin/lines/', views.api_lines_list, name='api_lines_list'),
    path('api/admin/lines/create/', views.api_line_create, name='api_line_create'),
    path('api/admin/lines/<int:obj_id>/', views.api_line_update, name='api_line_update'),
    path('api/admin/lines/<int:obj_id>/delete/', views.api_line_delete, name='api_line_delete'),

    path('api/admin/consumers/', views.api_consumers_list, name='api_consumers_list'),
    path('api/admin/consumers/create/', views.api_consumer_create, name='api_consumer_create'),
    path('api/admin/consumers/<int:obj_id>/', views.api_consumer_update, name='api_consumer_update'),
    path('api/admin/consumers/<int:obj_id>/delete/', views.api_consumer_delete, name='api_consumer_delete'),

    path('api/admin/organizations/', views.api_organizations_list, name='api_organizations_list'),
    path('api/admin/organizations/<int:obj_id>/', views.api_organization_update, name='api_organization_update'),
    path('api/admin/organizations/<int:obj_id>/delete/', views.api_organization_delete, name='api_organization_delete'),

    path('api/admin/users/', views.api_users_list, name='api_users_list'),
    path('api/admin/users/<int:obj_id>/', views.api_user_update, name='api_user_update'),
    path('api/admin/users/<int:obj_id>/delete/', views.api_user_delete, name='api_user_delete'),
    path('api/admin/permissions/', views.api_permissions_list, name='api_permissions_list'),

    # ==========================================
    # РЕЕСТР И СХЕМЫ
    # ==========================================
    path('api/registry/', views.api_get_registry, name='api_get_registry'),
    path('api/admin/folders/create/', views.api_create_folder, name='api_create_folder'),
    path('api/admin/folders/<int:folder_id>/', views.api_edit_folder, name='api_edit_folder'),
    path('api/admin/folders/<int:folder_id>/delete/', views.api_delete_folder, name='api_delete_folder'),

    # НОВЫЙ МАРШРУТ ДЛЯ УДАЛЕНИЯ СХЕМ
    path('api/admin/schemes/<int:scheme_id>/delete/', views.api_delete_scheme, name='api_delete_scheme'),
]
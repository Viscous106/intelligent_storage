"""
URL Configuration for Smart Upload System
"""

from django.urls import path
from . import smart_upload_views as views
from . import advanced_json_views as adv_views

urlpatterns = [
    # Authentication endpoints
    path('auth/login', views.admin_login, name='admin_login'),
    path('auth/create', views.admin_create, name='admin_create'),
    path('auth/logout', views.admin_logout, name='admin_logout'),

    # JSON upload and analysis
    path('upload/json', views.upload_json, name='upload_json'),
    path('upload/json/file', views.upload_json_file, name='upload_json_file'),
    path('analyze/json', views.analyze_json, name='analyze_json'),

    # Media upload
    path('upload/media', views.upload_media, name='upload_media'),

    # Retrieval endpoints
    path('retrieve/json/<str:doc_id>', views.retrieve_json, name='retrieve_json'),
    path('retrieve/json/<str:doc_id>/range', views.retrieve_json_range, name='retrieve_json_range'),
    path('retrieve/media/<str:file_id>', views.retrieve_media, name='retrieve_media'),

    # List endpoints
    path('list/json', views.list_json_documents, name='list_json'),
    path('list/media', views.list_media_files, name='list_media'),

    # Delete endpoints
    path('delete/json/<str:doc_id>', views.delete_json, name='delete_json'),
    path('delete/media/<str:file_id>', views.delete_media, name='delete_media'),

    # Statistics
    path('stats', views.get_statistics, name='statistics'),

    # Schema information
    path('schema', views.get_document_schema, name='get_schema'),

    # Advanced JSON Query Endpoints (NEW)
    path('query/json', adv_views.advanced_query_json, name='advanced_query_json'),
    path('search/json', adv_views.search_json, name='search_json'),
    path('aggregate/json', adv_views.aggregate_json, name='aggregate_json'),
]

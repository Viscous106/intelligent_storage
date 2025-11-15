"""
URL Configuration for storage app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'media-files', views.MediaFileViewSet, basename='mediafile')
router.register(r'json-stores', views.JSONDataViewSet, basename='jsonstore')
router.register(r'file-search-stores', views.FileSearchStoreViewSet, basename='filesearchstore')

# URL patterns
urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),

    # File upload endpoints
    path('upload/file/', views.FileUploadView.as_view(), name='file-upload'),
    path('upload/batch/', views.BatchFileUploadView.as_view(), name='batch-upload'),

    # JSON data upload
    path('upload/json/', views.JSONDataUploadView.as_view(), name='json-upload'),

    # Health check
    path('health/', views.health_check, name='health-check'),

    # RAG (Semantic Search) endpoints
    path('rag/index/<int:file_id>/', views.index_document, name='index-document'),
    path('rag/search/', views.semantic_search, name='semantic-search'),
    path('rag/query/', views.rag_query, name='rag-query'),
    path('rag/reindex-all/', views.reindex_all, name='reindex-all'),
    path('rag/stats/', views.rag_stats, name='rag-stats'),

    # Gemini-style File Search Store endpoints
    path('file-search/index/', views.index_file_to_store, name='file-search-index'),
    path('file-search/search/', views.semantic_search_with_filters, name='file-search-search'),

    # Smart Upload System - Intelligent SQL/NoSQL routing with admin auth
    path('smart/', include('storage.smart_urls')),

    # File Manager - Web-based file explorer for smart folders
    path('filemanager/', include('storage.file_manager_urls')),
]

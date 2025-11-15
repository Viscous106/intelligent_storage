"""
URL configuration for File Browser with Advanced Features
"""

from django.urls import path
from . import file_browser_views
from . import fuzzy_search_views
from . import search_suggestion_views

app_name = 'file_browser'

urlpatterns = [
    # Web views
    path('browse/', file_browser_views.FileBrowserView.as_view(), name='browse'),

    # File Browser API endpoints
    path('api/browse/', file_browser_views.file_browser_api, name='browse_api'),
    path('api/stats/', file_browser_views.folder_stats_api, name='stats_api'),
    path('api/download/<int:file_id>/', file_browser_views.download_file, name='download'),
    path('api/preview/<int:file_id>/', file_browser_views.preview_file, name='preview'),

    # Trash bin operations
    path('api/delete/<int:file_id>/', file_browser_views.delete_file, name='delete'),
    path('api/permanent-delete/<int:file_id>/', file_browser_views.permanent_delete_file, name='permanent_delete'),
    path('api/restore/<int:file_id>/', file_browser_views.restore_file, name='restore'),

    # Fuzzy Search API endpoints
    path('api/search/fuzzy/', fuzzy_search_views.fuzzy_search, name='fuzzy_search'),
    path('api/search/initialize/', fuzzy_search_views.initialize_search_index, name='initialize_search'),
    path('api/search/index/<int:file_id>/', fuzzy_search_views.index_single_file, name='index_file'),
    path('api/search/stats/', fuzzy_search_views.get_search_stats, name='search_stats'),
    path('api/search/record/<int:file_id>/', fuzzy_search_views.record_file_interaction, name='record_interaction'),

    # Search Suggestions API endpoints
    path('api/suggestions/', search_suggestion_views.get_search_suggestions, name='search_suggestions'),
    path('api/suggestions/record/', search_suggestion_views.record_search_query, name='record_search'),
    path('api/suggestions/click/', search_suggestion_views.record_search_click, name='record_click'),
    path('api/suggestions/analytics/', search_suggestion_views.get_search_analytics, name='search_analytics'),
    path('api/suggestions/trending/', search_suggestion_views.get_trending_searches, name='trending_searches'),
    path('api/suggestions/clear/', search_suggestion_views.clear_search_history, name='clear_history'),
]

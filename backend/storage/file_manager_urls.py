"""
File Manager URL Configuration
"""

from django.urls import path
from . import file_manager_views
from . import fuzzy_search_views
from . import file_preview_views
from . import search_suggestion_views

urlpatterns = [
    # Web Interface
    path('', file_manager_views.file_manager_ui, name='file_manager_ui'),

    # Browse folders
    path('folders/', file_manager_views.browse_folders, name='browse_folders'),

    # List files in category
    path('category/<str:category>/', file_manager_views.list_files_in_category, name='list_category_files'),

    # Search
    path('search/', file_manager_views.search_files, name='search_files'),

    # File operations
    path('file/<path:file_path>/', file_manager_views.get_file_info, name='get_file_info'),
    path('download/<path:file_path>/', file_manager_views.download_file, name='download_file'),
    path('thumbnail/<path:file_path>/', file_manager_views.get_thumbnail, name='get_thumbnail'),
    path('delete/<path:file_path>/', file_manager_views.delete_file, name='delete_file'),

    # Preview operations
    path('preview/<path:file_path>/', file_preview_views.get_file_preview, name='file_preview'),
    path('preview/content/<path:file_path>/', file_preview_views.get_file_content, name='preview_content'),

    # Batch operations
    path('batch/delete/', file_manager_views.batch_delete_files, name='batch_delete'),
    path('batch/download/', file_manager_views.batch_download_files, name='batch_download'),

    # Statistics
    path('stats/', file_manager_views.get_storage_stats, name='storage_stats'),

    # Trie-based Fuzzy Search API
    path('fuzzy-search/', fuzzy_search_views.fuzzy_search, name='fuzzy_search'),
    path('fuzzy-search/init/', fuzzy_search_views.initialize_search_index, name='init_search_index'),
    path('fuzzy-search/index/<int:file_id>/', fuzzy_search_views.index_single_file, name='index_file'),
    path('fuzzy-search/suggestions/', fuzzy_search_views.get_suggestions, name='search_suggestions'),
    path('fuzzy-search/stats/', fuzzy_search_views.get_search_stats, name='search_stats'),
    path('fuzzy-search/interact/<int:file_id>/', fuzzy_search_views.record_file_interaction, name='record_interaction'),
    path('fuzzy-search/clear-cache/', fuzzy_search_views.clear_search_cache, name='clear_search_cache'),

    # Intelligent Search Suggestions API
    path('search-suggestions/', search_suggestion_views.get_search_suggestions, name='intelligent_suggestions'),
    path('search-suggestions/record/', search_suggestion_views.record_search_query, name='record_search'),
    path('search-suggestions/click/', search_suggestion_views.record_search_click, name='record_click'),
    path('search-suggestions/analytics/', search_suggestion_views.get_search_analytics, name='search_analytics'),
    path('search-suggestions/trending/', search_suggestion_views.get_trending_searches, name='trending_searches'),
    path('search-suggestions/clear/', search_suggestion_views.clear_search_history, name='clear_history'),
    path('search-suggestions/save/', search_suggestion_views.save_search_data, name='save_search_data'),
]

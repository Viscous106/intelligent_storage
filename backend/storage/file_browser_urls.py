"""
URL configuration for File Browser
"""

from django.urls import path
from . import file_browser_views

app_name = 'file_browser'

urlpatterns = [
    # Web views
    path('browse/', file_browser_views.FileBrowserView.as_view(), name='browse'),

    # API endpoints
    path('api/browse/', file_browser_views.file_browser_api, name='browse_api'),
    path('api/stats/', file_browser_views.folder_stats_api, name='stats_api'),
    path('api/download/<int:file_id>/', file_browser_views.download_file, name='download'),
    path('api/preview/<int:file_id>/', file_browser_views.preview_file, name='preview'),
]

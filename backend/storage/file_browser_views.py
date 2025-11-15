"""
File Browser Views
Allow users to browse their uploaded files by category.
"""

from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404
from django.views.generic import ListView, TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view
from rest_framework.response import Response
from pathlib import Path
import os

from .models import MediaFile
from .file_organizer import file_organizer


class FileBrowserView(TemplateView):
    """Browse files by category."""
    template_name = 'storage/file_browser.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get folder statistics
        stats = file_organizer.get_folder_stats()
        context['folder_stats'] = stats

        # Get selected category from URL
        category = self.request.GET.get('category', 'all')
        context['selected_category'] = category

        # Normalize category (handle both singular and plural forms)
        category_map = {
            'image': 'images',
            'video': 'videos',
            'audio': 'audio',
            'document': 'documents',
            'code': 'code',
            'compressed': 'compressed',
            'program': 'programs',
            'other': 'others',
        }

        # Get files for selected category
        if category == 'all':
            files = MediaFile.objects.all().order_by('-uploaded_at')[:100]
        else:
            db_category = category_map.get(category, category)
            files = MediaFile.objects.filter(
                detected_type=db_category
            ).order_by('-uploaded_at')[:100]

        context['files'] = files

        # Categories for sidebar
        context['categories'] = [
            {'key': 'all', 'name': 'All Files', 'icon': '📁'},
            {'key': 'image', 'name': 'Images', 'icon': '🖼️'},
            {'key': 'video', 'name': 'Videos', 'icon': '🎬'},
            {'key': 'audio', 'name': 'Audio', 'icon': '🎵'},
            {'key': 'document', 'name': 'Documents', 'icon': '📄'},
            {'key': 'code', 'name': 'Code', 'icon': '💻'},
            {'key': 'compressed', 'name': 'Archives', 'icon': '📦'},
            {'key': 'other', 'name': 'Others', 'icon': '📎'},
        ]

        return context


@api_view(['GET'])
def file_browser_api(request):
    """
    API endpoint to browse files by category.

    Query params:
    - category: Filter by file type (image, video, document, etc.)
    - limit: Number of files to return (default: 50)
    - offset: Pagination offset (default: 0)
    """
    category = request.GET.get('category', 'all')
    limit = min(int(request.GET.get('limit', 50)), 100)
    offset = int(request.GET.get('offset', 0))

    # Normalize category (handle both singular and plural forms)
    # Database stores plural forms like "images", "videos"
    category_map = {
        'image': 'images',
        'video': 'videos',
        'audio': 'audio',
        'document': 'documents',
        'code': 'code',
        'compressed': 'compressed',
        'program': 'programs',
        'other': 'others',
    }

    # Get files
    if category == 'all':
        files = MediaFile.objects.all()
    else:
        # Use mapped plural form for database query
        db_category = category_map.get(category, category)
        files = MediaFile.objects.filter(detected_type=db_category)

    # Pagination
    total_count = files.count()
    files = files.order_by('-uploaded_at')[offset:offset+limit]

    # Reverse map for serialization (plural to singular)
    type_display_map = {
        'images': 'image',
        'videos': 'video',
        'audio': 'audio',
        'documents': 'document',
        'code': 'code',
        'compressed': 'compressed',
        'programs': 'program',
        'others': 'other',
    }

    # Serialize files
    files_data = []
    for file in files:
        # Convert plural form back to singular for frontend
        display_type = type_display_map.get(file.detected_type, file.detected_type)

        files_data.append({
            'id': file.id,
            'name': file.original_name,
            'type': display_type,
            'size': file.file_size,
            'mime_type': file.mime_type,
            'uploaded_at': file.uploaded_at.isoformat(),
            'is_indexed': file.is_indexed,
            'relative_path': file.relative_path,
            'preview_url': f'/media/{file.relative_path}' if file.relative_path else None,
        })

    return Response({
        'files': files_data,
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
        'has_more': offset + limit < total_count,
    })


@api_view(['GET'])
def folder_stats_api(request):
    """Get statistics for all file type folders."""
    stats = file_organizer.get_folder_stats()

    # Add total stats
    total = {
        'count': sum(s['count'] for s in stats.values()),
        'size_bytes': sum(s['size_bytes'] for s in stats.values()),
        'size_mb': sum(s['size_mb'] for s in stats.values()),
    }

    return Response({
        'by_type': stats,
        'total': total,
    })


@api_view(['GET'])
def download_file(request, file_id):
    """Download a file by ID."""
    try:
        media_file = MediaFile.objects.get(id=file_id)

        if not media_file.file_path or not os.path.exists(media_file.file_path):
            raise Http404('File not found on disk')

        # Serve file
        response = FileResponse(
            open(media_file.file_path, 'rb'),
            content_type=media_file.mime_type
        )
        response['Content-Disposition'] = f'attachment; filename="{media_file.original_name}"'

        return response

    except MediaFile.DoesNotExist:
        raise Http404('File not found in database')


@api_view(['GET'])
def preview_file(request, file_id):
    """Preview a file (for images, PDFs, etc.)."""
    try:
        media_file = MediaFile.objects.get(id=file_id)

        if not media_file.file_path or not os.path.exists(media_file.file_path):
            raise Http404('File not found on disk')

        # Serve file for preview (inline)
        response = FileResponse(
            open(media_file.file_path, 'rb'),
            content_type=media_file.mime_type
        )
        response['Content-Disposition'] = f'inline; filename="{media_file.original_name}"'

        return response

    except MediaFile.DoesNotExist:
        raise Http404('File not found in database')

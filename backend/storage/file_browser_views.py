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
from pathlib import Path
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
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

        # Get files for selected category (exclude deleted files)
        if category == 'all':
            files = MediaFile.objects.filter(is_deleted=False).order_by('-uploaded_at')[:100]
        else:
            db_category = category_map.get(category, category)
            files = MediaFile.objects.filter(
                detected_type=db_category,
                is_deleted=False
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

    # Get files (exclude deleted files unless viewing trash)
    if category == 'trash':
        files = MediaFile.objects.filter(is_deleted=True)
    elif category == 'all':
        files = MediaFile.objects.filter(is_deleted=False)
    else:
        # Use mapped plural form for database query
        db_category = category_map.get(category, category)
        files = MediaFile.objects.filter(detected_type=db_category, is_deleted=False)

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

    return JsonResponse({
        'files': files_data,
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
        'has_more': offset + limit < total_count,
    })


def folder_stats_api(request):
    """Get statistics for all file type folders."""
    stats = file_organizer.get_folder_stats()

    # Add total stats
    total = {
        'count': sum(s['count'] for s in stats.values()),
        'size_bytes': sum(s['size_bytes'] for s in stats.values()),
        'size_mb': sum(s['size_mb'] for s in stats.values()),
    }

    # Add trash count
    trash_count = MediaFile.objects.filter(is_deleted=True).count()

    return JsonResponse({
        'by_type': stats,
        'total': total,
        'trash': trash_count,
    })


@csrf_exempt
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

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'

        return response

    except MediaFile.DoesNotExist:
        raise Http404('File not found in database')


@csrf_exempt
def preview_file(request, file_id):
    """
    Get rich preview data for a file with support for multiple formats.

    Returns JSON with:
    - For text/code/sql: Content as text with syntax info
    - For CSV: Parsed table data
    - For JSON: Parsed and formatted JSON
    - For images: URLs for display
    - For video/audio: Stream URLs
    - For PDFs: PDF viewer URL
    - For other formats: Download info
    """
    try:
        media_file = MediaFile.objects.get(id=file_id)

        if not media_file.file_path or not os.path.exists(media_file.file_path):
            return JsonResponse({
                'success': False,
                'error': 'File not found on disk'
            }, status=404)

        file_path = Path(media_file.file_path)
        extension = media_file.file_extension.lower()
        stat = file_path.stat()

        # Base preview data
        preview_data = {
            'success': True,
            'id': media_file.id,
            'filename': media_file.original_name,
            'extension': extension,
            'mime_type': media_file.mime_type,
            'file_size': media_file.file_size,
            'file_size_human': _human_readable_size(media_file.file_size),
            'uploaded_at': media_file.uploaded_at.isoformat(),
            'category': media_file.detected_type,
            'download_url': f'/files/api/download/{file_id}/'
        }

        # Determine preview type and add type-specific data
        preview_type = _get_preview_type(extension, media_file.mime_type)
        preview_data['preview_type'] = preview_type

        if preview_type == 'text' or preview_type == 'code':
            # Text and code files (including SQL)
            max_size = 5 * 1024 * 1024  # 5MB
            if stat.st_size <= max_size:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(100000)  # Read up to 100KB
                        preview_data['content'] = content
                        preview_data['language'] = _detect_language(extension)
                        preview_data['lines'] = content.count('\n') + 1
                        preview_data['can_preview'] = True
                except Exception as e:
                    preview_data['can_preview'] = False
                    preview_data['error'] = f'Error reading file: {str(e)}'
            else:
                preview_data['can_preview'] = False
                preview_data['message'] = 'File too large for preview. Please download to view.'

        elif preview_type == 'csv':
            # CSV files - special table preview
            max_size = 10 * 1024 * 1024  # 10MB for CSV
            if stat.st_size <= max_size:
                try:
                    csv_data = _parse_csv_preview(file_path)
                    preview_data['csv_data'] = csv_data
                    preview_data['can_preview'] = True
                except Exception as e:
                    preview_data['can_preview'] = False
                    preview_data['error'] = f'Error parsing CSV: {str(e)}'
            else:
                preview_data['can_preview'] = False
                preview_data['message'] = 'CSV file too large for preview. Please download to view.'

        elif preview_type == 'image':
            # Images
            preview_data['preview_url'] = f'/files/api/preview/content/{file_id}/'
            preview_data['can_preview'] = True

        elif preview_type == 'video':
            # Videos
            preview_data['stream_url'] = f'/files/api/preview/content/{file_id}/'
            preview_data['supports_streaming'] = extension in ['.mp4', '.webm', '.ogg']
            preview_data['can_preview'] = True

        elif preview_type == 'audio':
            # Audio
            preview_data['stream_url'] = f'/files/api/preview/content/{file_id}/'
            preview_data['can_preview'] = True

        elif preview_type == 'pdf':
            # PDFs
            preview_data['pdf_url'] = f'/files/api/preview/content/{file_id}/'
            preview_data['can_preview'] = True

        elif preview_type == 'json':
            # JSON files - parse and format
            max_size = 5 * 1024 * 1024  # 5MB
            if stat.st_size <= max_size:
                try:
                    import json as json_lib
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json_content = json_lib.load(f)
                        preview_data['json_data'] = json_content
                        preview_data['content'] = json_lib.dumps(json_content, indent=2)
                        preview_data['language'] = 'json'
                        preview_data['can_preview'] = True
                except Exception as e:
                    preview_data['can_preview'] = False
                    preview_data['error'] = f'Error parsing JSON: {str(e)}'
            else:
                preview_data['can_preview'] = False
                preview_data['message'] = 'JSON file too large for preview.'

        elif preview_type == 'executable':
            # Executables - no preview for security
            preview_data['can_preview'] = False
            preview_data['message'] = 'Preview not available for executable files. Download to run (use caution).'
            preview_data['warning'] = 'This is an executable file. Only run if from a trusted source.'

        elif preview_type == 'compressed':
            # Compressed files - could show contents list in future
            preview_data['can_preview'] = False
            preview_data['message'] = f'Archive file. Download to extract contents.'
            preview_data['hint'] = 'Future versions may support archive contents preview.'

        else:
            # Other/unknown files - no preview available
            preview_data['can_preview'] = False
            preview_data['message'] = f'Preview not available for {extension} files. Click download to view.'

        return JsonResponse(preview_data)

    except MediaFile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'File not found in database'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def delete_file(request, file_id):
    """Move file to trash (soft delete)."""
    try:
        media_file = MediaFile.objects.get(id=file_id)

        # Soft delete - move to trash
        media_file.is_deleted = True
        media_file.deleted_at = timezone.now()
        media_file.save()

        return JsonResponse({
            'success': True,
            'message': f'File "{media_file.original_name}" moved to trash'
        })

    except MediaFile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'File not found in database'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def permanent_delete_file(request, file_id):
    """Permanently delete a file from trash."""
    try:
        media_file = MediaFile.objects.get(id=file_id, is_deleted=True)

        # Delete physical file from disk
        if media_file.file_path and os.path.exists(media_file.file_path):
            try:
                os.remove(media_file.file_path)
            except OSError as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Failed to delete physical file: {str(e)}'
                }, status=500)

        # Delete database record permanently
        file_name = media_file.original_name
        media_file.delete()

        return JsonResponse({
            'success': True,
            'message': f'File "{file_name}" permanently deleted'
        })

    except MediaFile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'File not found in trash'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def restore_file(request, file_id):
    """Restore a file from trash."""
    try:
        media_file = MediaFile.objects.get(id=file_id, is_deleted=True)

        # Restore file
        media_file.is_deleted = False
        media_file.deleted_at = None
        media_file.save()

        return JsonResponse({
            'success': True,
            'message': f'File "{media_file.original_name}" restored'
        })

    except MediaFile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'File not found in trash'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def preview_file_content(request, file_id):
    """
    Stream file content for inline display/playback.
    Used for images, videos, audio, PDFs.
    """
    try:
        media_file = MediaFile.objects.get(id=file_id)

        if not media_file.file_path or not os.path.exists(media_file.file_path):
            raise Http404('File not found on disk')

        # Serve file with inline disposition
        response = FileResponse(
            open(media_file.file_path, 'rb'),
            content_type=media_file.mime_type
        )
        response['Content-Disposition'] = f'inline; filename="{media_file.original_name}"'

        # Add CORS headers to allow cross-origin access
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        # Remove X-Frame-Options to allow iframe embedding
        response['X-Frame-Options'] = 'SAMEORIGIN'

        return response

    except MediaFile.DoesNotExist:
        raise Http404('File not found in database')


# Helper functions for preview

def _human_readable_size(size_bytes):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def _get_preview_type(extension, mime_type):
    """
    Determine the preview type for a file based on MediaClassifier reference.

    Returns preview type aligned with system classification:
    - image, video, audio: Media files
    - code: Programming files
    - text: Text documents
    - csv, json, pdf: Special document formats
    - compressed: Archives
    - executable: Executables (no preview)
    - other: Unknown/unsupported
    """
    ext = extension.lower()

    # Images - aligned with MediaClassifier
    image_exts = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
        '.webp', '.svg', '.ico', '.raw', '.cr2', '.nef', '.arw', '.heic', '.heif'
    }
    if ext in image_exts or (mime_type and mime_type.startswith('image/')):
        return 'image'

    # Videos - aligned with MediaClassifier
    video_exts = {
        '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm',
        '.m4v', '.3gp', '.mpg', '.mpeg', '.ts', '.mts', '.vob', '.ogv'
    }
    if ext in video_exts or (mime_type and mime_type.startswith('video/')):
        return 'video'

    # Audio - aligned with MediaClassifier
    audio_exts = {
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a',
        '.opus', '.aiff', '.ape', '.alac'
    }
    if ext in audio_exts or (mime_type and mime_type.startswith('audio/')):
        return 'audio'

    # Executables - aligned with MediaClassifier (no preview)
    executable_exts = {
        '.exe', '.dll', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.msi', '.jar', '.app', '.deb', '.rpm', '.dmg', '.apk', '.sh'
    }
    if ext in executable_exts:
        return 'executable'

    # Programming/Code files - aligned with MediaClassifier
    programming_exts = {
        '.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx',  # C/C++
        '.py', '.pyw', '.pyx',  # Python
        '.java', '.class',  # Java
        '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
        '.html', '.htm', '.css', '.scss', '.sass', '.less',  # Web
        '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',  # Other languages
        '.r', '.m', '.sql', '.pl', '.lua', '.bash', '.ps1'  # More languages
    }
    if ext in programming_exts:
        return 'code'

    # Compressed files - aligned with MediaClassifier (limited preview)
    compressed_exts = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
        '.tgz', '.tar.gz', '.tar.bz2', '.tar.xz', '.z', '.lz',
        '.lzma', '.zipx', '.cab', '.iso'
    }
    if ext in compressed_exts:
        return 'compressed'

    # Special document formats that get custom preview
    if ext == '.pdf':
        return 'pdf'

    if ext == '.csv' or ext == '.tsv':
        return 'csv'

    if ext == '.json':
        return 'json'

    # Other document formats - aligned with MediaClassifier
    document_exts = {
        '.txt', '.md', '.rtf', '.log',  # Text
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Office
        '.odt', '.ods', '.odp',  # OpenOffice
        '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg'  # Config
    }
    if ext in document_exts:
        return 'text'

    return 'other'


def _detect_language(extension):
    """
    Detect programming language from file extension for syntax highlighting.
    Aligned with MediaClassifier programming_extensions.
    """
    language_map = {
        # C/C++
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp',
        '.hxx': 'cpp',
        # Python
        '.py': 'python',
        '.pyw': 'python',
        '.pyx': 'python',
        # Java
        '.java': 'java',
        '.class': 'java',
        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        # Web
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        # Other languages
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.m': 'matlab',
        '.sql': 'sql',
        '.pl': 'perl',
        '.lua': 'lua',
        '.sh': 'shell',
        '.bash': 'bash',
        '.ps1': 'powershell',
        # Markup and data formats
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        '.md': 'markdown',
        # Text files
        '.txt': 'plaintext',
        '.log': 'plaintext',
        '.rtf': 'plaintext',
    }
    return language_map.get(extension.lower(), 'plaintext')


def _parse_csv_preview(csv_path, max_rows=100):
    """
    Parse CSV file and return structured data for table display.

    Returns:
        {
            'headers': [...],
            'rows': [[...]],
            'total_rows': int,
            'total_columns': int,
            'schema': {...},  # Inferred data types
            'preview': bool   # True if showing partial data
        }
    """
    import csv

    result = {
        'headers': [],
        'rows': [],
        'total_rows': 0,
        'total_columns': 0,
        'schema': {},
        'preview': False
    }

    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as csvfile:
            # Try to detect dialect
            sample = csvfile.read(1024)
            csvfile.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
            except:
                dialect = csv.excel

            reader = csv.reader(csvfile, dialect)

            # Read headers
            try:
                result['headers'] = next(reader)
                result['total_columns'] = len(result['headers'])
            except StopIteration:
                return result

            # Read rows
            row_count = 0
            for row in reader:
                if row_count < max_rows:
                    result['rows'].append(row)
                row_count += 1

            result['total_rows'] = row_count
            result['preview'] = row_count > max_rows

            # Infer schema (data types) from first few rows
            result['schema'] = _infer_csv_schema(result['headers'], result['rows'])

    except Exception as e:
        raise Exception(f"Error parsing CSV: {str(e)}")

    return result


def _infer_csv_schema(headers, rows):
    """Infer data types for each column in CSV."""
    schema = {}

    if not rows:
        return schema

    num_columns = len(headers)

    for col_idx in range(num_columns):
        if col_idx >= len(headers):
            continue

        column_name = headers[col_idx]
        column_values = []

        # Collect values from this column
        for row in rows[:20]:  # Sample first 20 rows
            if col_idx < len(row):
                column_values.append(row[col_idx])

        # Infer type
        data_type = _infer_column_type(column_values)

        schema[column_name] = {
            'type': data_type,
            'index': col_idx
        }

    return schema


def _infer_column_type(values):
    """Infer data type from column values."""
    non_empty = [v for v in values if v and v.strip()]

    if not non_empty:
        return 'string'

    # Check if all are integers
    try:
        for v in non_empty:
            int(v)
        return 'integer'
    except ValueError:
        pass

    # Check if all are floats
    try:
        for v in non_empty:
            float(v)
        return 'float'
    except ValueError:
        pass

    # Check if all are booleans
    bool_values = {'true', 'false', '1', '0', 'yes', 'no', 't', 'f'}
    if all(v.lower() in bool_values for v in non_empty):
        return 'boolean'

    return 'string'

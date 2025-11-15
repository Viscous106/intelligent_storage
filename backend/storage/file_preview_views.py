"""
File Preview API Views

Provides preview endpoints for all file types:
- Images: Direct display with thumbnail support
- Videos: HTML5 video player
- Audio: HTML5 audio player
- PDFs: PDF.js viewer
- Text files: Syntax-highlighted code or plain text
- Documents: Metadata and download option
- Archives: Contents listing
"""

import os
import json
import csv
import mimetypes
from pathlib import Path
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .admin_auth import require_admin
from .media_storage import get_media_storage
import logging

logger = logging.getLogger(__name__)


def get_file_type_category(extension, mime_type):
    """Determine the preview category for a file"""
    ext = extension.lower()

    # Images
    image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico', '.heic', '.heif']
    if ext in image_exts or (mime_type and mime_type.startswith('image/')):
        return 'image'

    # Videos
    video_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv', '.m4v']
    if ext in video_exts or (mime_type and mime_type.startswith('video/')):
        return 'video'

    # Audio
    audio_exts = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma', '.opus']
    if ext in audio_exts or (mime_type and mime_type.startswith('audio/')):
        return 'audio'

    # PDF
    if ext == '.pdf':
        return 'pdf'

    # Code files
    code_exts = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.cs',
                 '.rb', '.php', '.go', '.rs', '.swift', '.kt', '.html', '.css', '.scss',
                 '.json', '.xml', '.yaml', '.yml', '.sh', '.bash', '.sql']
    if ext in code_exts:
        return 'code'

    # Text files
    text_exts = ['.txt', '.md', '.log', '.csv', '.rtf']
    if ext in text_exts or (mime_type and mime_type.startswith('text/')):
        return 'text'

    # Documents
    doc_exts = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp']
    if ext in doc_exts:
        return 'document'

    # Archives
    archive_exts = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
    if ext in archive_exts:
        return 'archive'

    return 'unknown'


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_file_preview(request, file_path, admin_id):
    """
    Get preview data for a file

    Returns different data based on file type:
    - Images: URL to display
    - Videos/Audio: URL for player
    - Text/Code: File content
    - PDFs: URL for PDF.js
    - Documents: Metadata
    - Archives: Contents listing
    """
    try:
        storage = get_media_storage()
        full_path = storage.base_path / file_path

        if not full_path.exists():
            return JsonResponse({
                'success': False,
                'error': 'File not found'
            }, status=404)

        # Check admin access
        if admin_id not in full_path.name:
            return JsonResponse({
                'success': False,
                'error': 'Access denied'
            }, status=403)

        stat = full_path.stat()
        extension = full_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(full_path))
        file_type = get_file_type_category(extension, mime_type)

        preview_data = {
            'success': True,
            'file_type': file_type,
            'name': full_path.name,
            'size': stat.st_size,
            'size_human': storage._human_readable_size(stat.st_size),
            'extension': extension,
            'mime_type': mime_type or 'application/octet-stream',
            'download_url': f'/api/filemanager/download/{file_path}'
        }

        # Type-specific preview data
        if file_type == 'image':
            # Check for thumbnails
            preview_data['preview_url'] = f'/api/filemanager/preview/content/{file_path}'
            preview_data['thumbnails'] = {}

            for size in ['small', 'medium', 'large']:
                thumb_name = f"{full_path.stem}_{size}.jpg"
                thumb_path = storage.thumbnails_path / thumb_name
                if thumb_path.exists():
                    preview_data['thumbnails'][size] = f'/api/filemanager/thumbnail/{file_path}?size={size}'

        elif file_type == 'video':
            preview_data['stream_url'] = f'/api/filemanager/preview/content/{file_path}'
            preview_data['supports_streaming'] = extension in ['.mp4', '.webm', '.ogg']

        elif file_type == 'audio':
            preview_data['stream_url'] = f'/api/filemanager/preview/content/{file_path}'

        elif file_type == 'pdf':
            preview_data['pdf_url'] = f'/api/filemanager/preview/content/{file_path}'

        elif file_type in ['code', 'text']:
            # Special handling for CSV files
            if extension == '.csv':
                max_preview_size = 5 * 1024 * 1024  # 5MB for CSV
                if stat.st_size <= max_preview_size:
                    try:
                        csv_data = parse_csv_file(full_path)
                        preview_data['csv_data'] = csv_data
                        preview_data['is_csv'] = True
                    except Exception as e:
                        logger.error(f"Error parsing CSV: {e}")
                        preview_data['error'] = f'Error parsing CSV: {str(e)}'
                else:
                    preview_data['too_large'] = True
                    preview_data['message'] = 'CSV file too large for preview'
            else:
                # Regular text/code files
                max_preview_size = 1024 * 1024  # 1MB
                if stat.st_size <= max_preview_size:
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(100000)  # Limit to 100KB for preview
                            preview_data['content'] = content
                            preview_data['language'] = detect_language(extension)
                            preview_data['lines'] = content.count('\n') + 1
                    except UnicodeDecodeError:
                        preview_data['error'] = 'Binary file - cannot preview as text'
                else:
                    preview_data['too_large'] = True
                    preview_data['message'] = 'File too large for preview'

        elif file_type == 'document':
            preview_data['message'] = 'Document preview requires download'
            preview_data['app_suggestion'] = get_app_suggestion(extension)

        elif file_type == 'archive':
            # List archive contents
            try:
                contents = list_archive_contents(full_path)
                preview_data['contents'] = contents
            except Exception as e:
                logger.error(f"Error listing archive contents: {e}")
                preview_data['message'] = 'Unable to list archive contents'

        else:
            preview_data['message'] = 'Preview not available for this file type'

        return JsonResponse(preview_data)

    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_file_content(request, file_path, admin_id):
    """
    Stream file content for preview
    Used for images, videos, audio, PDFs
    """
    try:
        storage = get_media_storage()
        full_path = storage.base_path / file_path

        if not full_path.exists():
            return JsonResponse({
                'success': False,
                'error': 'File not found'
            }, status=404)

        # Check admin access
        if admin_id not in full_path.name:
            return JsonResponse({
                'success': False,
                'error': 'Access denied'
            }, status=403)

        # Determine mime type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Return file with appropriate content type
        response = FileResponse(open(full_path, 'rb'), content_type=mime_type)
        response['Content-Length'] = full_path.stat().st_size

        # Add inline disposition for preview
        response['Content-Disposition'] = f'inline; filename="{full_path.name}"'

        return response

    except Exception as e:
        logger.error(f"Error streaming file content: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def detect_language(extension):
    """Detect programming language from file extension for syntax highlighting"""
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bash': 'bash',
    }
    return language_map.get(extension.lower(), 'plaintext')


def get_app_suggestion(extension):
    """Suggest application for opening document"""
    suggestions = {
        '.doc': 'Microsoft Word or LibreOffice Writer',
        '.docx': 'Microsoft Word or LibreOffice Writer',
        '.xls': 'Microsoft Excel or LibreOffice Calc',
        '.xlsx': 'Microsoft Excel or LibreOffice Calc',
        '.ppt': 'Microsoft PowerPoint or LibreOffice Impress',
        '.pptx': 'Microsoft PowerPoint or LibreOffice Impress',
        '.odt': 'LibreOffice Writer',
        '.ods': 'LibreOffice Calc',
        '.odp': 'LibreOffice Impress',
    }
    return suggestions.get(extension.lower(), 'Appropriate application')


def parse_csv_file(csv_path, max_rows=100):
    """
    Parse CSV file and return structured data for table display

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
            result['schema'] = infer_csv_schema(result['headers'], result['rows'])

    except Exception as e:
        logger.error(f"Error parsing CSV {csv_path}: {e}")
        raise

    return result


def infer_csv_schema(headers, rows):
    """Infer data types for each column in CSV"""
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
        data_type = infer_column_type(column_values)

        schema[column_name] = {
            'type': data_type,
            'index': col_idx
        }

    return schema


def infer_column_type(values):
    """Infer data type from column values"""
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

    # Check if all are dates (basic check)
    date_indicators = ['-', '/', ':']
    if any(all(ind in v for ind in date_indicators[:2]) for v in non_empty):
        return 'date'

    return 'string'


def list_archive_contents(archive_path):
    """List contents of an archive file"""
    import zipfile
    import tarfile
    import rarfile

    extension = archive_path.suffix.lower()
    contents = []

    try:
        if extension == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for info in zf.filelist[:100]:  # Limit to first 100 files
                    contents.append({
                        'name': info.filename,
                        'size': info.file_size,
                        'compressed_size': info.compress_size,
                        'is_dir': info.is_dir()
                    })

        elif extension in ['.tar', '.gz', '.bz2', '.xz']:
            mode = 'r'
            if extension == '.gz':
                mode = 'r:gz'
            elif extension == '.bz2':
                mode = 'r:bz2'
            elif extension == '.xz':
                mode = 'r:xz'

            with tarfile.open(archive_path, mode) as tf:
                for member in list(tf.getmembers())[:100]:
                    contents.append({
                        'name': member.name,
                        'size': member.size,
                        'is_dir': member.isdir()
                    })

        elif extension == '.rar':
            with rarfile.RarFile(archive_path, 'r') as rf:
                for info in rf.infolist()[:100]:
                    contents.append({
                        'name': info.filename,
                        'size': info.file_size,
                        'compressed_size': info.compress_size,
                        'is_dir': info.isdir()
                    })

    except Exception as e:
        logger.error(f"Error reading archive {archive_path}: {e}")
        raise

    return contents

"""
File Manager API Views

Provides a complete file manager interface with:
- Browse all smart folders
- View files in each category
- File preview
- Download files
- Search across all files
- Storage statistics
- Admin-only access
"""

import os
import json
from pathlib import Path
from datetime import datetime
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .admin_auth import require_admin
from .media_storage import get_media_storage
from .smart_folder_classifier import get_smart_classifier
import logging

logger = logging.getLogger(__name__)


def file_manager_ui(request):
    """
    Serve the file manager web interface
    """
    return render(request, 'file_manager.html')


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def browse_folders(request, admin_id):
    """
    Get all folders and their file counts

    Returns a tree structure of all categories with file counts
    """
    try:
        storage = get_media_storage()
        classifier = get_smart_classifier()

        # Get all categories
        all_categories = classifier.get_all_categories()

        # Build folder tree
        folders = []
        total_files = 0
        total_size = 0

        for category, description in sorted(all_categories.items()):
            category_path = storage.base_path / category

            if category_path.exists():
                # Count files in this category
                file_count = 0
                category_size = 0
                recent_files = []

                for root, dirs, files in os.walk(category_path):
                    for filename in files:
                        if admin_id in filename:
                            file_path = Path(root) / filename
                            file_count += 1
                            file_size = file_path.stat().st_size
                            category_size += file_size

                            # Get recent files (limit to 3)
                            if len(recent_files) < 3:
                                recent_files.append({
                                    'name': filename,
                                    'size': file_size,
                                    'modified': datetime.fromtimestamp(
                                        file_path.stat().st_mtime
                                    ).isoformat()
                                })

                if file_count > 0:
                    folders.append({
                        'category': category,
                        'description': description,
                        'file_count': file_count,
                        'size': category_size,
                        'size_human': storage._human_readable_size(category_size),
                        'path': str(category_path.relative_to(storage.base_path)),
                        'recent_files': recent_files
                    })

                    total_files += file_count
                    total_size += category_size

        return JsonResponse({
            'success': True,
            'folders': folders,
            'summary': {
                'total_folders': len(folders),
                'total_files': total_files,
                'total_size': total_size,
                'total_size_human': storage._human_readable_size(total_size)
            }
        })

    except Exception as e:
        logger.error(f"Error browsing folders: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def list_files_in_category(request, category, admin_id):
    """
    List all files in a specific category

    Query parameters:
    - page: Page number (default: 1)
    - limit: Files per page (default: 50)
    - sort: Sort by (name, date, size)
    - order: asc or desc
    """
    try:
        storage = get_media_storage()

        # Pagination
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 50))
        sort_by = request.GET.get('sort', 'date')
        order = request.GET.get('order', 'desc')

        # Get all files in category
        category_path = storage.base_path / category

        if not category_path.exists():
            return JsonResponse({
                'success': False,
                'error': f'Category "{category}" not found'
            }, status=404)

        files = []

        for root, dirs, filenames in os.walk(category_path):
            for filename in filenames:
                if admin_id in filename:
                    file_path = Path(root) / filename
                    stat = file_path.stat()

                    # Extract file info
                    relative_path = file_path.relative_to(storage.base_path)

                    files.append({
                        'name': filename,
                        'path': str(relative_path),
                        'category': category,
                        'size': stat.st_size,
                        'size_human': storage._human_readable_size(stat.st_size),
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'extension': Path(filename).suffix.lower()
                    })

        # Sort files
        if sort_by == 'name':
            files.sort(key=lambda x: x['name'], reverse=(order == 'desc'))
        elif sort_by == 'size':
            files.sort(key=lambda x: x['size'], reverse=(order == 'desc'))
        else:  # date
            files.sort(key=lambda x: x['modified'], reverse=(order == 'desc'))

        # Paginate
        start = (page - 1) * limit
        end = start + limit
        paginated_files = files[start:end]

        return JsonResponse({
            'success': True,
            'category': category,
            'files': paginated_files,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_files': len(files),
                'total_pages': (len(files) + limit - 1) // limit
            }
        })

    except Exception as e:
        logger.error(f"Error listing files in category: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def search_files(request, admin_id):
    """
    Search files across all categories

    Query parameters:
    - q: Search query
    - category: Optional category filter
    - extension: Optional extension filter
    """
    try:
        storage = get_media_storage()

        query = request.GET.get('q', '').lower()
        category_filter = request.GET.get('category')
        extension_filter = request.GET.get('extension', '').lower()

        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Search query required'
            }, status=400)

        # Search paths
        if category_filter:
            search_paths = [storage.base_path / category_filter]
        else:
            search_paths = [p for p in storage.base_path.iterdir()
                          if p.is_dir() and p.name not in ['thumbnails', 'temp']]

        results = []

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for root, dirs, filenames in os.walk(search_path):
                for filename in filenames:
                    if admin_id in filename:
                        # Search in filename
                        if query in filename.lower():
                            file_path = Path(root) / filename
                            stat = file_path.stat()

                            # Check extension filter
                            if extension_filter and not filename.lower().endswith(extension_filter):
                                continue

                            relative_path = file_path.relative_to(storage.base_path)
                            category = relative_path.parts[0]

                            results.append({
                                'name': filename,
                                'path': str(relative_path),
                                'category': category,
                                'size': stat.st_size,
                                'size_human': storage._human_readable_size(stat.st_size),
                                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                'extension': Path(filename).suffix.lower()
                            })

        # Sort by relevance (exact match first, then by date)
        results.sort(key=lambda x: (
            query not in x['name'].lower().split('_')[0],
            -datetime.fromisoformat(x['modified']).timestamp()
        ))

        return JsonResponse({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_file_info(request, file_path, admin_id):
    """
    Get detailed information about a specific file
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
        relative_path = full_path.relative_to(storage.base_path)
        category = relative_path.parts[0]

        file_info = {
            'name': full_path.name,
            'path': str(relative_path),
            'category': category,
            'size': stat.st_size,
            'size_human': storage._human_readable_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'extension': full_path.suffix.lower(),
            'is_image': category in ['photos', 'gifs', 'webp', 'icons'],
            'download_url': f'/api/filemanager/download/{file_path}'
        }

        # Check for thumbnails
        if file_info['is_image']:
            thumbnails = {}
            for size in ['small', 'medium', 'large']:
                thumb_name = f"{full_path.stem}_{size}.jpg"
                thumb_path = storage.thumbnails_path / thumb_name
                if thumb_path.exists():
                    thumbnails[size] = f'/api/filemanager/thumbnail/{file_path}?size={size}'

            if thumbnails:
                file_info['thumbnails'] = thumbnails

        return JsonResponse({
            'success': True,
            'file': file_info
        })

    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def download_file(request, file_path, admin_id):
    """
    Download a file
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

        # Serve file
        response = FileResponse(open(full_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{full_path.name}"'

        return response

    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return HttpResponse(f'Error: {str(e)}', status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_thumbnail(request, file_path, admin_id):
    """
    Get thumbnail for an image file

    Query parameters:
    - size: small, medium, or large
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

        size = request.GET.get('size', 'medium')
        thumb_name = f"{full_path.stem}_{size}.jpg"
        thumb_path = storage.thumbnails_path / thumb_name

        if not thumb_path.exists():
            # Return original if no thumbnail
            return FileResponse(open(full_path, 'rb'))

        return FileResponse(open(thumb_path, 'rb'))

    except Exception as e:
        logger.error(f"Error getting thumbnail: {e}")
        return HttpResponse(f'Error: {str(e)}', status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_admin
def delete_file(request, file_path, admin_id):
    """
    Delete a file and its thumbnails
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

        # Delete file
        full_path.unlink()

        # Delete thumbnails if image
        category = full_path.relative_to(storage.base_path).parts[0]
        if category in ['photos', 'gifs', 'webp', 'icons']:
            for size in ['small', 'medium', 'large']:
                thumb_name = f"{full_path.stem}_{size}.jpg"
                thumb_path = storage.thumbnails_path / thumb_name
                if thumb_path.exists():
                    thumb_path.unlink()

        logger.info(f"Deleted file: {file_path}")

        return JsonResponse({
            'success': True,
            'message': 'File deleted successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_storage_stats(request, admin_id):
    """
    Get comprehensive storage statistics
    """
    try:
        storage = get_media_storage()
        classifier = get_smart_classifier()

        stats = {
            'categories': [],
            'total_files': 0,
            'total_size': 0,
            'by_extension': {},
            'recent_uploads': []
        }

        all_files = []

        # Scan all categories
        for category in classifier.FILE_CATEGORIES.keys():
            category_path = storage.base_path / category

            if not category_path.exists():
                continue

            category_files = 0
            category_size = 0

            for root, dirs, filenames in os.walk(category_path):
                for filename in filenames:
                    if admin_id in filename:
                        file_path = Path(root) / filename
                        stat = file_path.stat()

                        category_files += 1
                        category_size += stat.st_size

                        # Track by extension
                        ext = file_path.suffix.lower()
                        if ext:
                            stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + 1

                        # Track all files for recent uploads
                        all_files.append({
                            'path': str(file_path.relative_to(storage.base_path)),
                            'name': filename,
                            'category': category,
                            'size': stat.st_size,
                            'modified': stat.st_mtime
                        })

            if category_files > 0:
                stats['categories'].append({
                    'category': category,
                    'description': classifier.FILE_CATEGORIES[category]['description'],
                    'files': category_files,
                    'size': category_size,
                    'size_human': storage._human_readable_size(category_size)
                })

                stats['total_files'] += category_files
                stats['total_size'] += category_size

        # Get recent uploads (last 10)
        all_files.sort(key=lambda x: x['modified'], reverse=True)
        stats['recent_uploads'] = [
            {
                'name': f['name'],
                'category': f['category'],
                'size_human': storage._human_readable_size(f['size']),
                'modified': datetime.fromtimestamp(f['modified']).isoformat()
            }
            for f in all_files[:10]
        ]

        stats['total_size_human'] = storage._human_readable_size(stats['total_size'])

        # Sort categories by file count
        stats['categories'].sort(key=lambda x: x['files'], reverse=True)

        return JsonResponse({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def batch_delete_files(request, admin_id):
    """
    Delete multiple files at once

    Request body:
    {
        "file_paths": ["category/file1.jpg", "category/file2.pdf", ...]
    }
    """
    try:
        storage = get_media_storage()

        # Parse request body
        data = json.loads(request.body)
        file_paths = data.get('file_paths', [])

        if not file_paths:
            return JsonResponse({
                'success': False,
                'error': 'No files specified'
            }, status=400)

        if len(file_paths) > 100:
            return JsonResponse({
                'success': False,
                'error': 'Maximum 100 files can be deleted at once'
            }, status=400)

        results = {
            'deleted': [],
            'failed': [],
            'total': len(file_paths)
        }

        for file_path in file_paths:
            try:
                full_path = storage.base_path / file_path

                # Check if file exists
                if not full_path.exists():
                    results['failed'].append({
                        'path': file_path,
                        'error': 'File not found'
                    })
                    continue

                # Check admin access
                if admin_id not in full_path.name:
                    results['failed'].append({
                        'path': file_path,
                        'error': 'Access denied'
                    })
                    continue

                # Delete file
                file_size = full_path.stat().st_size
                full_path.unlink()

                # Delete thumbnails if image
                category = full_path.relative_to(storage.base_path).parts[0]
                if category in ['photos', 'gifs', 'webp', 'icons']:
                    for size in ['small', 'medium', 'large']:
                        thumb_name = f"{full_path.stem}_{size}.jpg"
                        thumb_path = storage.thumbnails_path / thumb_name
                        if thumb_path.exists():
                            thumb_path.unlink()

                results['deleted'].append({
                    'path': file_path,
                    'size': file_size
                })

            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
                results['failed'].append({
                    'path': file_path,
                    'error': str(e)
                })

        logger.info(f"Batch delete: {len(results['deleted'])} succeeded, {len(results['failed'])} failed")

        return JsonResponse({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Error in batch delete: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def batch_download_files(request, admin_id):
    """
    Download multiple files as a ZIP archive

    Request body:
    {
        "file_paths": ["category/file1.jpg", "category/file2.pdf", ...],
        "archive_name": "optional_name.zip"
    }
    """
    try:
        import zipfile
        import io

        storage = get_media_storage()

        # Parse request body
        data = json.loads(request.body)
        file_paths = data.get('file_paths', [])
        archive_name = data.get('archive_name', 'download.zip')

        if not file_paths:
            return JsonResponse({
                'success': False,
                'error': 'No files specified'
            }, status=400)

        if len(file_paths) > 1000:
            return JsonResponse({
                'success': False,
                'error': 'Maximum 1000 files can be downloaded at once'
            }, status=400)

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            added_count = 0

            for file_path in file_paths:
                try:
                    full_path = storage.base_path / file_path

                    # Check if file exists
                    if not full_path.exists():
                        continue

                    # Check admin access
                    if admin_id not in full_path.name:
                        continue

                    # Add file to ZIP
                    zip_file.write(full_path, arcname=full_path.name)
                    added_count += 1

                except Exception as e:
                    logger.error(f"Error adding {file_path} to ZIP: {e}")
                    continue

        if added_count == 0:
            return JsonResponse({
                'success': False,
                'error': 'No valid files found to download'
            }, status=404)

        # Prepare response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{archive_name}"'

        logger.info(f"Batch download: {added_count} files in {archive_name}")

        return response

    except Exception as e:
        logger.error(f"Error in batch download: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

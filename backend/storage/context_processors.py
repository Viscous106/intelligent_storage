"""
Django Context Processors for Intelligent Storage System.
Add global variables to all template contexts.
"""

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum, Count
from storage.models import FileSearchStore, MediaFile, DocumentChunk


def storage_stats(request):
    """
    Add global storage statistics to context.
    Cached for 5 minutes.
    """
    stats = cache.get('global_storage_stats')

    if not stats:
        stats = {
            'total_stores': FileSearchStore.objects.count(),
            'active_stores': FileSearchStore.objects.filter(is_active=True).count(),
            'total_files': MediaFile.objects.count(),
            'indexed_files': MediaFile.objects.filter(is_indexed=True).count(),
            'total_chunks': DocumentChunk.objects.count(),
            'total_storage_bytes': MediaFile.objects.aggregate(
                total=Sum('file_size')
            )['total'] or 0,
        }

        # Calculate storage usage
        total_quota = FileSearchStore.objects.aggregate(
            total=Sum('storage_quota')
        )['total'] or 0

        stats['total_quota_bytes'] = total_quota
        stats['storage_usage_percentage'] = (
            (stats['total_storage_bytes'] / total_quota * 100)
            if total_quota > 0 else 0
        )

        cache.set('global_storage_stats', stats, 300)  # 5 minutes

    return {'storage_stats': stats}


def site_settings(request):
    """
    Add site-wide settings to context.
    """
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Intelligent Storage System'),
        'SITE_VERSION': getattr(settings, 'API_VERSION', '1.0'),
        'MAX_UPLOAD_SIZE': getattr(settings, 'MAX_UPLOAD_SIZE', 100 * 1024 * 1024),
        'DEBUG_MODE': settings.DEBUG,
    }


def active_stores(request):
    """
    Add list of active stores to context.
    Cached for 5 minutes.
    """
    stores = cache.get('active_stores_list')

    if not stores:
        stores = list(
            FileSearchStore.objects.filter(is_active=True)
            .values('id', 'name', 'display_name', 'store_id')
            .order_by('display_name')
        )
        cache.set('active_stores_list', stores, 300)

    return {'active_stores': stores}


def user_preferences(request):
    """
    Add user preferences to context.
    """
    prefs = {
        'theme': request.session.get('theme', 'light'),
        'items_per_page': request.session.get('items_per_page', 20),
        'default_chunking': request.session.get('default_chunking', 'auto'),
    }
    return {'user_prefs': prefs}


def navigation_context(request):
    """
    Add navigation-related context.
    """
    current_path = request.path

    nav_items = [
        {
            'name': 'Dashboard',
            'url': '/',
            'icon': '🏠',
            'active': current_path == '/',
        },
        {
            'name': 'Files',
            'url': '/files/',
            'icon': '📁',
            'active': current_path.startswith('/files/'),
        },
        {
            'name': 'Stores',
            'url': '/stores/',
            'icon': '🗄️',
            'active': current_path.startswith('/stores/'),
        },
        {
            'name': 'Search',
            'url': '/search/',
            'icon': '🔍',
            'active': current_path.startswith('/search/'),
        },
    ]

    return {
        'nav_items': nav_items,
        'current_path': current_path,
    }

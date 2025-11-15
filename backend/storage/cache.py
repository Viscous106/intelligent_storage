"""
Django Caching Utilities for Intelligent Storage System.
Cache managers, decorators, and optimization functions.
Cross-platform compatible (Windows + Linux).
"""

from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# ===== Cache Key Generators =====

def generate_cache_key(prefix, *args, **kwargs):
    """
    Generate a cache key from arguments.

    Args:
        prefix: Key prefix
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        str: Cache key
    """
    # Combine all arguments into a string
    key_parts = [prefix]

    for arg in args:
        key_parts.append(str(arg))

    for key, value in sorted(kwargs.items()):
        key_parts.append(f'{key}={value}')

    key_string = ':'.join(key_parts)

    # Hash if too long
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f'{prefix}:{key_hash}'

    return key_string


# ===== Cache Managers =====

class CacheManager:
    """Base cache manager class."""

    def __init__(self, prefix='', timeout=300):
        """
        Initialize cache manager.

        Args:
            prefix: Cache key prefix
            timeout: Default timeout in seconds
        """
        self.prefix = prefix
        self.timeout = timeout

    def get_key(self, *args, **kwargs):
        """Generate cache key."""
        return generate_cache_key(self.prefix, *args, **kwargs)

    def get(self, *args, **kwargs):
        """Get value from cache."""
        key = self.get_key(*args, **kwargs)
        value = cache.get(key)

        if value is not None:
            logger.debug(f'Cache hit: {key}')
        else:
            logger.debug(f'Cache miss: {key}')

        return value

    def set(self, value, *args, timeout=None, **kwargs):
        """Set value in cache."""
        key = self.get_key(*args, **kwargs)
        timeout = timeout or self.timeout

        cache.set(key, value, timeout)
        logger.debug(f'Cache set: {key} (timeout: {timeout}s)')

    def delete(self, *args, **kwargs):
        """Delete value from cache."""
        key = self.get_key(*args, **kwargs)
        cache.delete(key)
        logger.debug(f'Cache deleted: {key}')

    def delete_pattern(self, pattern):
        """Delete all keys matching pattern."""
        # Note: This requires cache backend that supports pattern deletion
        # For now, we'll need to track keys manually
        logger.warning(f'Pattern deletion not fully implemented: {pattern}')


class FileCache(CacheManager):
    """Cache manager for file-related data."""

    def __init__(self):
        super().__init__(prefix='file', timeout=600)  # 10 minutes

    def get_file_metadata(self, file_id):
        """Get cached file metadata."""
        return self.get('metadata', file_id=file_id)

    def set_file_metadata(self, file_id, metadata):
        """Cache file metadata."""
        self.set(metadata, 'metadata', file_id=file_id)

    def invalidate_file(self, file_id):
        """Invalidate all cache for a file."""
        self.delete('metadata', file_id=file_id)
        self.delete('chunks', file_id=file_id)


class StoreCache(CacheManager):
    """Cache manager for store-related data."""

    def __init__(self):
        super().__init__(prefix='store', timeout=300)  # 5 minutes

    def get_store_stats(self, store_id):
        """Get cached store statistics."""
        return self.get('stats', store_id=store_id)

    def set_store_stats(self, store_id, stats):
        """Cache store statistics."""
        self.set(stats, 'stats', store_id=store_id)

    def invalidate_store(self, store_id):
        """Invalidate all cache for a store."""
        self.delete('stats', store_id=store_id)
        self.delete('files', store_id=store_id)
        self.delete('list', store_id=store_id)


class SearchCache(CacheManager):
    """Cache manager for search results."""

    def __init__(self):
        super().__init__(prefix='search', timeout=1800)  # 30 minutes

    def get_search_results(self, query_text, **filters):
        """Get cached search results."""
        return self.get('results', query=query_text, **filters)

    def set_search_results(self, query_text, results, **filters):
        """Cache search results."""
        self.set(results, 'results', query=query_text, **filters, timeout=1800)


# ===== Cache Decorators =====

def cached_property_with_ttl(ttl=300):
    """
    Decorator for caching property values with TTL.
    Usage: @cached_property_with_ttl(ttl=600)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self):
            cache_key = f'{self.__class__.__name__}_{self.pk}_{func.__name__}'
            value = cache.get(cache_key)

            if value is None:
                value = func(self)
                cache.set(cache_key, value, ttl)

            return value

        return property(wrapper)
    return decorator


def cache_page_conditional(condition_func, timeout=300):
    """
    Conditionally cache a page based on a condition function.
    Usage: @cache_page_conditional(lambda request: not request.user.is_staff, 600)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check condition
            should_cache = condition_func(request)

            if should_cache:
                # Generate cache key
                cache_key = generate_cache_key(
                    'page',
                    request.path,
                    request.GET.urlencode()
                )

                # Try to get cached response
                cached_response = cache.get(cache_key)
                if cached_response:
                    logger.debug(f'Page cache hit: {request.path}')
                    return cached_response

                # Execute view
                response = view_func(request, *args, **kwargs)

                # Cache response
                cache.set(cache_key, response, timeout)
                logger.debug(f'Page cached: {request.path}')

                return response
            else:
                # Don't cache
                return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# ===== Query Optimization =====

class QueryOptimizer:
    """Utilities for optimizing database queries."""

    @staticmethod
    def prefetch_file_relations(queryset):
        """
        Prefetch related objects for MediaFile queryset.

        Args:
            queryset: MediaFile queryset

        Returns:
            Optimized queryset
        """
        return queryset.select_related(
            'file_search_store'
        ).prefetch_related(
            'chunks'
        )

    @staticmethod
    def prefetch_store_relations(queryset):
        """
        Prefetch related objects for FileSearchStore queryset.

        Args:
            queryset: FileSearchStore queryset

        Returns:
            Optimized queryset
        """
        return queryset.prefetch_related(
            'files',
            'chunks'
        )

    @staticmethod
    def optimize_search_query(queryset):
        """
        Optimize search query queryset.

        Args:
            queryset: SearchQuery queryset

        Returns:
            Optimized queryset
        """
        return queryset.prefetch_related(
            'file_search_stores',
            'rag_responses__source_chunks'
        )


# ===== Batch Operations =====

class BatchProcessor:
    """Utilities for batch processing with caching."""

    @staticmethod
    def process_files_in_batches(file_ids, batch_size=100, cache_results=True):
        """
        Process files in batches with optional result caching.

        Args:
            file_ids: List of file IDs
            batch_size: Number of files per batch
            cache_results: Whether to cache results

        Returns:
            List of results
        """
        from storage.models import MediaFile

        results = []

        for i in range(0, len(file_ids), batch_size):
            batch_ids = file_ids[i:i+batch_size]

            # Check cache first if enabled
            if cache_results:
                cache_key = f'batch_files_{hash(tuple(batch_ids))}'
                cached = cache.get(cache_key)
                if cached:
                    results.extend(cached)
                    continue

            # Fetch batch
            files = MediaFile.objects.filter(
                id__in=batch_ids
            ).select_related('file_search_store')

            batch_results = list(files)
            results.extend(batch_results)

            # Cache if enabled
            if cache_results:
                cache.set(cache_key, batch_results, 600)

        return results


# ===== Cache Warming =====

def warm_cache_for_store(store_id):
    """
    Pre-populate cache for a store.

    Args:
        store_id: FileSearchStore ID
    """
    from storage.models import FileSearchStore, MediaFile

    logger.info(f'Warming cache for store {store_id}')

    try:
        # Load store
        store = FileSearchStore.objects.get(id=store_id)

        # Cache store stats
        store_cache = StoreCache()
        stats = {
            'total_files': store.total_files,
            'total_chunks': store.total_chunks,
            'storage_size_bytes': store.storage_size_bytes,
            'usage_percentage': store.storage_used_percentage,
        }
        store_cache.set_store_stats(store_id, stats)

        # Cache file list (first page)
        files = MediaFile.objects.filter(
            file_search_store_id=store_id
        ).select_related('file_search_store')[:20]

        cache_key = f'store:{store_id}:files:page1'
        cache.set(cache_key, list(files), 600)

        logger.info(f'Cache warmed for store {store_id}')

    except Exception as e:
        logger.error(f'Failed to warm cache for store {store_id}: {str(e)}')


def warm_global_cache():
    """Pre-populate global caches."""
    from storage.models import FileSearchStore

    logger.info('Warming global caches')

    # Cache active stores
    active_stores = list(
        FileSearchStore.objects.filter(is_active=True)
        .values('id', 'name', 'display_name')
    )
    cache.set('active_stores_list', active_stores, 300)

    # Cache global stats
    from django.db.models import Sum, Count
    stats = {
        'total_stores': FileSearchStore.objects.count(),
        'total_files': FileSearchStore.objects.aggregate(
            total=Sum('total_files')
        )['total'] or 0,
    }
    cache.set('global_stats', stats, 300)

    logger.info('Global caches warmed')


# ===== Cache Invalidation =====

class CacheInvalidator:
    """Utility for invalidating related caches."""

    @staticmethod
    def invalidate_file_caches(file_id):
        """Invalidate all caches related to a file."""
        file_cache = FileCache()
        file_cache.invalidate_file(file_id)

        # Also invalidate list caches
        cache.delete('mediafile_list')
        cache.delete('global_stats')

    @staticmethod
    def invalidate_store_caches(store_id):
        """Invalidate all caches related to a store."""
        store_cache = StoreCache()
        store_cache.invalidate_store(store_id)

        # Also invalidate global caches
        cache.delete('active_stores_list')
        cache.delete('global_stats')

    @staticmethod
    def invalidate_all():
        """Invalidate all application caches."""
        cache.clear()
        logger.warning('All caches cleared')


# ===== Performance Monitoring =====

class CacheMetrics:
    """Track cache performance metrics."""

    @staticmethod
    def get_cache_stats():
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics
        """
        # This is cache-backend dependent
        # For memcached/redis, you can get actual stats
        # For now, return basic info

        return {
            'backend': settings.CACHES['default']['BACKEND'],
            'location': settings.CACHES.get('default', {}).get('LOCATION', 'N/A'),
        }

    @staticmethod
    def log_cache_usage(operation, key, hit=True):
        """
        Log cache usage for monitoring.

        Args:
            operation: 'get', 'set', 'delete'
            key: Cache key
            hit: Whether it was a hit (for get operations)
        """
        logger.debug(f'Cache {operation}: {key} (hit: {hit})')


# ===== Initialize Cache Managers =====

# Global cache manager instances
file_cache = FileCache()
store_cache = StoreCache()
search_cache = SearchCache()

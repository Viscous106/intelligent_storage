"""
Django Database and Performance Optimization for Intelligent Storage.
Query optimization, indexing strategies, and performance utilities.
Cross-platform compatible (Windows + Linux).
"""

from django.db import connection
from django.db.models import Prefetch, Q, Count, Sum
from django.conf import settings
import logging
import time

logger = logging.getLogger(__name__)


# ===== Query Optimization =====

class QueryOptimizations:
    """Collection of query optimization utilities."""

    @staticmethod
    def optimize_file_list_query(queryset):
        """
        Optimize MediaFile list queries.

        Args:
            queryset: MediaFile queryset

        Returns:
            Optimized queryset with select_related and prefetch_related
        """
        return queryset.select_related(
            'file_search_store'
        ).only(
            'id', 'original_name', 'file_size', 'detected_type',
            'mime_type', 'is_indexed', 'uploaded_at',
            'file_search_store__name', 'file_search_store__display_name'
        )

    @staticmethod
    def optimize_store_list_query(queryset):
        """
        Optimize FileSearchStore list queries.

        Args:
            queryset: FileSearchStore queryset

        Returns:
            Optimized queryset with annotations
        """
        return queryset.annotate(
            file_count=Count('files'),
            chunk_count=Count('chunks')
        ).only(
            'id', 'name', 'display_name', 'is_active',
            'created_at', 'storage_quota', 'storage_size_bytes'
        )

    @staticmethod
    def optimize_search_query(queryset):
        """
        Optimize SearchQuery with related data.

        Args:
            queryset: SearchQuery queryset

        Returns:
            Optimized queryset
        """
        from storage.models import DocumentChunk

        return queryset.select_related(
            'user'
        ).prefetch_related(
            'file_search_stores',
            Prefetch(
                'rag_responses',
                queryset=None  # All RAG responses
            )
        )

    @staticmethod
    def get_files_with_chunks(file_ids):
        """
        Efficiently load files with their chunks.

        Args:
            file_ids: List of file IDs

        Returns:
            Queryset with prefetched chunks
        """
        from storage.models import MediaFile, DocumentChunk

        return MediaFile.objects.filter(
            id__in=file_ids
        ).prefetch_related(
            Prefetch(
                'chunks',
                queryset=DocumentChunk.objects.order_by('chunk_index')
            )
        )


# ===== Batch Operations =====

class BatchOperations:
    """Utilities for efficient batch operations."""

    @staticmethod
    def bulk_create_chunks(chunks_data, batch_size=1000):
        """
        Bulk create document chunks efficiently.

        Args:
            chunks_data: List of DocumentChunk instances
            batch_size: Number of chunks to create at once

        Returns:
            Number of chunks created
        """
        from storage.models import DocumentChunk

        total_created = 0

        for i in range(0, len(chunks_data), batch_size):
            batch = chunks_data[i:i+batch_size]
            DocumentChunk.objects.bulk_create(batch, batch_size)
            total_created += len(batch)

        logger.info(f'Bulk created {total_created} chunks')
        return total_created

    @staticmethod
    def bulk_update_fields(model, instances, fields, batch_size=500):
        """
        Bulk update specific fields efficiently.

        Args:
            model: Django model class
            instances: List of model instances
            fields: List of field names to update
            batch_size: Number of instances per batch

        Returns:
            Number of instances updated
        """
        total_updated = 0

        for i in range(0, len(instances), batch_size):
            batch = instances[i:i+batch_size]
            model.objects.bulk_update(batch, fields, batch_size)
            total_updated += len(batch)

        logger.info(f'Bulk updated {total_updated} instances')
        return total_updated

    @staticmethod
    def batch_delete_with_logging(queryset, batch_size=1000):
        """
        Delete records in batches with logging.

        Args:
            queryset: Queryset to delete
            batch_size: Number of records per batch

        Returns:
            Total number deleted
        """
        total = queryset.count()
        deleted = 0

        logger.info(f'Starting batch deletion of {total} records')

        while queryset.exists():
            # Get batch IDs
            batch_ids = list(queryset.values_list('id', flat=True)[:batch_size])

            # Delete batch
            count, _ = queryset.filter(id__in=batch_ids).delete()
            deleted += count

            logger.debug(f'Deleted {deleted}/{total} records')

        logger.info(f'Batch deletion completed: {deleted} records deleted')
        return deleted


# ===== Index Management =====

class IndexOptimization:
    """Database index management and optimization."""

    @staticmethod
    def get_missing_indexes():
        """
        Analyze queries and suggest missing indexes.

        Returns:
            List of suggested indexes
        """
        # This is a simplified version
        # In production, use tools like django-silk or django-debug-toolbar

        suggestions = []

        # Common lookup patterns
        suggestions.append({
            'model': 'MediaFile',
            'fields': ['file_search_store', 'is_indexed'],
            'reason': 'Frequent filtering by store and indexed status'
        })

        suggestions.append({
            'model': 'DocumentChunk',
            'fields': ['file_search_store', 'media_file'],
            'reason': 'Frequent joins on store and file'
        })

        return suggestions

    @staticmethod
    def analyze_slow_queries(min_time=1.0):
        """
        Analyze slow queries from connection.

        Args:
            min_time: Minimum query time in seconds

        Returns:
            List of slow queries
        """
        # This requires query logging to be enabled
        queries = connection.queries

        slow_queries = [
            {
                'sql': q['sql'][:200],
                'time': float(q['time'])
            }
            for q in queries
            if float(q['time']) >= min_time
        ]

        return slow_queries


# ===== Performance Monitoring =====

class PerformanceMonitor:
    """Monitor and log performance metrics."""

    def __init__(self):
        self.start_time = None
        self.query_count_start = None

    def __enter__(self):
        """Start monitoring."""
        self.start_time = time.time()
        self.query_count_start = len(connection.queries)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop monitoring and log results."""
        duration = time.time() - self.start_time
        query_count = len(connection.queries) - self.query_count_start

        logger.info(
            f'Performance: {duration:.3f}s, {query_count} queries'
        )

        if settings.DEBUG and query_count > 0:
            # Log queries in debug mode
            for query in connection.queries[-query_count:]:
                logger.debug(f'Query ({query["time"]}s): {query["sql"][:100]}')


# ===== Memory Optimization =====

class MemoryOptimization:
    """Utilities for memory-efficient operations."""

    @staticmethod
    def iterate_in_chunks(queryset, chunk_size=1000):
        """
        Iterate over queryset in chunks to save memory.

        Args:
            queryset: Django queryset
            chunk_size: Number of records per chunk

        Yields:
            Chunks of records
        """
        count = queryset.count()
        for offset in range(0, count, chunk_size):
            yield queryset[offset:offset + chunk_size]

    @staticmethod
    def process_large_queryset(queryset, process_func, chunk_size=1000):
        """
        Process large queryset without loading all into memory.

        Args:
            queryset: Django queryset
            process_func: Function to process each chunk
            chunk_size: Number of records per chunk

        Returns:
            Total records processed
        """
        total_processed = 0

        for chunk in MemoryOptimization.iterate_in_chunks(queryset, chunk_size):
            process_func(chunk)
            total_processed += len(chunk)

        return total_processed


# ===== Connection Pool Optimization =====

class ConnectionOptimization:
    """Database connection optimization utilities."""

    @staticmethod
    def get_connection_info():
        """
        Get current database connection information.

        Returns:
            dict: Connection information
        """
        return {
            'vendor': connection.vendor,
            'queries_count': len(connection.queries),
            'database': connection.settings_dict.get('NAME'),
        }

    @staticmethod
    def close_old_connections():
        """Close old database connections."""
        from django.db import close_old_connections
        close_old_connections()
        logger.info('Closed old database connections')


# ===== Aggregation Optimization =====

class AggregationOptimization:
    """Optimize aggregation queries."""

    @staticmethod
    def get_store_statistics_optimized(store_id):
        """
        Get store statistics with optimized query.

        Args:
            store_id: FileSearchStore ID

        Returns:
            dict: Statistics
        """
        from storage.models import FileSearchStore, MediaFile, DocumentChunk

        # Single query with aggregations
        stats = FileSearchStore.objects.filter(
            id=store_id
        ).aggregate(
            total_files=Count('files'),
            total_chunks=Count('chunks'),
            total_storage=Sum('files__file_size'),
        )

        return stats

    @staticmethod
    def get_file_type_distribution():
        """
        Get file type distribution efficiently.

        Returns:
            dict: Distribution by type
        """
        from storage.models import MediaFile

        distribution = MediaFile.objects.values(
            'detected_type'
        ).annotate(
            count=Count('id'),
            total_size=Sum('file_size')
        ).order_by('-count')

        return list(distribution)


# ===== Database Router for Read Replicas =====

class ReadWriteRouter:
    """
    Database router for read/write splitting.
    Route read queries to replicas and write queries to primary.
    """

    def db_for_read(self, model, **hints):
        """Point all read operations to replica."""
        # Check if read replica is configured
        if 'replica' in settings.DATABASES:
            return 'replica'
        return 'default'

    def db_for_write(self, model, **hints):
        """Point all write operations to primary."""
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between objects."""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only run on primary."""
        return db == 'default'


# ===== Query Utilities =====

def log_query_count(func):
    """
    Decorator to log query count for a function.

    Usage: @log_query_count
    """
    def wrapper(*args, **kwargs):
        query_count_start = len(connection.queries)

        result = func(*args, **kwargs)

        query_count = len(connection.queries) - query_count_start
        logger.info(f'{func.__name__} executed {query_count} queries')

        return result

    return wrapper


def reset_queries():
    """Reset query log (useful in debug mode)."""
    if settings.DEBUG:
        connection.queries_log.clear()
        logger.debug('Query log cleared')


# ===== Export Functions =====

__all__ = [
    'QueryOptimizations',
    'BatchOperations',
    'IndexOptimization',
    'PerformanceMonitor',
    'MemoryOptimization',
    'ConnectionOptimization',
    'AggregationOptimization',
    'ReadWriteRouter',
    'log_query_count',
    'reset_queries',
]

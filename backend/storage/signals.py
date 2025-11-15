"""
Django Signals for Intelligent Storage System.
Automated actions triggered by model changes.
Cross-platform compatible.
"""

from django.db.models.signals import (
    post_save, pre_save, post_delete, pre_delete,
    m2m_changed
)
from django.dispatch import receiver, Signal
from django.core.cache import cache
from django.utils import timezone
import logging
import os
import shutil
from pathlib import Path

from .models import (
    MediaFile, DocumentChunk, FileSearchStore,
    UploadBatch, SearchQuery, RAGResponse, JSONDataStore
)

logger = logging.getLogger(__name__)


# ===== Custom Signals =====

file_indexed = Signal()
file_deleted = Signal()
store_quota_exceeded = Signal()
batch_completed = Signal()


# ===== MediaFile Signals =====

@receiver(post_save, sender=MediaFile)
def update_store_statistics_on_file_save(sender, instance, created, **kwargs):
    """Update file search store statistics when file is saved."""
    if instance.file_search_store:
        store = instance.file_search_store

        # Update file count
        store.total_files = MediaFile.objects.filter(file_search_store=store).count()

        # Update storage size
        if created:
            store.storage_size_bytes += instance.file_size
            # Estimate embeddings size (~3x file size)
            if instance.is_indexed:
                store.embeddings_size_bytes += instance.file_size * 3

        store.save(update_fields=['total_files', 'storage_size_bytes', 'embeddings_size_bytes'])

        # Check quota
        if store.is_quota_exceeded():
            logger.warning(f"Storage quota exceeded for store: {store.name}")
            store_quota_exceeded.send(sender=FileSearchStore, instance=store)


@receiver(pre_delete, sender=MediaFile)
def cleanup_file_on_delete(sender, instance, **kwargs):
    """Delete physical file and update store statistics when MediaFile is deleted."""
    # Delete physical file (cross-platform)
    if instance.file_path and os.path.exists(instance.file_path):
        try:
            os.remove(instance.file_path)
            logger.info(f"Deleted file: {instance.file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {instance.file_path}: {str(e)}")

    # Update store statistics
    if instance.file_search_store:
        store = instance.file_search_store
        store.storage_size_bytes = max(0, store.storage_size_bytes - instance.file_size)
        if instance.is_indexed:
            store.embeddings_size_bytes = max(0, store.embeddings_size_bytes - (instance.file_size * 3))
        store.save(update_fields=['storage_size_bytes', 'embeddings_size_bytes'])

    # Send custom signal
    file_deleted.send(sender=MediaFile, instance=instance)


@receiver(post_save, sender=MediaFile)
def log_file_upload(sender, instance, created, **kwargs):
    """Log file upload events."""
    if created:
        logger.info(
            f"New file uploaded: {instance.original_name} "
            f"({instance.file_size} bytes) - Type: {instance.detected_type}"
        )


# ===== DocumentChunk Signals =====

@receiver(post_save, sender=DocumentChunk)
def update_chunk_count(sender, instance, created, **kwargs):
    """Update chunk count in file search store."""
    if created and instance.file_search_store:
        store = instance.file_search_store
        store.total_chunks = DocumentChunk.objects.filter(file_search_store=store).count()
        store.save(update_fields=['total_chunks'])

        # Send indexed signal
        if instance.media_file:
            file_indexed.send(sender=MediaFile, instance=instance.media_file)


@receiver(post_delete, sender=DocumentChunk)
def decrease_chunk_count(sender, instance, **kwargs):
    """Decrease chunk count when chunk is deleted."""
    if instance.file_search_store:
        store = instance.file_search_store
        store.total_chunks = DocumentChunk.objects.filter(file_search_store=store).count()
        store.save(update_fields=['total_chunks'])


# ===== FileSearchStore Signals =====

@receiver(post_save, sender=FileSearchStore)
def log_store_creation(sender, instance, created, **kwargs):
    """Log file search store creation."""
    if created:
        logger.info(
            f"New File Search Store created: {instance.display_name} "
            f"({instance.name}) - Quota: {instance.storage_quota} bytes"
        )


@receiver(pre_delete, sender=FileSearchStore)
def cleanup_store_files(sender, instance, **kwargs):
    """Clean up associated data when store is deleted."""
    # Count items for logging
    file_count = instance.files.count()
    chunk_count = instance.chunks.count()

    logger.info(
        f"Deleting File Search Store: {instance.name} "
        f"({file_count} files, {chunk_count} chunks)"
    )


# ===== UploadBatch Signals =====

@receiver(post_save, sender=UploadBatch)
def check_batch_completion(sender, instance, **kwargs):
    """Check if batch upload is complete."""
    if instance.status == 'processing':
        total = instance.total_files
        processed = instance.processed_files + instance.failed_files

        if total > 0 and processed >= total:
            instance.status = 'completed'
            instance.completed_at = timezone.now()
            instance.save(update_fields=['status', 'completed_at'])

            logger.info(f"Batch {instance.batch_id} completed: {instance.processed_files} succeeded, {instance.failed_files} failed")
            batch_completed.send(sender=UploadBatch, instance=instance)


# ===== SearchQuery Signals =====

@receiver(post_save, sender=SearchQuery)
def log_search_query(sender, instance, created, **kwargs):
    """Log search queries for analytics."""
    if created:
        logger.info(
            f"Search query: '{instance.query_text[:50]}...' "
            f"- Results: {instance.results_count}"
        )


# ===== RAGResponse Signals =====

@receiver(post_save, sender=RAGResponse)
def log_rag_response(sender, instance, created, **kwargs):
    """Log RAG response generation."""
    if created:
        logger.info(
            f"RAG response generated for query: '{instance.search_query.query_text[:50]}...' "
            f"- Chunks used: {instance.source_chunks.count()}, "
            f"Grounding score: {instance.grounding_score}"
        )


# ===== Cache Invalidation Signals =====

@receiver(post_save, sender=MediaFile)
@receiver(post_delete, sender=MediaFile)
def invalidate_file_cache(sender, instance, **kwargs):
    """Invalidate cache when files are modified."""
    cache_keys = [
        f'mediafile_{instance.id}',
        'mediafile_list',
        f'store_{instance.file_search_store_id}_files' if instance.file_search_store_id else None,
    ]

    for key in cache_keys:
        if key:
            cache.delete(key)


@receiver(post_save, sender=FileSearchStore)
@receiver(post_delete, sender=FileSearchStore)
def invalidate_store_cache(sender, instance, **kwargs):
    """Invalidate cache when stores are modified."""
    cache_keys = [
        f'store_{instance.id}',
        f'store_{instance.store_id}',
        'store_list',
    ]

    for key in cache_keys:
        cache.delete(key)


# ===== M2M Changed Signals =====

@receiver(m2m_changed, sender=RAGResponse.source_chunks.through)
def update_rag_chunk_count(sender, instance, action, **kwargs):
    """Update chunk count when source chunks are added/removed."""
    if action in ['post_add', 'post_remove', 'post_clear']:
        logger.debug(f"RAG response {instance.id} chunks updated via {action}")


@receiver(m2m_changed, sender=SearchQuery.file_search_stores.through)
def log_search_store_filter(sender, instance, action, **kwargs):
    """Log when search queries filter by stores."""
    if action == 'post_add':
        stores = instance.file_search_stores.all()
        logger.debug(f"Search query filtered by stores: {[s.name for s in stores]}")


# ===== File System Monitoring =====

@receiver(post_save, sender=MediaFile)
def verify_file_exists(sender, instance, created, **kwargs):
    """Verify that the physical file exists (cross-platform)."""
    if instance.file_path:
        if not os.path.exists(instance.file_path):
            logger.error(
                f"Physical file missing for MediaFile {instance.id}: {instance.file_path}"
            )


# ===== Statistics Update Signals =====

@receiver(post_save, sender=MediaFile)
@receiver(post_delete, sender=MediaFile)
def update_global_statistics(sender, instance, **kwargs):
    """Update global statistics cache."""
    cache.delete('global_stats')
    cache.delete('file_type_stats')
    cache.delete('storage_stats')


# ===== Error Handling Signals =====

@receiver(file_indexed)
def handle_file_indexed(sender, instance, **kwargs):
    """Handle file indexed event."""
    logger.info(f"File indexed successfully: {instance.original_name}")


@receiver(store_quota_exceeded)
def handle_quota_exceeded(sender, instance, **kwargs):
    """Handle store quota exceeded event."""
    logger.warning(
        f"ALERT: Storage quota exceeded for store '{instance.name}' "
        f"({instance.storage_used_percentage:.1f}% used)"
    )

    # You could send email notifications here
    # send_quota_alert_email(instance)


@receiver(batch_completed)
def handle_batch_completed(sender, instance, **kwargs):
    """Handle batch upload completion."""
    logger.info(
        f"Batch upload completed: {instance.batch_id} - "
        f"Success: {instance.processed_files}, Failed: {instance.failed_files}"
    )

    # You could trigger post-processing here
    # if instance.processed_files > 0:
    #     trigger_batch_indexing.delay(instance.batch_id)


# ===== Auto-cleanup Signals =====

@receiver(pre_delete, sender=MediaFile)
def cleanup_orphaned_chunks(sender, instance, **kwargs):
    """Delete orphaned chunks when a file is deleted."""
    chunk_count = instance.chunks.count()
    if chunk_count > 0:
        instance.chunks.all().delete()
        logger.info(f"Deleted {chunk_count} orphaned chunks for file: {instance.original_name}")


# ===== Directory Management (Cross-platform) =====

@receiver(post_save, sender=MediaFile)
def ensure_directory_structure(sender, instance, created, **kwargs):
    """Ensure directory structure exists (cross-platform)."""
    if created and instance.file_path:
        directory = os.path.dirname(instance.file_path)
        if directory and not os.path.exists(directory):
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {str(e)}")


# ===== Initialization Signal =====

def register_signals():
    """
    Register all custom signals.
    Call this from apps.py ready() method.
    """
    logger.info("Storage app signals registered")
    return {
        'file_indexed': file_indexed,
        'file_deleted': file_deleted,
        'store_quota_exceeded': store_quota_exceeded,
        'batch_completed': batch_completed,
    }

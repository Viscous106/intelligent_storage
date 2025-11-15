"""
Django Admin Configuration for Intelligent Storage System.
Provides comprehensive admin interface for all models with advanced features.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum, Q
from django.utils.safestring import mark_safe
from django import forms
import json

from .models import (
    MediaFile, JSONDataStore, UploadBatch, DocumentChunk,
    SearchQuery, FileSearchStore, RAGResponse
)


# ===== Custom Admin Actions =====

@admin.action(description='Mark selected files as indexed')
def mark_as_indexed(modeladmin, request, queryset):
    """Mark selected media files as indexed."""
    from django.utils import timezone
    queryset.update(is_indexed=True, indexed_at=timezone.now())


@admin.action(description='Mark selected files as not indexed')
def mark_as_not_indexed(modeladmin, request, queryset):
    """Mark selected media files as not indexed."""
    queryset.update(is_indexed=False, indexed_at=None)


@admin.action(description='Delete selected and associated chunks')
def delete_with_chunks(modeladmin, request, queryset):
    """Delete files and their associated chunks."""
    chunk_count = 0
    for obj in queryset:
        chunk_count += obj.chunks.count()
        obj.chunks.all().delete()
    queryset.delete()
    modeladmin.message_user(
        request,
        f"Deleted {queryset.count()} files and {chunk_count} chunks."
    )


@admin.action(description='Activate selected stores')
def activate_stores(modeladmin, request, queryset):
    """Activate selected file search stores."""
    queryset.update(is_active=True)


@admin.action(description='Deactivate selected stores')
def deactivate_stores(modeladmin, request, queryset):
    """Deactivate selected file search stores."""
    queryset.update(is_active=False)


# ===== Inline Admin Classes =====

class DocumentChunkInline(admin.TabularInline):
    """Inline display of document chunks for MediaFile."""
    model = DocumentChunk
    extra = 0
    fields = ['chunk_index', 'chunk_size', 'token_count', 'chunking_strategy', 'created_at']
    readonly_fields = ['chunk_index', 'chunk_size', 'token_count', 'created_at']
    can_delete = True
    show_change_link = True
    max_num = 10  # Limit display for performance

    def has_add_permission(self, request, obj=None):
        return False  # Chunks created via indexing, not manually


class RAGResponseInline(admin.TabularInline):
    """Inline display of RAG responses for SearchQuery."""
    model = RAGResponse
    extra = 0
    fields = ['response_text_preview', 'grounding_score', 'total_tokens_used', 'created_at']
    readonly_fields = ['response_text_preview', 'grounding_score', 'total_tokens_used', 'created_at']
    can_delete = True
    show_change_link = True

    def response_text_preview(self, obj):
        """Show preview of response text."""
        return obj.response_text[:100] + '...' if len(obj.response_text) > 100 else obj.response_text
    response_text_preview.short_description = 'Response Preview'

    def has_add_permission(self, request, obj=None):
        return False


# ===== Model Admin Classes =====

@admin.register(FileSearchStore)
class FileSearchStoreAdmin(admin.ModelAdmin):
    """Admin interface for File Search Stores."""

    list_display = [
        'display_name', 'name', 'store_id_short', 'total_files', 'total_chunks',
        'storage_usage_display', 'quota_status', 'chunking_strategy', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'chunking_strategy', 'created_at']
    search_fields = ['name', 'display_name', 'description', 'store_id']
    readonly_fields = [
        'store_id', 'total_files', 'total_chunks', 'storage_size_bytes',
        'embeddings_size_bytes', 'storage_usage_bar', 'created_at', 'updated_at'
    ]
    actions = [activate_stores, deactivate_stores]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name', 'description', 'store_id', 'is_active')
        }),
        ('Storage Configuration', {
            'fields': ('storage_quota', 'storage_size_bytes', 'embeddings_size_bytes', 'storage_usage_bar')
        }),
        ('Chunking Configuration', {
            'fields': ('chunking_strategy', 'max_tokens_per_chunk', 'max_overlap_tokens')
        }),
        ('Statistics', {
            'fields': ('total_files', 'total_chunks'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('custom_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def store_id_short(self, obj):
        """Display shortened UUID."""
        return str(obj.store_id)[:8] + '...'
    store_id_short.short_description = 'Store ID'

    def storage_usage_display(self, obj):
        """Display storage usage with color coding."""
        percentage = obj.storage_used_percentage
        color = 'green' if percentage < 70 else 'orange' if percentage < 90 else 'red'
        return format_html(
            '<span style="color: {};">{:.2f}%</span>',
            color, percentage
        )
    storage_usage_display.short_description = 'Storage Used'

    def quota_status(self, obj):
        """Display quota status with icon."""
        if obj.is_quota_exceeded():
            return format_html('<span style="color: red;">⚠ EXCEEDED</span>')
        elif obj.storage_used_percentage > 90:
            return format_html('<span style="color: orange;">⚠ HIGH</span>')
        else:
            return format_html('<span style="color: green;">✓ OK</span>')
    quota_status.short_description = 'Quota'

    def storage_usage_bar(self, obj):
        """Display visual storage usage bar."""
        percentage = min(obj.storage_used_percentage, 100)
        color = '#28a745' if percentage < 70 else '#ffc107' if percentage < 90 else '#dc3545'
        return format_html(
            '<div style="width: 200px; background-color: #f0f0f0; border: 1px solid #ccc;">'
            '<div style="width: {}%; background-color: {}; height: 20px; text-align: center; color: white;">'
            '{:.1f}%</div></div>',
            percentage, color, percentage
        )
    storage_usage_bar.short_description = 'Usage Bar'

    def get_queryset(self, request):
        """Optimize queryset with annotations."""
        qs = super().get_queryset(request)
        return qs.select_related()


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    """Admin interface for Media Files."""

    list_display = [
        'original_name', 'detected_type', 'file_size_display', 'is_indexed',
        'file_search_store', 'ai_category', 'uploaded_at'
    ]
    list_filter = [
        'detected_type', 'is_indexed', 'file_search_store',
        'uploaded_at', 'ai_category'
    ]
    search_fields = ['original_name', 'ai_description', 'user_comment', 'ai_tags']
    readonly_fields = [
        'detected_type', 'mime_type', 'file_extension', 'magic_description',
        'ai_category', 'ai_subcategory', 'ai_tags', 'ai_description',
        'storage_category', 'storage_subcategory', 'relative_path',
        'uploaded_at', 'processed_at', 'indexed_at', 'file_size_display',
        'chunk_count', 'file_preview'
    ]
    actions = [mark_as_indexed, mark_as_not_indexed, delete_with_chunks]
    date_hierarchy = 'uploaded_at'
    inlines = [DocumentChunkInline]

    fieldsets = (
        ('File Information', {
            'fields': ('original_name', 'file_path', 'file_size', 'file_size_display', 'file_preview')
        }),
        ('File Search Store', {
            'fields': ('file_search_store', 'is_indexed')
        }),
        ('Type Detection', {
            'fields': ('detected_type', 'mime_type', 'file_extension', 'magic_description')
        }),
        ('AI Analysis', {
            'fields': ('ai_category', 'ai_subcategory', 'ai_tags', 'ai_description'),
            'classes': ('collapse',)
        }),
        ('Storage Organization', {
            'fields': ('storage_category', 'storage_subcategory', 'relative_path'),
            'classes': ('collapse',)
        }),
        ('User Input', {
            'fields': ('user_comment',)
        }),
        ('Custom Metadata', {
            'fields': ('custom_metadata',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('chunk_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'processed_at', 'indexed_at'),
            'classes': ('collapse',)
        }),
    )

    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    file_size_display.short_description = 'Size'

    def chunk_count(self, obj):
        """Display number of chunks."""
        count = obj.chunks.count()
        if count > 0:
            return format_html(
                '<a href="{}?media_file__id__exact={}">{} chunks</a>',
                reverse('admin:storage_documentchunk_changelist'),
                obj.id,
                count
            )
        return '0 chunks'
    chunk_count.short_description = 'Chunks'

    def file_preview(self, obj):
        """Display file preview for images."""
        if obj.detected_type == 'image' and obj.file_path:
            return format_html(
                '<img src="/media/{}" style="max-width: 200px; max-height: 200px;" />',
                obj.relative_path
            )
        return 'No preview available'
    file_preview.short_description = 'Preview'

    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('file_search_store').prefetch_related('chunks')


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """Admin interface for Document Chunks."""

    list_display = [
        'file_name', 'chunk_index', 'chunk_size', 'token_count',
        'chunking_strategy', 'file_search_store', 'created_at'
    ]
    list_filter = ['chunking_strategy', 'file_type', 'file_search_store', 'created_at']
    search_fields = ['file_name', 'chunk_text', 'source_reference']
    readonly_fields = [
        'citation_id', 'chunk_text_preview', 'embedding_info',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('media_file', 'file_search_store', 'file_name', 'file_type')
        }),
        ('Chunk Data', {
            'fields': ('chunk_index', 'chunk_text_preview', 'chunk_size', 'token_count')
        }),
        ('Chunking Configuration', {
            'fields': ('chunking_strategy', 'overlap_tokens')
        }),
        ('Citation', {
            'fields': ('citation_id', 'source_reference', 'page_number')
        }),
        ('Embedding', {
            'fields': ('embedding_info',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def chunk_text_preview(self, obj):
        """Display preview of chunk text."""
        text = obj.chunk_text
        if len(text) > 500:
            return text[:500] + '...'
        return text
    chunk_text_preview.short_description = 'Chunk Text'

    def embedding_info(self, obj):
        """Display embedding information."""
        if obj.embedding:
            return f"Vector (768 dimensions) - First 5: {obj.embedding[:5]}"
        return "No embedding"
    embedding_info.short_description = 'Embedding'

    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('media_file', 'file_search_store')


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    """Admin interface for Search Queries."""

    list_display = [
        'query_preview', 'results_count', 'top_result_score',
        'has_filters', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['query_text']
    readonly_fields = [
        'query_text', 'query_embedding_info', 'results_count',
        'top_result_score', 'metadata_filter_display', 'stores_display',
        'created_at'
    ]
    date_hierarchy = 'created_at'
    inlines = [RAGResponseInline]

    fieldsets = (
        ('Query', {
            'fields': ('query_text', 'query_embedding_info')
        }),
        ('Results', {
            'fields': ('results_count', 'top_result_score')
        }),
        ('Filters', {
            'fields': ('stores_display', 'metadata_filter_display')
        }),
        ('Context', {
            'fields': ('user_session', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def query_preview(self, obj):
        """Display query preview."""
        return obj.query_text[:100] + '...' if len(obj.query_text) > 100 else obj.query_text
    query_preview.short_description = 'Query'

    def has_filters(self, obj):
        """Check if query has filters."""
        has_store_filter = obj.file_search_stores.exists()
        has_metadata_filter = bool(obj.metadata_filter)
        if has_store_filter or has_metadata_filter:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">-</span>')
    has_filters.short_description = 'Filtered'

    def query_embedding_info(self, obj):
        """Display embedding info."""
        if obj.query_embedding:
            return f"Vector (768 dimensions)"
        return "No embedding"
    query_embedding_info.short_description = 'Embedding'

    def metadata_filter_display(self, obj):
        """Display metadata filter as formatted JSON."""
        if obj.metadata_filter:
            return format_html('<pre>{}</pre>', json.dumps(obj.metadata_filter, indent=2))
        return "No filters"
    metadata_filter_display.short_description = 'Metadata Filter'

    def stores_display(self, obj):
        """Display associated stores."""
        stores = obj.file_search_stores.all()
        if stores:
            return ', '.join([store.display_name for store in stores])
        return "All stores"
    stores_display.short_description = 'Stores'

    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('file_search_stores', 'rag_responses')


@admin.register(RAGResponse)
class RAGResponseAdmin(admin.ModelAdmin):
    """Admin interface for RAG Responses."""

    list_display = [
        'search_query_preview', 'grounding_score', 'chunk_count',
        'total_tokens_used', 'processing_time', 'created_at'
    ]
    list_filter = ['created_at', 'grounding_score']
    search_fields = ['response_text', 'search_query__query_text']
    readonly_fields = [
        'search_query', 'response_text_display', 'grounding_score',
        'citations_display', 'source_chunks_display', 'processing_time',
        'retrieval_time_ms', 'generation_time_ms', 'total_tokens_used',
        'created_at'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Query', {
            'fields': ('search_query',)
        }),
        ('Response', {
            'fields': ('response_text_display', 'grounding_score')
        }),
        ('Citations', {
            'fields': ('citations_display', 'source_chunks_display')
        }),
        ('Performance', {
            'fields': ('retrieval_time_ms', 'generation_time_ms', 'processing_time', 'total_tokens_used'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def search_query_preview(self, obj):
        """Display search query preview."""
        text = obj.search_query.query_text
        return text[:50] + '...' if len(text) > 50 else text
    search_query_preview.short_description = 'Query'

    def chunk_count(self, obj):
        """Display number of source chunks."""
        return obj.source_chunks.count()
    chunk_count.short_description = 'Chunks Used'

    def processing_time(self, obj):
        """Display total processing time."""
        if obj.retrieval_time_ms and obj.generation_time_ms:
            total = obj.retrieval_time_ms + obj.generation_time_ms
            return f"{total} ms"
        return "N/A"
    processing_time.short_description = 'Total Time'

    def response_text_display(self, obj):
        """Display response text."""
        return format_html('<pre style="white-space: pre-wrap;">{}</pre>', obj.response_text)
    response_text_display.short_description = 'Response'

    def citations_display(self, obj):
        """Display citations as formatted JSON."""
        if obj.citations:
            return format_html('<pre>{}</pre>', json.dumps(obj.citations, indent=2))
        return "No citations"
    citations_display.short_description = 'Citations'

    def source_chunks_display(self, obj):
        """Display source chunks."""
        chunks = obj.source_chunks.all()[:5]  # Limit to 5
        if chunks:
            html = '<ul>'
            for chunk in chunks:
                html += f'<li>{chunk.file_name} - Chunk {chunk.chunk_index}</li>'
            html += '</ul>'
            if obj.source_chunks.count() > 5:
                html += f'<p>... and {obj.source_chunks.count() - 5} more</p>'
            return format_html(html)
        return "No source chunks"
    source_chunks_display.short_description = 'Source Chunks'

    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('search_query').prefetch_related('source_chunks')


@admin.register(JSONDataStore)
class JSONDataStoreAdmin(admin.ModelAdmin):
    """Admin interface for JSON Data Stores."""

    list_display = [
        'name', 'database_type', 'confidence_score', 'record_count',
        'structure_info', 'created_at'
    ]
    list_filter = ['database_type', 'has_nested_objects', 'has_arrays', 'is_consistent', 'created_at']
    search_fields = ['name', 'description', 'ai_reasoning']
    readonly_fields = [
        'database_type', 'confidence_score', 'inferred_schema_display',
        'sample_data_display', 'structure_depth', 'has_nested_objects',
        'has_arrays', 'is_consistent', 'ai_reasoning', 'record_count',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Database Selection', {
            'fields': ('database_type', 'confidence_score', 'ai_reasoning')
        }),
        ('Storage Details', {
            'fields': ('table_name', 'collection_name')
        }),
        ('Schema Analysis', {
            'fields': (
                'inferred_schema_display', 'sample_data_display',
                'structure_depth', 'has_nested_objects', 'has_arrays', 'is_consistent'
            ),
            'classes': ('collapse',)
        }),
        ('User Input', {
            'fields': ('user_comment',)
        }),
        ('Statistics', {
            'fields': ('record_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def structure_info(self, obj):
        """Display structure information."""
        icons = []
        if obj.has_nested_objects:
            icons.append('📦 Nested')
        if obj.has_arrays:
            icons.append('📝 Arrays')
        if not obj.is_consistent:
            icons.append('⚠ Inconsistent')
        return ' | '.join(icons) if icons else '✓ Simple'
    structure_info.short_description = 'Structure'

    def inferred_schema_display(self, obj):
        """Display schema as formatted JSON."""
        if obj.inferred_schema:
            return format_html('<pre>{}</pre>', json.dumps(obj.inferred_schema, indent=2))
        return "No schema"
    inferred_schema_display.short_description = 'Schema'

    def sample_data_display(self, obj):
        """Display sample data as formatted JSON."""
        if obj.sample_data:
            return format_html('<pre>{}</pre>', json.dumps(obj.sample_data, indent=2))
        return "No sample data"
    sample_data_display.short_description = 'Sample Data'


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    """Admin interface for Upload Batches."""

    list_display = [
        'batch_id', 'status', 'progress_bar', 'total_files',
        'processed_files', 'failed_files', 'started_at', 'duration'
    ]
    list_filter = ['status', 'started_at']
    search_fields = ['batch_id']
    readonly_fields = [
        'batch_id', 'started_at', 'completed_at', 'duration',
        'progress_percentage', 'progress_bar'
    ]
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_id', 'status')
        }),
        ('Progress', {
            'fields': ('total_files', 'processed_files', 'failed_files', 'progress_percentage', 'progress_bar')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration')
        }),
    )

    def progress_percentage(self, obj):
        """Calculate progress percentage."""
        if obj.total_files == 0:
            return "0%"
        percentage = (obj.processed_files / obj.total_files) * 100
        return f"{percentage:.1f}%"
    progress_percentage.short_description = 'Progress'

    def progress_bar(self, obj):
        """Display visual progress bar."""
        if obj.total_files == 0:
            percentage = 0
        else:
            percentage = (obj.processed_files / obj.total_files) * 100

        color = '#28a745' if obj.status == 'completed' else '#ffc107' if obj.status == 'processing' else '#dc3545'
        return format_html(
            '<div style="width: 200px; background-color: #f0f0f0; border: 1px solid #ccc;">'
            '<div style="width: {}%; background-color: {}; height: 20px; text-align: center; color: white;">'
            '{:.0f}%</div></div>',
            percentage, color, percentage
        )
    progress_bar.short_description = 'Progress Bar'

    def duration(self, obj):
        """Calculate duration."""
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            seconds = delta.total_seconds()
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h"
        return "In progress" if obj.status == 'processing' else "N/A"
    duration.short_description = 'Duration'


# ===== Admin Site Customization =====

admin.site.site_header = "Intelligent Storage Admin"
admin.site.site_title = "Storage Admin Portal"
admin.site.index_title = "Welcome to Intelligent Storage Administration"

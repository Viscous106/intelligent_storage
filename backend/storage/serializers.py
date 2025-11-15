"""
Django REST Framework serializers for the storage app.
Includes Gemini-style File Search Store serializers.
"""

from rest_framework import serializers
from .models import (
    MediaFile, JSONDataStore, UploadBatch,
    FileSearchStore, DocumentChunk, SearchQuery, RAGResponse
)


class MediaFileSerializer(serializers.ModelSerializer):
    """Serializer for MediaFile model."""

    class Meta:
        model = MediaFile
        fields = '__all__'
        read_only_fields = [
            'detected_type', 'mime_type', 'file_extension',
            'magic_description', 'ai_category', 'ai_subcategory',
            'ai_tags', 'ai_description', 'storage_category',
            'storage_subcategory', 'relative_path', 'uploaded_at',
            'processed_at'
        ]


class JSONDataStoreSerializer(serializers.ModelSerializer):
    """Serializer for JSONDataStore model."""

    class Meta:
        model = JSONDataStore
        fields = '__all__'
        read_only_fields = [
            'database_type', 'confidence_score', 'inferred_schema',
            'structure_depth', 'has_nested_objects', 'has_arrays',
            'is_consistent', 'ai_reasoning', 'record_count',
            'created_at', 'updated_at'
        ]


class UploadBatchSerializer(serializers.ModelSerializer):
    """Serializer for UploadBatch model."""

    class Meta:
        model = UploadBatch
        fields = '__all__'
        read_only_fields = ['batch_id', 'started_at', 'completed_at']


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests."""

    file = serializers.FileField(required=True)
    user_comment = serializers.CharField(required=False, allow_blank=True)


class BatchFileUploadSerializer(serializers.Serializer):
    """Serializer for batch file upload requests."""

    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False
    )
    user_comment = serializers.CharField(required=False, allow_blank=True)


class JSONUploadSerializer(serializers.Serializer):
    """Serializer for JSON data upload requests."""

    data = serializers.JSONField(required=True)
    name = serializers.CharField(required=False)
    user_comment = serializers.CharField(required=False, allow_blank=True)
    force_db_type = serializers.ChoiceField(
        choices=['SQL', 'NoSQL'],
        required=False,
        help_text="Force a specific database type instead of AI recommendation"
    )


# ===== Gemini-style File Search Store Serializers =====

class FileSearchStoreSerializer(serializers.ModelSerializer):
    """Serializer for FileSearchStore model."""

    storage_used_percentage = serializers.SerializerMethodField()
    is_quota_exceeded = serializers.SerializerMethodField()
    total_size_bytes = serializers.SerializerMethodField()

    class Meta:
        model = FileSearchStore
        fields = '__all__'
        read_only_fields = [
            'store_id', 'total_files', 'total_chunks',
            'storage_size_bytes', 'embeddings_size_bytes',
            'created_at', 'updated_at'
        ]

    def get_storage_used_percentage(self, obj):
        """Calculate storage usage percentage."""
        return obj.storage_used_percentage

    def get_is_quota_exceeded(self, obj):
        """Check if quota is exceeded."""
        return obj.is_quota_exceeded()

    def get_total_size_bytes(self, obj):
        """Get total size including embeddings."""
        return obj.total_size_bytes


class FileSearchStoreCreateSerializer(serializers.Serializer):
    """Serializer for creating a new File Search Store."""

    name = serializers.CharField(max_length=255)
    display_name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    chunking_strategy = serializers.ChoiceField(
        choices=['auto', 'whitespace', 'semantic', 'fixed'],
        default='auto'
    )
    max_tokens_per_chunk = serializers.IntegerField(
        default=512,
        min_value=100,
        max_value=2048
    )
    max_overlap_tokens = serializers.IntegerField(
        default=50,
        min_value=0,
        max_value=500
    )
    storage_quota = serializers.IntegerField(
        default=1073741824,  # 1 GB
        help_text="Storage quota in bytes"
    )
    custom_metadata = serializers.JSONField(required=False, default=dict)


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for DocumentChunk model."""

    class Meta:
        model = DocumentChunk
        fields = '__all__'
        read_only_fields = [
            'citation_id', 'created_at', 'updated_at'
        ]


class SearchQuerySerializer(serializers.ModelSerializer):
    """Serializer for SearchQuery model."""

    class Meta:
        model = SearchQuery
        fields = '__all__'
        read_only_fields = ['created_at']


class RAGResponseSerializer(serializers.ModelSerializer):
    """Serializer for RAG Response with citations."""

    citations_formatted = serializers.SerializerMethodField()
    source_files = serializers.SerializerMethodField()

    class Meta:
        model = RAGResponse
        fields = '__all__'
        read_only_fields = ['created_at']

    def get_citations_formatted(self, obj):
        """Return formatted citations for display."""
        return obj.citations

    def get_source_files(self, obj):
        """Get list of unique source files."""
        source_files = set()
        for citation in obj.citations:
            if 'source_file' in citation:
                source_files.add(citation['source_file'])
        return list(source_files)


class FileIndexRequestSerializer(serializers.Serializer):
    """Serializer for file indexing requests."""

    file_id = serializers.IntegerField(required=True)
    file_search_store_name = serializers.CharField(required=False)
    chunking_strategy = serializers.ChoiceField(
        choices=['auto', 'whitespace', 'semantic', 'fixed'],
        required=False
    )
    max_tokens_per_chunk = serializers.IntegerField(
        required=False,
        min_value=100,
        max_value=2048
    )
    max_overlap_tokens = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=500
    )
    custom_metadata = serializers.JSONField(required=False)


class SemanticSearchRequestSerializer(serializers.Serializer):
    """Serializer for semantic search requests with Gemini-style filtering."""

    query = serializers.CharField(required=True)
    file_search_store_names = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Filter search to specific stores"
    )
    metadata_filter = serializers.JSONField(
        required=False,
        help_text="Filter by custom metadata (e.g., {'year': '2024'})"
    )
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)
    include_citations = serializers.BooleanField(default=True)


class RAGQueryRequestSerializer(serializers.Serializer):
    """Serializer for RAG query requests with grounding."""

    query = serializers.CharField(required=True)
    file_search_store_names = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    metadata_filter = serializers.JSONField(required=False)
    max_context_chunks = serializers.IntegerField(default=5, min_value=1, max_value=20)
    include_citations = serializers.BooleanField(default=True)
    include_grounding_metadata = serializers.BooleanField(default=True)

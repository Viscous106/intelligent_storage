from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from pgvector.django import VectorField
import uuid


class FileSearchStore(models.Model):
    """
    Persistent container for organizing documents and their embeddings.
    Similar to Gemini's File Search Store concept.
    """
    # Identification
    store_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text="Unique store name")
    display_name = models.CharField(max_length=255, help_text="Human-readable display name")
    description = models.TextField(blank=True, null=True)

    # Storage statistics
    total_files = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=0)
    storage_size_bytes = models.BigIntegerField(default=0, help_text="Actual file storage size")
    embeddings_size_bytes = models.BigIntegerField(default=0, help_text="Estimated embeddings storage size (~3x)")

    # Configuration
    chunking_strategy = models.CharField(
        max_length=50,
        default='auto',
        choices=[
            ('auto', 'Auto'),
            ('whitespace', 'Whitespace'),
            ('semantic', 'Semantic'),
            ('fixed', 'Fixed Size'),
        ],
        help_text="Default chunking strategy for files in this store"
    )
    max_tokens_per_chunk = models.IntegerField(
        default=512,
        validators=[MinValueValidator(100), MaxValueValidator(2048)],
        help_text="Maximum tokens per chunk"
    )
    max_overlap_tokens = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(500)],
        help_text="Overlap between consecutive chunks"
    )

    # Storage limits (in bytes)
    storage_quota = models.BigIntegerField(
        default=1073741824,  # 1 GB default
        help_text="Storage quota in bytes"
    )

    # Metadata
    custom_metadata = models.JSONField(default=dict, blank=True, help_text="Store-level metadata")

    # Status
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['store_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.name})"

    @property
    def total_size_bytes(self):
        """Total size including embeddings overhead"""
        return self.storage_size_bytes + self.embeddings_size_bytes

    @property
    def storage_used_percentage(self):
        """Percentage of quota used"""
        if self.storage_quota == 0:
            return 0
        return (self.total_size_bytes / self.storage_quota) * 100

    def is_quota_exceeded(self):
        """Check if quota is exceeded"""
        return self.total_size_bytes > self.storage_quota


class MediaFile(models.Model):
    """
    Represents an uploaded media file with comprehensive metadata.
    """
    # File Search Store association
    file_search_store = models.ForeignKey(
        FileSearchStore,
        on_delete=models.SET_NULL,
        related_name='files',
        null=True,
        blank=True,
        help_text="Optional file search store for organized document management"
    )

    # File information
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=1024)
    file_size = models.BigIntegerField(help_text="File size in bytes")

    # Type detection
    detected_type = models.CharField(max_length=50, help_text="Primary file category")
    mime_type = models.CharField(max_length=100)
    file_extension = models.CharField(max_length=20)
    magic_description = models.TextField(blank=True, null=True)

    # AI Analysis
    ai_category = models.CharField(max_length=255, blank=True, null=True)
    ai_subcategory = models.CharField(max_length=255, blank=True, null=True)
    ai_tags = models.JSONField(default=list, blank=True)
    ai_description = models.TextField(blank=True, null=True)

    # User input
    user_comment = models.TextField(blank=True, null=True)

    # Storage organization
    storage_category = models.CharField(max_length=100)
    storage_subcategory = models.CharField(max_length=100)
    relative_path = models.CharField(max_length=1024)

    # Custom metadata for filtering (Gemini-style)
    custom_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom key-value metadata for filtering searches"
    )

    # Indexing status
    is_indexed = models.BooleanField(default=False, help_text="Whether file has been indexed for search")
    indexed_at = models.DateTimeField(null=True, blank=True, help_text="When file was indexed")

    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['detected_type']),
            models.Index(fields=['storage_category']),
            models.Index(fields=['uploaded_at']),
        ]

    def __str__(self):
        return f"{self.original_name} ({self.detected_type})"

class JSONDataStore(models.Model):
    """
    Tracks JSON data storage in either SQL or NoSQL database.
    """
    # Identification
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    # Database choice
    DATABASE_TYPES = [
        ('SQL', 'PostgreSQL'),
        ('NoSQL', 'MongoDB'),
    ]
    database_type = models.CharField(max_length=10, choices=DATABASE_TYPES)
    confidence_score = models.IntegerField(help_text="AI confidence in DB choice (0-100)")

    # Storage details
    table_name = models.CharField(max_length=255, blank=True, null=True)
    collection_name = models.CharField(max_length=255, blank=True, null=True)

    # Schema information
    inferred_schema = models.JSONField(default=dict)
    sample_data = models.JSONField(default=dict, blank=True)

    # Analysis metadata
    structure_depth = models.IntegerField(default=0)
    has_nested_objects = models.BooleanField(default=False)
    has_arrays = models.BooleanField(default=False)
    is_consistent = models.BooleanField(default=True)
    ai_reasoning = models.TextField(blank=True, null=True)

    # User input
    user_comment = models.TextField(blank=True, null=True)

    # Stats
    record_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['database_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.database_type})"


class UploadBatch(models.Model):
    """
    Tracks batch upload operations.
    """
    batch_id = models.CharField(max_length=100, unique=True)
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)

    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Batch {self.batch_id} ({self.status})"


class DocumentChunk(models.Model):
    """
    Stores chunked document content with vector embeddings for semantic search.
    Implements RAG (Retrieval Augmented Generation) capabilities.
    """
    # Source file reference
    media_file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        related_name='chunks',
        null=True,
        blank=True,
        help_text="Reference to the source media file (if applicable)"
    )

    # File Search Store reference
    file_search_store = models.ForeignKey(
        FileSearchStore,
        on_delete=models.CASCADE,
        related_name='chunks',
        null=True,
        blank=True,
        help_text="File search store this chunk belongs to"
    )

    # Chunk information
    chunk_index = models.IntegerField(help_text="Position of this chunk in the document")
    chunk_text = models.TextField(help_text="The actual text content of this chunk")
    chunk_size = models.IntegerField(help_text="Number of characters in this chunk")
    token_count = models.IntegerField(default=0, help_text="Estimated token count for this chunk")

    # Vector embedding for semantic search
    embedding = VectorField(
        dimensions=768,
        help_text="Vector embedding generated by Ollama nomic-embed-text model"
    )

    # Metadata
    file_name = models.CharField(max_length=255, help_text="Original file name")
    file_type = models.CharField(max_length=50, help_text="File type/category")
    page_number = models.IntegerField(null=True, blank=True, help_text="Page number (for PDFs)")

    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (author, date, tags, etc.)"
    )

    # Chunking configuration used
    chunking_strategy = models.CharField(max_length=50, default='auto')
    overlap_tokens = models.IntegerField(default=0, help_text="Overlap with previous chunk")

    # Citation tracking
    citation_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    source_reference = models.CharField(
        max_length=500,
        blank=True,
        help_text="Human-readable source reference (e.g., 'report.pdf, page 5, para 3')"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['media_file', 'chunk_index']
        indexes = [
            models.Index(fields=['file_name']),
            models.Index(fields=['file_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.file_name} - Chunk {self.chunk_index}"


class SearchQuery(models.Model):
    """
    Tracks search queries for analytics and improvement.
    """
    query_text = models.TextField(help_text="The search query")
    query_embedding = VectorField(
        dimensions=768,
        help_text="Vector embedding of the query"
    )

    # Results metadata
    results_count = models.IntegerField(default=0)
    top_result_score = models.FloatField(null=True, blank=True)

    # File Search Store filter
    file_search_stores = models.ManyToManyField(
        FileSearchStore,
        blank=True,
        help_text="Stores searched (if filtered)"
    )

    # Metadata filter used
    metadata_filter = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadata filter applied to search"
    )

    # Context
    user_session = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Query: {self.query_text[:50]}..."


class RAGResponse(models.Model):
    """
    Tracks RAG responses with grounding metadata and citations.
    Similar to Gemini's grounding_metadata.
    """
    # Query reference
    search_query = models.ForeignKey(
        SearchQuery,
        on_delete=models.CASCADE,
        related_name='rag_responses',
        help_text="Original search query"
    )

    # Response
    response_text = models.TextField(help_text="Generated response text")

    # Retrieved chunks used
    source_chunks = models.ManyToManyField(
        DocumentChunk,
        related_name='rag_responses',
        help_text="Document chunks used to generate this response"
    )

    # Grounding metadata
    grounding_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score for grounding (0-1)"
    )

    citations = models.JSONField(
        default=list,
        help_text="Structured citation data with chunk references"
    )

    # Example citation structure:
    # [
    #     {
    #         "citation_id": "uuid",
    #         "source_file": "document.pdf",
    #         "page": 5,
    #         "chunk_index": 3,
    #         "text_snippet": "relevant text...",
    #         "relevance_score": 0.95
    #     }
    # ]

    # Processing metadata
    retrieval_time_ms = models.IntegerField(null=True, blank=True)
    generation_time_ms = models.IntegerField(null=True, blank=True)
    total_tokens_used = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['grounding_score']),
        ]

    def __str__(self):
        return f"RAG Response for: {self.search_query.query_text[:50]}..."
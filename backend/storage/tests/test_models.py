"""
Django Tests for Storage Models.
Test all model methods, properties, and validations.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from storage.models import (
    FileSearchStore, MediaFile, DocumentChunk,
    SearchQuery, RAGResponse, UploadBatch, JSONDataStore
)
import uuid


class FileSearchStoreModelTest(TestCase):
    """Test FileSearchStore model."""

    def setUp(self):
        """Set up test data."""
        self.store = FileSearchStore.objects.create(
            name='test-store',
            display_name='Test Store',
            description='Test store for unit tests',
            chunking_strategy='auto',
            max_tokens_per_chunk=512,
            max_overlap_tokens=50,
            storage_quota=1073741824,  # 1GB
        )

    def test_store_creation(self):
        """Test store creation and default values."""
        self.assertEqual(self.store.name, 'test-store')
        self.assertEqual(self.store.display_name, 'Test Store')
        self.assertTrue(isinstance(self.store.store_id, uuid.UUID))
        self.assertTrue(self.store.is_active)
        self.assertEqual(self.store.total_files, 0)
        self.assertEqual(self.store.total_chunks, 0)

    def test_storage_used_percentage(self):
        """Test storage usage percentage calculation."""
        # Empty store
        self.assertEqual(self.store.storage_used_percentage, 0.0)

        # Add some usage
        self.store.storage_size_bytes = 536870912  # 512MB
        self.store.save()
        self.assertAlmostEqual(self.store.storage_used_percentage, 50.0, places=1)

    def test_is_quota_exceeded(self):
        """Test quota exceeded check."""
        # Not exceeded
        self.assertFalse(self.store.is_quota_exceeded())

        # Exceeded
        self.store.storage_size_bytes = 1073741824 + 1  # 1GB + 1 byte
        self.store.save()
        self.assertTrue(self.store.is_quota_exceeded())

    def test_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.store), 'Test Store')


class MediaFileModelTest(TestCase):
    """Test MediaFile model."""

    def setUp(self):
        """Set up test data."""
        self.store = FileSearchStore.objects.create(
            name='test-store',
            display_name='Test Store',
        )

        self.media_file = MediaFile.objects.create(
            original_name='test_document.pdf',
            file_path='/media/test_document.pdf',
            file_size=1024000,
            detected_type='document',
            mime_type='application/pdf',
            file_search_store=self.store,
        )

    def test_file_creation(self):
        """Test file creation and defaults."""
        self.assertEqual(self.media_file.original_name, 'test_document.pdf')
        self.assertEqual(self.media_file.detected_type, 'document')
        self.assertFalse(self.media_file.is_indexed)
        self.assertTrue(isinstance(self.media_file.file_id, uuid.UUID))

    def test_file_size_display(self):
        """Test file size display formatting (if implemented)."""
        # Would test custom property if added
        pass

    def test_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.media_file), 'test_document.pdf')


class DocumentChunkModelTest(TestCase):
    """Test DocumentChunk model."""

    def setUp(self):
        """Set up test data."""
        self.store = FileSearchStore.objects.create(
            name='test-store',
            display_name='Test Store',
        )

        self.media_file = MediaFile.objects.create(
            original_name='test.txt',
            file_path='/media/test.txt',
            file_size=1000,
            file_search_store=self.store,
        )

        self.chunk = DocumentChunk.objects.create(
            media_file=self.media_file,
            file_search_store=self.store,
            chunk_index=0,
            chunk_text='This is a test chunk of text.',
            token_count=7,
            chunking_strategy='auto',
        )

    def test_chunk_creation(self):
        """Test chunk creation."""
        self.assertEqual(self.chunk.chunk_index, 0)
        self.assertEqual(self.chunk.token_count, 7)
        self.assertEqual(self.chunk.chunking_strategy, 'auto')
        self.assertTrue(isinstance(self.chunk.chunk_id, uuid.UUID))
        self.assertTrue(isinstance(self.chunk.citation_id, uuid.UUID))

    def test_str_representation(self):
        """Test string representation."""
        expected = f'Chunk 0 of test.txt'
        self.assertEqual(str(self.chunk), expected)


class SearchQueryModelTest(TestCase):
    """Test SearchQuery model."""

    def setUp(self):
        """Set up test data."""
        self.query = SearchQuery.objects.create(
            query_text='machine learning algorithms',
            results_count=10,
        )

    def test_query_creation(self):
        """Test query creation."""
        self.assertEqual(self.query.query_text, 'machine learning algorithms')
        self.assertEqual(self.query.results_count, 10)
        self.assertTrue(isinstance(self.query.query_id, uuid.UUID))

    def test_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.query), 'machine learning algorithms')


class RAGResponseModelTest(TestCase):
    """Test RAGResponse model."""

    def setUp(self):
        """Set up test data."""
        self.query = SearchQuery.objects.create(
            query_text='test query',
            results_count=5,
        )

        self.response = RAGResponse.objects.create(
            search_query=self.query,
            response_text='This is a test response.',
            grounding_score=0.85,
            processing_time=1.5,
        )

    def test_response_creation(self):
        """Test response creation."""
        self.assertEqual(self.response.response_text, 'This is a test response.')
        self.assertAlmostEqual(self.response.grounding_score, 0.85)
        self.assertEqual(self.response.processing_time, 1.5)

    def test_str_representation(self):
        """Test string representation."""
        expected = f'Response to: test query'
        self.assertEqual(str(self.response), expected)


class UploadBatchModelTest(TestCase):
    """Test UploadBatch model."""

    def setUp(self):
        """Set up test data."""
        self.batch = UploadBatch.objects.create(
            total_files=10,
            processed_files=5,
            failed_files=0,
        )

    def test_batch_creation(self):
        """Test batch creation."""
        self.assertEqual(self.batch.total_files, 10)
        self.assertEqual(self.batch.processed_files, 5)
        self.assertEqual(self.batch.status, 'processing')
        self.assertTrue(isinstance(self.batch.batch_id, uuid.UUID))

    def test_str_representation(self):
        """Test string representation."""
        self.assertTrue(str(self.batch).startswith('Batch'))


class JSONDataStoreModelTest(TestCase):
    """Test JSONDataStore model."""

    def setUp(self):
        """Set up test data."""
        self.json_store = JSONDataStore.objects.create(
            name='test-json',
            description='Test JSON data',
            json_data={'key': 'value', 'items': [1, 2, 3]},
            recommended_db_type='NoSQL',
        )

    def test_json_store_creation(self):
        """Test JSON store creation."""
        self.assertEqual(self.json_store.name, 'test-json')
        self.assertEqual(self.json_store.recommended_db_type, 'NoSQL')
        self.assertIsInstance(self.json_store.json_data, dict)
        self.assertEqual(self.json_store.json_data['key'], 'value')

    def test_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.json_store), 'test-json')

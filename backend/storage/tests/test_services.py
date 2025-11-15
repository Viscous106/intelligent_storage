"""
Django Tests for Storage Services.
Test chunking, embeddings, and other services.
"""

from django.test import TestCase
from storage.chunking_service import ChunkingService
import tempfile
import os


class ChunkingServiceTest(TestCase):
    """Test ChunkingService functionality."""

    def setUp(self):
        """Set up test data."""
        self.service = ChunkingService(
            strategy='auto',
            max_tokens_per_chunk=100,
            max_overlap_tokens=10
        )

    def test_whitespace_chunking(self):
        """Test whitespace-based chunking."""
        text = "This is sentence one. " * 50  # Long text

        chunks = self.service._whitespace_chunk(text)

        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

        # Each chunk should not be empty
        for chunk in chunks:
            self.assertTrue(chunk.strip())

    def test_semantic_chunking(self):
        """Test semantic chunking."""
        text = """
        # Introduction
        This is the introduction paragraph.

        # Main Content
        This is the main content paragraph.

        # Conclusion
        This is the conclusion paragraph.
        """

        chunks = self.service._semantic_chunk(text)

        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_fixed_chunking(self):
        """Test fixed-size chunking with overlap."""
        text = "word " * 200  # 200 words

        chunks = self.service._fixed_chunk(text)

        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 1)

        # Check overlap
        if len(chunks) > 1:
            # There should be some overlap between chunks
            chunk1_end = chunks[0].split()[-5:]
            chunk2_start = chunks[1].split()[:5]
            # Some words should overlap
            overlap = set(chunk1_end) & set(chunk2_start)
            self.assertGreater(len(overlap), 0)

    def test_auto_chunking_selection(self):
        """Test auto strategy selection."""
        # Text with clear sections should use semantic
        text_with_sections = """
        # Section 1
        Content here.

        # Section 2
        More content.
        """

        chunks = self.service._auto_chunk(text_with_sections)
        self.assertGreater(len(chunks), 0)

        # Plain text should use whitespace
        plain_text = "This is plain text. " * 50

        chunks = self.service._auto_chunk(plain_text)
        self.assertGreater(len(chunks), 0)

    def test_chunk_text_file(self):
        """Test chunking a text file."""
        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document. " * 100)
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                content = f.read()

            chunks = self.service.chunk_file(content, 'document')

            self.assertIsInstance(chunks, list)
            self.assertGreater(len(chunks), 0)

        finally:
            os.unlink(temp_path)

    def test_count_tokens(self):
        """Test token counting."""
        text = "This is a simple test sentence."

        token_count = self.service._count_tokens(text)

        # Should be approximately 6-7 tokens
        self.assertGreater(token_count, 0)
        self.assertLess(token_count, 20)

    def test_extract_text_from_pdf(self):
        """Test PDF text extraction (requires PDF library)."""
        # This would require a sample PDF file
        # Placeholder test
        pass

    def test_extract_text_from_docx(self):
        """Test DOCX text extraction."""
        # This would require a sample DOCX file
        # Placeholder test
        pass


class EmbeddingsServiceTest(TestCase):
    """Test EmbeddingsService functionality."""

    def setUp(self):
        """Set up test data."""
        # Only import if we're actually testing
        # from storage.embeddings_service import EmbeddingsService
        # self.service = EmbeddingsService()
        pass

    def test_generate_embedding(self):
        """Test embedding generation."""
        # This requires Ollama to be running
        # Placeholder test
        pass

    def test_batch_embeddings(self):
        """Test batch embedding generation."""
        # Placeholder test
        pass

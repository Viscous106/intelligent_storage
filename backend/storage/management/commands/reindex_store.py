"""
Django Management Command: Reindex File Search Store
Reindex all files in a specific store or all stores.
Cross-platform compatible (Windows + Linux).
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import logging
import os

from storage.models import FileSearchStore, MediaFile, DocumentChunk
from storage.chunking_service import ChunkingService
from storage.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reindex files in a File Search Store'

    def add_arguments(self, parser):
        parser.add_argument(
            '--store',
            type=str,
            help='Store name or ID to reindex (leave empty for all stores)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reindexing even for already indexed files',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing chunks before reindexing',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of files to process in each batch (default: 10)',
        )

    def handle(self, *args, **options):
        store_identifier = options['store']
        force = options['force']
        clear_existing = options['clear_existing']
        batch_size = options['batch_size']

        # Get stores to reindex
        if store_identifier:
            try:
                # Try by name first
                stores = FileSearchStore.objects.filter(name=store_identifier)
                if not stores.exists():
                    # Try by ID
                    stores = FileSearchStore.objects.filter(store_id=store_identifier)

                if not stores.exists():
                    raise CommandError(f'Store not found: {store_identifier}')
            except Exception as e:
                raise CommandError(f'Error finding store: {str(e)}')
        else:
            stores = FileSearchStore.objects.filter(is_active=True)

        self.stdout.write(self.style.SUCCESS(
            f'Reindexing {stores.count()} store(s)...'
        ))

        # Initialize services
        chunking_service = ChunkingService()
        embeddings_service = EmbeddingsService()

        # Process each store
        total_files_processed = 0
        total_chunks_created = 0
        total_errors = 0

        for store in stores:
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.WARNING(
                f'Processing Store: {store.display_name} ({store.name})'
            ))
            self.stdout.write('=' * 70)

            # Get files to index
            if force:
                files_to_index = MediaFile.objects.filter(file_search_store=store)
            else:
                files_to_index = MediaFile.objects.filter(
                    file_search_store=store,
                    is_indexed=False
                )

            file_count = files_to_index.count()
            self.stdout.write(f'Files to process: {file_count}')

            if file_count == 0:
                self.stdout.write(self.style.WARNING('No files to process'))
                continue

            # Clear existing chunks if requested
            if clear_existing:
                chunks_deleted = DocumentChunk.objects.filter(file_search_store=store).count()
                DocumentChunk.objects.filter(file_search_store=store).delete()
                self.stdout.write(self.style.WARNING(
                    f'Cleared {chunks_deleted} existing chunk(s)'
                ))

            # Process files in batches
            for i in range(0, file_count, batch_size):
                batch = files_to_index[i:i+batch_size]

                self.stdout.write(f'\nBatch {i//batch_size + 1}: Processing {len(batch)} file(s)...')

                for media_file in batch:
                    try:
                        self._index_file(
                            media_file,
                            store,
                            chunking_service,
                            embeddings_service,
                            clear_existing
                        )
                        total_files_processed += 1

                        # Count chunks for this file
                        chunk_count = DocumentChunk.objects.filter(media_file=media_file).count()
                        total_chunks_created += chunk_count

                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ {media_file.original_name} ({chunk_count} chunks)'
                        ))

                    except Exception as e:
                        total_errors += 1
                        self.stdout.write(self.style.ERROR(
                            f'  ✗ {media_file.original_name}: {str(e)}'
                        ))
                        logger.error(f'Failed to index {media_file.id}: {str(e)}', exc_info=True)

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('REINDEXING SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Stores processed: {stores.count()}')
        self.stdout.write(f'Files processed: {total_files_processed}')
        self.stdout.write(f'Chunks created: {total_chunks_created}')

        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {total_errors}'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ No errors'))

        logger.info(
            f'Reindexing completed - Files: {total_files_processed}, '
            f'Chunks: {total_chunks_created}, Errors: {total_errors}'
        )

    def _index_file(self, media_file, store, chunking_service, embeddings_service, clear_existing):
        """Index a single file."""

        # Delete existing chunks for this file if requested
        if clear_existing:
            DocumentChunk.objects.filter(media_file=media_file).delete()

        # Read file content
        if not media_file.file_path or not os.path.exists(media_file.file_path):
            raise Exception('File path does not exist')

        with open(media_file.file_path, 'rb') as f:
            content = f.read()

        # Extract text based on file type
        chunking_service.strategy = store.chunking_strategy
        chunking_service.max_tokens_per_chunk = store.max_tokens_per_chunk
        chunking_service.max_overlap_tokens = store.max_overlap_tokens

        # Process file
        chunks = chunking_service.chunk_file(content, media_file.detected_type)

        # Create chunks with embeddings
        with transaction.atomic():
            for idx, chunk_text in enumerate(chunks):
                # Generate embedding
                embedding = embeddings_service.generate_embedding(chunk_text)

                # Create chunk
                DocumentChunk.objects.create(
                    media_file=media_file,
                    file_search_store=store,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    embedding=embedding,
                    token_count=len(chunk_text.split()),  # Approximation
                    chunking_strategy=store.chunking_strategy,
                    metadata={
                        'original_filename': media_file.original_name,
                        'file_type': media_file.detected_type,
                    }
                )

            # Mark file as indexed
            media_file.is_indexed = True
            media_file.save(update_fields=['is_indexed'])

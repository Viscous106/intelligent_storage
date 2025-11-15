"""
Django Management Command: Export File Search Store
Export store configuration and data to JSON file.
Cross-platform compatible (Windows + Linux).
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers import serialize
from django.utils import timezone
import json
import os
from pathlib import Path
import logging

from storage.models import FileSearchStore, MediaFile, DocumentChunk

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Export File Search Store configuration and data'

    def add_arguments(self, parser):
        parser.add_argument(
            'store',
            type=str,
            help='Store name or ID to export',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: exports/store_<name>_<timestamp>.json)',
        )
        parser.add_argument(
            '--include-files',
            action='store_true',
            help='Include file metadata',
        )
        parser.add_argument(
            '--include-chunks',
            action='store_true',
            help='Include chunk data',
        )
        parser.add_argument(
            '--include-embeddings',
            action='store_true',
            help='Include embeddings (warning: large file size)',
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty print JSON output',
        )

    def handle(self, *args, **options):
        store_identifier = options['store']
        output_path = options['output']
        include_files = options['include_files']
        include_chunks = options['include_chunks']
        include_embeddings = options['include_embeddings']
        pretty = options['pretty']

        # Find store
        try:
            store = FileSearchStore.objects.filter(name=store_identifier).first()
            if not store:
                store = FileSearchStore.objects.filter(store_id=store_identifier).first()

            if not store:
                raise CommandError(f'Store not found: {store_identifier}')
        except Exception as e:
            raise CommandError(f'Error finding store: {str(e)}')

        self.stdout.write(self.style.SUCCESS(
            f'Exporting store: {store.display_name} ({store.name})'
        ))

        # Prepare export data
        export_data = {
            'export_metadata': {
                'exported_at': timezone.now().isoformat(),
                'version': '1.0',
                'includes': {
                    'files': include_files,
                    'chunks': include_chunks,
                    'embeddings': include_embeddings,
                }
            },
            'store': {
                'store_id': str(store.store_id),
                'name': store.name,
                'display_name': store.display_name,
                'description': store.description,
                'chunking_strategy': store.chunking_strategy,
                'max_tokens_per_chunk': store.max_tokens_per_chunk,
                'max_overlap_tokens': store.max_overlap_tokens,
                'storage_quota': store.storage_quota,
                'custom_metadata': store.custom_metadata,
                'is_active': store.is_active,
                'created_at': store.created_at.isoformat(),
                'statistics': {
                    'total_files': store.total_files,
                    'total_chunks': store.total_chunks,
                    'storage_size_bytes': store.storage_size_bytes,
                    'embeddings_size_bytes': store.embeddings_size_bytes,
                    'storage_used_percentage': store.storage_used_percentage,
                }
            }
        }

        # Include files
        if include_files:
            self.stdout.write('Including file metadata...')
            files_data = []

            for media_file in MediaFile.objects.filter(file_search_store=store):
                file_data = {
                    'id': media_file.id,
                    'original_name': media_file.original_name,
                    'file_size': media_file.file_size,
                    'detected_type': media_file.detected_type,
                    'mime_type': media_file.mime_type,
                    'is_indexed': media_file.is_indexed,
                    'custom_metadata': media_file.custom_metadata,
                    'user_comment': media_file.user_comment,
                    'uploaded_at': media_file.uploaded_at.isoformat(),
                }
                files_data.append(file_data)

            export_data['files'] = files_data
            export_data['files_count'] = len(files_data)

        # Include chunks
        if include_chunks:
            self.stdout.write('Including chunk data...')
            chunks_data = []

            for chunk in DocumentChunk.objects.filter(file_search_store=store):
                chunk_data = {
                    'chunk_id': str(chunk.chunk_id),
                    'citation_id': str(chunk.citation_id),
                    'chunk_index': chunk.chunk_index,
                    'chunk_text': chunk.chunk_text,
                    'token_count': chunk.token_count,
                    'chunking_strategy': chunk.chunking_strategy,
                    'metadata': chunk.metadata,
                    'page_number': chunk.page_number,
                    'media_file_id': chunk.media_file_id,
                }

                # Include embedding if requested
                if include_embeddings and chunk.embedding:
                    chunk_data['embedding'] = chunk.embedding

                chunks_data.append(chunk_data)

            export_data['chunks'] = chunks_data
            export_data['chunks_count'] = len(chunks_data)

        # Determine output path
        if not output_path:
            exports_dir = Path('exports')
            exports_dir.mkdir(exist_ok=True)

            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            output_path = exports_dir / f'store_{store.name}_{timestamp}.json'
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        self.stdout.write(f'Writing to: {output_path}')

        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(export_data, f, ensure_ascii=False)

        # Summary
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('EXPORT SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Store: {store.display_name}')
        self.stdout.write(f'Output: {output_path}')
        self.stdout.write(f'File Size: {file_size_mb:.2f} MB')

        if include_files:
            self.stdout.write(f'Files Exported: {export_data["files_count"]}')
        if include_chunks:
            self.stdout.write(f'Chunks Exported: {export_data["chunks_count"]}')

        self.stdout.write(self.style.SUCCESS('\n✓ Export completed successfully'))

        logger.info(f'Store exported: {store.name} to {output_path}')

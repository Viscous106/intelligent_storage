"""
Django Management Command: Import File Search Store
Import store configuration and data from JSON file.
Cross-platform compatible (Windows + Linux).
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import json
from pathlib import Path
import logging

from storage.models import FileSearchStore, MediaFile, DocumentChunk

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import File Search Store configuration and data from JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            'input_file',
            type=str,
            help='Path to JSON export file',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip if store with same name already exists',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing store (WARNING: destructive)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        input_file = Path(options['input_file'])
        skip_existing = options['skip_existing']
        overwrite = options['overwrite']
        dry_run = options['dry_run']

        # Validate input file
        if not input_file.exists():
            raise CommandError(f'Input file not found: {input_file}')

        # Read JSON
        self.stdout.write(f'Reading from: {input_file}')

        with open(input_file, 'r', encoding='utf-8') as f:
            import_data = json.load(f)

        # Validate structure
        if 'store' not in import_data:
            raise CommandError('Invalid export file: missing "store" key')

        store_data = import_data['store']
        store_name = store_data['name']

        # Check if store exists
        existing_store = FileSearchStore.objects.filter(name=store_name).first()

        if existing_store:
            if skip_existing:
                self.stdout.write(self.style.WARNING(
                    f'Store "{store_name}" already exists. Skipping.'
                ))
                return
            elif not overwrite:
                raise CommandError(
                    f'Store "{store_name}" already exists. Use --overwrite to replace or --skip-existing to skip.'
                )

        # Preview
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.WARNING('IMPORT PREVIEW'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Store Name: {store_data["display_name"]} ({store_data["name"]})')
        self.stdout.write(f'Store ID: {store_data["store_id"]}')
        self.stdout.write(f'Chunking Strategy: {store_data["chunking_strategy"]}')
        self.stdout.write(f'Files: {import_data.get("files_count", 0)}')
        self.stdout.write(f'Chunks: {import_data.get("chunks_count", 0)}')

        if existing_store:
            self.stdout.write(self.style.ERROR('\n⚠ WARNING: This will DELETE the existing store and all its data!'))

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - Nothing will be imported'))
            return

        # Confirm
        self.stdout.write('')
        confirm = input('Continue with import? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Import cancelled'))
            return

        # Import
        try:
            with transaction.atomic():
                # Delete existing if overwriting
                if existing_store and overwrite:
                    self.stdout.write('Deleting existing store...')
                    existing_store.delete()

                # Create store
                self.stdout.write('Creating store...')
                store = FileSearchStore.objects.create(
                    name=store_data['name'],
                    display_name=store_data['display_name'],
                    description=store_data.get('description', ''),
                    chunking_strategy=store_data['chunking_strategy'],
                    max_tokens_per_chunk=store_data['max_tokens_per_chunk'],
                    max_overlap_tokens=store_data['max_overlap_tokens'],
                    storage_quota=store_data['storage_quota'],
                    custom_metadata=store_data.get('custom_metadata', {}),
                    is_active=store_data.get('is_active', True),
                )

                # Import files (metadata only)
                if 'files' in import_data:
                    self.stdout.write(f'Importing {len(import_data["files"])} file records...')

                    for file_data in import_data['files']:
                        # Note: Physical files are not imported, only metadata
                        MediaFile.objects.create(
                            file_search_store=store,
                            original_name=file_data['original_name'],
                            file_size=file_data['file_size'],
                            detected_type=file_data['detected_type'],
                            mime_type=file_data['mime_type'],
                            is_indexed=False,  # Will need reindexing
                            custom_metadata=file_data.get('custom_metadata', {}),
                            user_comment=file_data.get('user_comment', ''),
                            file_path='',  # Physical file not imported
                        )

                # Import chunks
                if 'chunks' in import_data:
                    self.stdout.write(f'Importing {len(import_data["chunks"])} chunks...')

                    chunk_count = 0
                    for chunk_data in import_data['chunks']:
                        # Find corresponding media file
                        media_file_id = chunk_data.get('media_file_id')
                        media_file = None

                        if media_file_id:
                            # This will only work if file IDs are preserved
                            media_file = MediaFile.objects.filter(
                                id=media_file_id,
                                file_search_store=store
                            ).first()

                        DocumentChunk.objects.create(
                            file_search_store=store,
                            media_file=media_file,
                            chunk_index=chunk_data['chunk_index'],
                            chunk_text=chunk_data['chunk_text'],
                            token_count=chunk_data['token_count'],
                            chunking_strategy=chunk_data['chunking_strategy'],
                            metadata=chunk_data.get('metadata', {}),
                            page_number=chunk_data.get('page_number'),
                            embedding=chunk_data.get('embedding'),  # May be None
                        )
                        chunk_count += 1

                self.stdout.write(self.style.SUCCESS('\n✓ Import completed successfully'))

        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Store: {store.display_name}')
        self.stdout.write(f'Files Imported: {import_data.get("files_count", 0)}')
        self.stdout.write(f'Chunks Imported: {import_data.get("chunks_count", 0)}')

        if 'files' in import_data and not 'chunks' in import_data:
            self.stdout.write(self.style.WARNING(
                '\n⚠ Note: Physical files were not imported. '
                'You will need to re-upload and reindex files.'
            ))

        logger.info(f'Store imported: {store.name} from {input_file}')

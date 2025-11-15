"""
Django Management Command: Sync Storage Statistics
Synchronize and recalculate storage statistics for all stores.
Cross-platform compatible (Windows + Linux).
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
import logging

from storage.models import FileSearchStore, MediaFile, DocumentChunk

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Synchronize storage statistics for all File Search Stores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--store',
            type=str,
            help='Sync specific store only',
        )
        parser.add_argument(
            '--fix-discrepancies',
            action='store_true',
            help='Fix any discrepancies found',
        )

    def handle(self, *args, **options):
        store_filter = options['store']
        fix_discrepancies = options['fix_discrepancies']

        # Get stores
        if store_filter:
            stores = FileSearchStore.objects.filter(name=store_filter)
            if not stores.exists():
                stores = FileSearchStore.objects.filter(store_id=store_filter)
        else:
            stores = FileSearchStore.objects.all()

        self.stdout.write(self.style.SUCCESS(
            f'Syncing statistics for {stores.count()} store(s)...'
        ))

        total_discrepancies = 0
        total_fixed = 0

        for store in stores:
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.WARNING(
                f'Store: {store.display_name} ({store.name})'
            ))
            self.stdout.write('=' * 70)

            discrepancies = []

            # Check file count
            actual_file_count = MediaFile.objects.filter(file_search_store=store).count()
            if store.total_files != actual_file_count:
                discrepancies.append({
                    'field': 'total_files',
                    'stored': store.total_files,
                    'actual': actual_file_count,
                })

            # Check chunk count
            actual_chunk_count = DocumentChunk.objects.filter(file_search_store=store).count()
            if store.total_chunks != actual_chunk_count:
                discrepancies.append({
                    'field': 'total_chunks',
                    'stored': store.total_chunks,
                    'actual': actual_chunk_count,
                })

            # Check storage size
            actual_storage_size = MediaFile.objects.filter(
                file_search_store=store
            ).aggregate(
                total=Sum('file_size')
            )['total'] or 0

            if store.storage_size_bytes != actual_storage_size:
                discrepancies.append({
                    'field': 'storage_size_bytes',
                    'stored': store.storage_size_bytes,
                    'actual': actual_storage_size,
                })

            # Check indexed files
            indexed_count = MediaFile.objects.filter(
                file_search_store=store,
                is_indexed=True
            ).count()

            # Estimate embeddings size (3x file size for indexed files)
            actual_embeddings_size = MediaFile.objects.filter(
                file_search_store=store,
                is_indexed=True
            ).aggregate(
                total=Sum('file_size')
            )['total'] or 0
            actual_embeddings_size *= 3

            if abs(store.embeddings_size_bytes - actual_embeddings_size) > 1024:  # 1KB tolerance
                discrepancies.append({
                    'field': 'embeddings_size_bytes',
                    'stored': store.embeddings_size_bytes,
                    'actual': actual_embeddings_size,
                })

            # Report discrepancies
            if discrepancies:
                total_discrepancies += len(discrepancies)

                self.stdout.write(self.style.ERROR(
                    f'\n⚠ Found {len(discrepancies)} discrepanc{"y" if len(discrepancies) == 1 else "ies"}:'
                ))

                for disc in discrepancies:
                    stored_val = self._format_value(disc['field'], disc['stored'])
                    actual_val = self._format_value(disc['field'], disc['actual'])

                    self.stdout.write(
                        f'  • {disc["field"]}: '
                        f'Stored={stored_val}, Actual={actual_val}'
                    )

                # Fix if requested
                if fix_discrepancies:
                    store.total_files = actual_file_count
                    store.total_chunks = actual_chunk_count
                    store.storage_size_bytes = actual_storage_size
                    store.embeddings_size_bytes = actual_embeddings_size
                    store.save()

                    total_fixed += len(discrepancies)
                    self.stdout.write(self.style.SUCCESS('  ✓ Fixed'))
            else:
                self.stdout.write(self.style.SUCCESS('\n✓ All statistics are accurate'))

            # Display current statistics
            self.stdout.write('\nCurrent Statistics:')
            self.stdout.write(f'  Files: {actual_file_count} (Indexed: {indexed_count})')
            self.stdout.write(f'  Chunks: {actual_chunk_count}')
            self.stdout.write(f'  Storage: {actual_storage_size / (1024*1024):.2f} MB')
            self.stdout.write(f'  Embeddings: {actual_embeddings_size / (1024*1024):.2f} MB')
            self.stdout.write(f'  Total: {(actual_storage_size + actual_embeddings_size) / (1024*1024):.2f} MB')
            self.stdout.write(f'  Usage: {store.storage_used_percentage:.1f}%')

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('SYNC SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Stores Processed: {stores.count()}')
        self.stdout.write(f'Discrepancies Found: {total_discrepancies}')

        if fix_discrepancies:
            self.stdout.write(self.style.SUCCESS(f'Discrepancies Fixed: {total_fixed}'))
        elif total_discrepancies > 0:
            self.stdout.write(self.style.WARNING(
                '\nRun with --fix-discrepancies to fix these issues'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All statistics are accurate'))

        logger.info(
            f'Statistics sync completed - Stores: {stores.count()}, '
            f'Discrepancies: {total_discrepancies}, Fixed: {total_fixed}'
        )

    def _format_value(self, field_name, value):
        """Format value based on field type."""
        if 'bytes' in field_name:
            return f'{value / (1024*1024):.2f} MB'
        else:
            return str(value)

"""
Django Management Command: Cleanup Orphaned Files
Removes physical files without database records and vice versa.
Cross-platform compatible (Windows + Linux).
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
from pathlib import Path
import logging

from storage.models import MediaFile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up orphaned files (files without DB records or DB records without files)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--delete-db-orphans',
            action='store_true',
            help='Delete database records without physical files',
        )
        parser.add_argument(
            '--delete-file-orphans',
            action='store_true',
            help='Delete physical files without database records',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clean up both types of orphans',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_db = options['delete_db_orphans'] or options['all']
        delete_files = options['delete_file_orphans'] or options['all']

        if not delete_db and not delete_files:
            raise CommandError('Please specify --delete-db-orphans, --delete-file-orphans, or --all')

        self.stdout.write(self.style.WARNING(
            f'Running cleanup (DRY RUN: {dry_run})'
        ))

        # Track statistics
        db_orphans_count = 0
        file_orphans_count = 0

        # 1. Find DB records without physical files
        if delete_db:
            self.stdout.write('\n=== Checking for database orphans ===')

            all_files = MediaFile.objects.all()
            for media_file in all_files:
                if media_file.file_path and not os.path.exists(media_file.file_path):
                    db_orphans_count += 1
                    self.stdout.write(self.style.ERROR(
                        f'DB Orphan: {media_file.original_name} (ID: {media_file.id}) - '
                        f'File not found: {media_file.file_path}'
                    ))

                    if not dry_run:
                        media_file.delete()
                        self.stdout.write(self.style.SUCCESS('  ✓ Deleted from database'))

            self.stdout.write(f'\nFound {db_orphans_count} database orphan(s)')

        # 2. Find physical files without DB records
        if delete_files:
            self.stdout.write('\n=== Checking for file orphans ===')

            # Get media root (cross-platform)
            media_root = Path(settings.MEDIA_ROOT) if hasattr(settings, 'MEDIA_ROOT') else Path('media')

            if not media_root.exists():
                self.stdout.write(self.style.WARNING(
                    f'Media root does not exist: {media_root}'
                ))
            else:
                # Get all file paths from DB
                db_file_paths = set(
                    MediaFile.objects.exclude(file_path__isnull=True)
                    .exclude(file_path='')
                    .values_list('file_path', flat=True)
                )

                # Walk through media directory (cross-platform)
                for root, dirs, files in os.walk(media_root):
                    for filename in files:
                        file_path = os.path.join(root, filename)

                        # Skip hidden files and system files
                        if filename.startswith('.') or filename.startswith('__'):
                            continue

                        if file_path not in db_file_paths:
                            file_orphans_count += 1
                            self.stdout.write(self.style.ERROR(
                                f'File Orphan: {file_path}'
                            ))

                            if not dry_run:
                                try:
                                    os.remove(file_path)
                                    self.stdout.write(self.style.SUCCESS('  ✓ Deleted file'))
                                except Exception as e:
                                    self.stdout.write(self.style.ERROR(f'  ✗ Failed to delete: {str(e)}'))

                self.stdout.write(f'\nFound {file_orphans_count} file orphan(s)')

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('CLEANUP SUMMARY'))
        self.stdout.write('=' * 50)

        if delete_db:
            self.stdout.write(f'Database orphans: {db_orphans_count}')
        if delete_files:
            self.stdout.write(f'File orphans: {file_orphans_count}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nDRY RUN - Nothing was deleted. Remove --dry-run to actually delete.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Cleanup completed'))

        logger.info(
            f'Cleanup completed - DB orphans: {db_orphans_count}, '
            f'File orphans: {file_orphans_count}, Dry run: {dry_run}'
        )

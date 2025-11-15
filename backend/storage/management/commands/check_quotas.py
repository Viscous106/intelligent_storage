"""
Django Management Command: Check Storage Quotas
Check and report storage quota usage for all stores.
Cross-platform compatible (Windows + Linux).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

from storage.models import FileSearchStore, MediaFile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check storage quotas for all File Search Stores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--warning-threshold',
            type=float,
            default=70.0,
            help='Warning threshold percentage (default: 70%%)',
        )
        parser.add_argument(
            '--critical-threshold',
            type=float,
            default=90.0,
            help='Critical threshold percentage (default: 90%%)',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format',
        )
        parser.add_argument(
            '--store',
            type=str,
            help='Check specific store only',
        )

    def handle(self, *args, **options):
        warning_threshold = options['warning_threshold']
        critical_threshold = options['critical_threshold']
        json_output = options['json']
        store_filter = options['store']

        # Get stores
        if store_filter:
            stores = FileSearchStore.objects.filter(name=store_filter)
            if not stores.exists():
                stores = FileSearchStore.objects.filter(store_id=store_filter)
        else:
            stores = FileSearchStore.objects.all()

        if not stores.exists():
            self.stdout.write(self.style.ERROR('No stores found'))
            return

        # Collect results
        results = []
        warning_stores = []
        critical_stores = []
        exceeded_stores = []

        for store in stores:
            usage_pct = store.storage_used_percentage

            result = {
                'name': store.name,
                'display_name': store.display_name,
                'store_id': str(store.store_id),
                'total_files': store.total_files,
                'total_chunks': store.total_chunks,
                'storage_used_bytes': store.storage_size_bytes,
                'embeddings_used_bytes': store.embeddings_size_bytes,
                'total_used_bytes': store.storage_size_bytes + store.embeddings_size_bytes,
                'quota_bytes': store.storage_quota,
                'usage_percentage': round(usage_pct, 2),
                'status': self._get_status(usage_pct, warning_threshold, critical_threshold),
                'is_active': store.is_active,
            }

            results.append(result)

            # Categorize
            if store.is_quota_exceeded():
                exceeded_stores.append(store)
            elif usage_pct >= critical_threshold:
                critical_stores.append(store)
            elif usage_pct >= warning_threshold:
                warning_stores.append(store)

        # Output
        if json_output:
            import json
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self._print_report(
                results,
                warning_stores,
                critical_stores,
                exceeded_stores,
                warning_threshold,
                critical_threshold
            )

        logger.info(f'Quota check completed - Total stores: {len(results)}')

    def _get_status(self, usage_pct, warning_threshold, critical_threshold):
        """Get status based on usage percentage."""
        if usage_pct >= 100:
            return 'EXCEEDED'
        elif usage_pct >= critical_threshold:
            return 'CRITICAL'
        elif usage_pct >= warning_threshold:
            return 'WARNING'
        else:
            return 'OK'

    def _print_report(self, results, warning_stores, critical_stores, exceeded_stores,
                     warning_threshold, critical_threshold):
        """Print formatted report."""

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('STORAGE QUOTA REPORT'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Total Stores: {len(results)}')
        self.stdout.write('')

        # Summary
        self.stdout.write(self.style.WARNING('SUMMARY:'))
        self.stdout.write(f'  ✓ OK: {len([r for r in results if r["status"] == "OK"])}')
        self.stdout.write(self.style.WARNING(
            f'  ⚠ Warning ({warning_threshold}%+): {len(warning_stores)}'
        ))
        self.stdout.write(self.style.ERROR(
            f'  ⚠⚠ Critical ({critical_threshold}%+): {len(critical_stores)}'
        ))
        self.stdout.write(self.style.ERROR(
            f'  ✗ Exceeded (100%+): {len(exceeded_stores)}'
        ))

        # Detailed results
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('DETAILED RESULTS:')
        self.stdout.write('=' * 80)

        for result in results:
            self._print_store_details(result, warning_threshold, critical_threshold)

        # Alerts
        if exceeded_stores or critical_stores:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.ERROR('⚠ ALERTS'))
            self.stdout.write('=' * 80)

            if exceeded_stores:
                self.stdout.write(self.style.ERROR('\n✗ QUOTA EXCEEDED:'))
                for store in exceeded_stores:
                    self.stdout.write(
                        f'  • {store.display_name} ({store.name}): '
                        f'{store.storage_used_percentage:.1f}%'
                    )

            if critical_stores:
                self.stdout.write(self.style.ERROR('\n⚠⚠ CRITICAL USAGE:'))
                for store in critical_stores:
                    self.stdout.write(
                        f'  • {store.display_name} ({store.name}): '
                        f'{store.storage_used_percentage:.1f}%'
                    )

    def _print_store_details(self, result, warning_threshold, critical_threshold):
        """Print details for a single store."""

        # Status styling
        status = result['status']
        if status == 'EXCEEDED':
            status_style = self.style.ERROR
            status_icon = '✗'
        elif status == 'CRITICAL':
            status_style = self.style.ERROR
            status_icon = '⚠⚠'
        elif status == 'WARNING':
            status_style = self.style.WARNING
            status_icon = '⚠'
        else:
            status_style = self.style.SUCCESS
            status_icon = '✓'

        self.stdout.write('\n' + '-' * 80)
        self.stdout.write(status_style(
            f'{status_icon} {result["display_name"]} ({result["name"]}) - {status}'
        ))
        self.stdout.write('-' * 80)

        self.stdout.write(f'Store ID: {result["store_id"]}')
        self.stdout.write(f'Active: {"Yes" if result["is_active"] else "No"}')
        self.stdout.write(f'Files: {result["total_files"]} | Chunks: {result["total_chunks"]}')

        # Storage
        storage_mb = result["storage_used_bytes"] / (1024 * 1024)
        embeddings_mb = result["embeddings_used_bytes"] / (1024 * 1024)
        total_mb = result["total_used_bytes"] / (1024 * 1024)
        quota_mb = result["quota_bytes"] / (1024 * 1024)

        self.stdout.write(f'Storage: {storage_mb:.2f} MB')
        self.stdout.write(f'Embeddings: {embeddings_mb:.2f} MB')
        self.stdout.write(f'Total Used: {total_mb:.2f} MB / {quota_mb:.2f} MB')

        # Progress bar
        usage_pct = result["usage_percentage"]
        bar_length = 50
        filled = int(bar_length * min(usage_pct, 100) / 100)
        bar = '█' * filled + '░' * (bar_length - filled)

        self.stdout.write(status_style(f'Usage: [{bar}] {usage_pct:.1f}%'))

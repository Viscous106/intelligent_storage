"""
Django App Configuration for Storage.
"""

from django.apps import AppConfig


class StorageConfig(AppConfig):
    """Configuration for Storage application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'storage'
    verbose_name = 'Intelligent Storage System'

    def ready(self):
        """
        Import signals when app is ready.
        This ensures signals are registered properly.
        """
        try:
            # Import signals to register them
            from . import signals
            signals.register_signals()
        except ImportError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to import signals: {e}")

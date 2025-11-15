"""
File Organization Service
Automatically organizes uploaded files by type into structured folders.
Cross-platform compatible (Windows + Linux).
"""

import os
from pathlib import Path
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FileOrganizer:
    """
    Service to organize uploaded files by type into categorized folders.
    """

    # File type to folder mapping
    TYPE_FOLDERS = {
        'image': 'images',
        'video': 'videos',
        'audio': 'audio',
        'document': 'documents',
        'code': 'code',
        'compressed': 'compressed',
        'program': 'programs',
        'other': 'others',
    }

    def __init__(self):
        """Initialize file organizer with media root."""
        self.media_root = Path(getattr(settings, 'MEDIA_ROOT', 'media'))
        self._ensure_folders_exist()

    def _ensure_folders_exist(self):
        """Create all category folders if they don't exist."""
        for folder in self.TYPE_FOLDERS.values():
            folder_path = self.media_root / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f'Ensured folder exists: {folder_path}')

    def get_organized_path(self, file_type, original_filename):
        """
        Get the organized path for a file based on its type.

        Args:
            file_type: Type of file (image, video, document, etc.)
            original_filename: Original name of the file

        Returns:
            str: Relative path within media root
        """
        # Get folder for this file type
        folder = self.TYPE_FOLDERS.get(file_type, 'others')

        # Add date-based subfolder for better organization
        date_folder = datetime.now().strftime('%Y/%m')

        # Create unique filename to avoid conflicts
        filename = self._get_unique_filename(folder, date_folder, original_filename)

        # Return relative path
        return os.path.join(folder, date_folder, filename)

    def _get_unique_filename(self, folder, date_folder, original_filename):
        """
        Generate a unique filename to avoid conflicts.

        Args:
            folder: Category folder
            date_folder: Date-based subfolder
            original_filename: Original file name

        Returns:
            str: Unique filename
        """
        # Clean filename
        name = Path(original_filename).stem
        ext = Path(original_filename).suffix

        # Sanitize name (remove special characters)
        import re
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)

        # Start with original name
        filename = f"{name}{ext}"
        full_path = self.media_root / folder / date_folder
        full_path.mkdir(parents=True, exist_ok=True)

        # If file exists, add number suffix
        counter = 1
        while (full_path / filename).exists():
            filename = f"{name}_{counter}{ext}"
            counter += 1

        return filename

    def get_full_path(self, relative_path):
        """
        Get full filesystem path from relative path.

        Args:
            relative_path: Relative path within media root

        Returns:
            Path: Full filesystem path
        """
        return self.media_root / relative_path

    def organize_file(self, uploaded_file, file_type):
        """
        Organize and save an uploaded file.

        Args:
            uploaded_file: Django UploadedFile object
            file_type: Detected file type

        Returns:
            tuple: (relative_path, full_path)
        """
        # Get organized path
        relative_path = self.get_organized_path(file_type, uploaded_file.name)
        full_path = self.get_full_path(relative_path)

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        with open(full_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        logger.info(f'File organized: {uploaded_file.name} -> {relative_path}')

        return str(relative_path), str(full_path)

    def get_files_by_type(self, file_type):
        """
        Get all files of a specific type.

        Args:
            file_type: Type of files to retrieve

        Returns:
            list: List of file paths
        """
        folder = self.TYPE_FOLDERS.get(file_type, 'others')
        folder_path = self.media_root / folder

        if not folder_path.exists():
            return []

        # Find all files recursively
        files = []
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                relative = file_path.relative_to(self.media_root)
                files.append(str(relative))

        return files

    def get_all_organized_files(self):
        """
        Get all files organized by type.

        Returns:
            dict: Dictionary mapping file types to lists of file paths
        """
        organized = {}

        for file_type, folder in self.TYPE_FOLDERS.items():
            organized[file_type] = self.get_files_by_type(file_type)

        return organized

    def get_folder_stats(self):
        """
        Get statistics for each folder.

        Returns:
            dict: Statistics per folder
        """
        stats = {}

        for file_type, folder in self.TYPE_FOLDERS.items():
            folder_path = self.media_root / folder

            if not folder_path.exists():
                stats[file_type] = {
                    'count': 0,
                    'size_bytes': 0,
                    'folder': folder,
                }
                continue

            # Count files and calculate total size
            file_count = 0
            total_size = 0

            for file_path in folder_path.rglob('*'):
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size

            stats[file_type] = {
                'count': file_count,
                'size_bytes': total_size,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'folder': folder,
            }

        return stats


# Singleton instance
file_organizer = FileOrganizer()

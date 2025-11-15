"""
Unified File Upload Handler
Handles both single and multiple file uploads in one endpoint
"""

import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import MediaFile, UploadBatch
from .file_detector import file_detector
from .ai_analyzer import ai_analyzer
from .file_organizer import file_organizer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class UnifiedFileUploadView(View):
    """
    Unified file upload endpoint that handles both single and multiple files.

    This replaces the separate FileUploadView and BatchFileUploadView,
    reducing code duplication and storage overhead.

    Usage:
        Single file: POST with 'file' field
        Multiple files: POST with 'files' field (array)

    Optional fields:
        - user_comment: Comment for categorization
        - file_search_store: ID of store to index to
        - auto_index: Boolean to auto-index files (default: False)
    """

    def post(self, request):
        """
        Handle file upload(s).

        Accepts both:
        - file: Single file upload
        - files: Multiple file uploads (array)
        """
        # Detect if single or multiple files
        single_file = request.FILES.get('file')
        multiple_files = request.FILES.getlist('files')

        if not single_file and not multiple_files:
            return JsonResponse(
                {'error': 'No files provided. Use "file" for single or "files" for multiple.'},
                status=400
            )

        # Get optional parameters
        user_comment = request.POST.get('user_comment', '')
        file_search_store_id = request.POST.get('file_search_store')
        auto_index = request.POST.get('auto_index', 'false').lower() == 'true'

        # Prepare files list
        files_to_process = [single_file] if single_file else multiple_files

        # Process files
        if len(files_to_process) == 1:
            # Single file - return direct response
            result = self._process_single_file(
                files_to_process[0],
                user_comment,
                file_search_store_id,
                auto_index
            )
            return result
        else:
            # Multiple files - return batch response
            result = self._process_batch_files(
                files_to_process,
                user_comment,
                file_search_store_id,
                auto_index
            )
            return result

    def _process_single_file(self, uploaded_file, user_comment='',
                            file_search_store_id=None, auto_index=False):
        """Process a single file upload."""
        try:
            media_file = self._save_and_organize_file(
                uploaded_file, user_comment
            )

            # Index if requested
            if auto_index and file_search_store_id:
                self._index_file(media_file, file_search_store_id)

            return JsonResponse(
                {
                    'success': True,
                    'file': {
                        'id': media_file.id,
                        'original_name': media_file.original_name,
                        'detected_type': media_file.detected_type,
                        'mime_type': media_file.mime_type,
                        'file_size': media_file.file_size,
                        'ai_category': media_file.ai_category,
                        'ai_subcategory': media_file.ai_subcategory,
                        'ai_tags': media_file.ai_tags or [],
                        'ai_description': media_file.ai_description,
                        'storage_category': media_file.storage_category,
                        'storage_subcategory': media_file.storage_subcategory,
                        'relative_path': media_file.relative_path,
                    },
                    'message': f'File uploaded and organized in {media_file.storage_category}/{media_file.storage_subcategory}/'
                },
                status=201
            )

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            return JsonResponse(
                {'error': str(e)},
                status=500
            )

    def _process_batch_files(self, files, user_comment='',
                            file_search_store_id=None, auto_index=False):
        """Process multiple file uploads."""
        # Create batch record
        batch = UploadBatch.objects.create(
            batch_id=str(uuid.uuid4()),
            total_files=len(files),
            status='processing'
        )

        results = []
        processed = 0
        failed = 0

        for uploaded_file in files:
            try:
                media_file = self._save_and_organize_file(
                    uploaded_file, user_comment
                )

                # Index if requested
                if auto_index and file_search_store_id:
                    self._index_file(media_file, file_search_store_id)

                results.append({
                    'file': uploaded_file.name,
                    'status': 'success',
                    'id': media_file.id,
                    'category': media_file.storage_category,
                    'subcategory': media_file.storage_subcategory,
                })
                processed += 1

            except Exception as e:
                logger.error(f"Failed to process {uploaded_file.name}: {str(e)}")
                results.append({
                    'file': uploaded_file.name,
                    'status': 'failed',
                    'error': str(e)
                })
                failed += 1

        # Update batch status
        batch.processed_files = processed
        batch.failed_files = failed
        batch.status = 'completed' if failed == 0 else 'partial'
        batch.save()

        return JsonResponse(
            {
                'success': True,
                'batch_id': batch.batch_id,
                'total': len(files),
                'processed': processed,
                'failed': failed,
                'results': results,
            },
            status=201
        )

    def _save_and_organize_file(self, uploaded_file, user_comment=''):
        """
        Save and organize a file using the file organizer.
        This is the core logic shared between single and batch uploads.
        """
        # Use the file organizer to handle the file
        # This automatically:
        # 1. Detects file type
        # 2. Organizes into proper folder
        # 3. Generates unique filename
        # 4. Creates database record

        # Get file extension and content type
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        content_type = uploaded_file.content_type or 'application/octet-stream'

        # Determine file type from MIME type and extension
        file_type = self._detect_file_type_from_mime(content_type, file_extension)

        # Get organized path
        relative_path = file_organizer.get_organized_path(file_type, uploaded_file.name)
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # Save the file
        with open(absolute_path, 'wb+') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Get file size
        file_size = os.path.getsize(absolute_path)

        # Get AI analysis (if available)
        ai_result = self._analyze_with_ai(absolute_path, file_type, user_comment)

        # Convert file type to plural for database (legacy compatibility)
        file_type_plural = file_type + 's' if file_type != 'audio' else 'audio'
        if file_type == 'compressed':
            file_type_plural = 'compressed'

        # Create database record
        media_file = MediaFile.objects.create(
            original_name=uploaded_file.name,
            file_path=absolute_path,
            file_size=file_size,
            detected_type=file_type_plural,
            mime_type=content_type,
            file_extension=file_extension,
            magic_description=f'{file_type} file',
            ai_category=ai_result.get('category'),
            ai_subcategory=ai_result.get('subcategory'),
            ai_tags=ai_result.get('tags', []),
            ai_description=ai_result.get('description'),
            user_comment=user_comment,
            storage_category=file_type_plural,
            storage_subcategory=ai_result.get('subcategory', 'general'),
            relative_path=relative_path,
        )

        logger.info(f"File saved: {uploaded_file.name} -> {relative_path}")
        return media_file

    def _analyze_with_ai(self, file_path, file_type, user_comment):
        """Analyze file with AI if available."""
        try:
            if file_type == 'image':
                return ai_analyzer.analyze_image(file_path, user_comment)
            else:
                return ai_analyzer.analyze_file_content(
                    file_path, file_type, user_comment
                )
        except Exception as e:
            logger.warning(f"AI analysis failed: {str(e)}")
            return {}

    def _index_file(self, media_file, file_search_store_id):
        """Index file to search store if requested."""
        try:
            from .models import FileSearchStore
            store = FileSearchStore.objects.get(id=file_search_store_id)

            # Index the file using RAG service
            from .rag_service import rag_service
            rag_service.index_document(media_file, store)

            media_file.file_search_store = store
            media_file.is_indexed = True
            media_file.save()

            logger.info(f"File indexed: {media_file.original_name} to store {store.name}")
        except Exception as e:
            logger.warning(f"Indexing failed: {str(e)}")

    def _detect_file_type_from_mime(self, mime_type, extension):
        """Detect file type from MIME type and extension."""
        mime_lower = mime_type.lower()
        ext_lower = extension.lower()

        # Image files
        if mime_lower.startswith('image/') or ext_lower in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico']:
            return 'image'

        # Video files
        if mime_lower.startswith('video/') or ext_lower in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']:
            return 'video'

        # Audio files
        if mime_lower.startswith('audio/') or ext_lower in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma']:
            return 'audio'

        # Document files
        if 'pdf' in mime_lower or 'document' in mime_lower or 'text' in mime_lower or 'spreadsheet' in mime_lower:
            return 'document'
        if ext_lower in ['.pdf', '.doc', '.docx', '.txt', '.md', '.rtf', '.odt', '.xls', '.xlsx', '.csv', '.ppt', '.pptx']:
            return 'document'

        # Code files
        if ext_lower in ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php',
                         '.swift', '.kt', '.ts', '.jsx', '.tsx', '.vue', '.sql', '.sh', '.bat', '.json', '.xml',
                         '.yaml', '.yml']:
            return 'code'

        # Compressed files
        if 'zip' in mime_lower or 'compressed' in mime_lower or 'archive' in mime_lower:
            return 'compressed'
        if ext_lower in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tar.gz', '.tgz']:
            return 'compressed'

        # Program files
        if ext_lower in ['.exe', '.msi', '.app', '.deb', '.rpm', '.dmg', '.apk']:
            return 'program'

        # Default to other
        return 'other'

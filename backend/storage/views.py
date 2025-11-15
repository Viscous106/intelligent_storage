"""
API views for the intelligent storage system.
"""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    MediaFile, JSONDataStore, UploadBatch, DocumentChunk,
    FileSearchStore, SearchQuery, RAGResponse
)
from .serializers import (
    MediaFileSerializer, JSONDataStoreSerializer,
    UploadBatchSerializer, FileUploadSerializer,
    BatchFileUploadSerializer, JSONUploadSerializer,
    FileSearchStoreSerializer, FileSearchStoreCreateSerializer,
    DocumentChunkSerializer, SearchQuerySerializer, RAGResponseSerializer,
    FileIndexRequestSerializer, SemanticSearchRequestSerializer,
    RAGQueryRequestSerializer
)
from .file_detector import file_detector
from .ai_analyzer import ai_analyzer
from .db_manager import db_manager
from .rag_service import rag_service

logger = logging.getLogger(__name__)


class MediaFileViewSet(viewsets.ModelViewSet):
    """ViewSet for MediaFile operations."""

    queryset = MediaFile.objects.all()
    serializer_class = MediaFileSerializer

    @action(detail=False, methods=['GET'])
    def by_category(self, request):
        """Get files grouped by category."""
        category = request.query_params.get('category')
        if category:
            files = self.queryset.filter(detected_type=category)
        else:
            files = self.queryset.all()

        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def statistics(self, request):
        """Get storage statistics."""
        from django.db.models import Count, Sum

        stats = {
            'total_files': MediaFile.objects.count(),
            'by_type': dict(
                MediaFile.objects.values('detected_type')
                .annotate(count=Count('id'))
                .values_list('detected_type', 'count')
            ),
            'total_size': MediaFile.objects.aggregate(
                total=Sum('file_size')
            )['total'] or 0,
        }
        return Response(stats)


class FileUploadView(APIView):
    """
    Handle single file uploads with intelligent categorization.
    """

    def post(self, request):
        """
        Upload a single file.

        Accepts:
        - file: The file to upload
        - user_comment: Optional comment to aid categorization
        """
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = serializer.validated_data['file']
        user_comment = serializer.validated_data.get('user_comment', '')

        try:
            # Save file temporarily
            temp_path = self._save_temp_file(uploaded_file)

            # Detect file type
            file_type, metadata = file_detector.detect_file_type(temp_path)

            # Get AI analysis for better categorization
            ai_result = self._analyze_with_ai(
                temp_path, file_type, user_comment
            )

            # Determine subcategory
            subcategory = ai_result.get('category') or \
                         file_detector.get_subcategory_suggestion(temp_path, ai_result)

            # Move to organized location
            final_path = self._organize_file(
                temp_path, file_type, subcategory, uploaded_file.name
            )

            # Create database record
            media_file = MediaFile.objects.create(
                original_name=uploaded_file.name,
                file_path=final_path,
                file_size=metadata['file_size'],
                detected_type=file_type,
                mime_type=metadata['mime_type'],
                file_extension=metadata['extension'],
                magic_description=metadata['magic_description'],
                ai_category=ai_result.get('category'),
                ai_subcategory=subcategory,
                ai_tags=ai_result.get('tags', []),
                ai_description=ai_result.get('description'),
                user_comment=user_comment,
                storage_category=file_type,
                storage_subcategory=subcategory,
                relative_path=self._get_relative_path(final_path),
            )

            return Response(
                {
                    'success': True,
                    'file': MediaFileSerializer(media_file).data,
                    'message': f'File uploaded and organized in {file_type}/{subcategory}/'
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _save_temp_file(self, uploaded_file):
        """Save uploaded file to temporary location."""
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        temp_filename = f"{uuid.uuid4()}_{uploaded_file.name}"
        temp_path = os.path.join(temp_dir, temp_filename)

        with open(temp_path, 'wb+') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        return temp_path

    def _analyze_with_ai(self, file_path, file_type, user_comment):
        """Analyze file with AI."""
        try:
            if file_type == 'images':
                return ai_analyzer.analyze_image(file_path, user_comment)
            else:
                return ai_analyzer.analyze_file_content(
                    file_path, file_type, user_comment
                )
        except Exception as e:
            logger.warning(f"AI analysis failed: {str(e)}")
            return {}

    def _organize_file(self, temp_path, category, subcategory, original_name):
        """Move file to organized directory structure."""
        # Create directory structure: media/{category}/{subcategory}/
        target_dir = os.path.join(
            settings.MEDIA_ROOT,
            category,
            subcategory
        )
        os.makedirs(target_dir, exist_ok=True)

        # Generate unique filename to avoid conflicts
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_name}"
        final_path = os.path.join(target_dir, filename)

        # Move file
        os.rename(temp_path, final_path)

        return final_path

    def _get_relative_path(self, absolute_path):
        """Get path relative to MEDIA_ROOT."""
        return os.path.relpath(absolute_path, settings.MEDIA_ROOT)


class BatchFileUploadView(APIView):
    """
    Handle batch file uploads.
    """

    def post(self, request):
        """
        Upload multiple files at once.

        Accepts:
        - files: List of files to upload
        - user_comment: Optional comment for all files
        """
        serializer = BatchFileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        files = serializer.validated_data['files']
        user_comment = serializer.validated_data.get('user_comment', '')

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
                # Process each file (reusing single upload logic)
                temp_path = FileUploadView()._save_temp_file(uploaded_file)
                file_type, metadata = file_detector.detect_file_type(temp_path)
                ai_result = FileUploadView()._analyze_with_ai(
                    temp_path, file_type, user_comment
                )
                subcategory = ai_result.get('category') or \
                             file_detector.get_subcategory_suggestion(temp_path, ai_result)
                final_path = FileUploadView()._organize_file(
                    temp_path, file_type, subcategory, uploaded_file.name
                )

                media_file = MediaFile.objects.create(
                    original_name=uploaded_file.name,
                    file_path=final_path,
                    file_size=metadata['file_size'],
                    detected_type=file_type,
                    mime_type=metadata['mime_type'],
                    file_extension=metadata['extension'],
                    magic_description=metadata['magic_description'],
                    ai_category=ai_result.get('category'),
                    ai_subcategory=subcategory,
                    ai_tags=ai_result.get('tags', []),
                    ai_description=ai_result.get('description'),
                    user_comment=user_comment,
                    storage_category=file_type,
                    storage_subcategory=subcategory,
                    relative_path=FileUploadView()._get_relative_path(final_path),
                )

                results.append({
                    'file': uploaded_file.name,
                    'status': 'success',
                    'category': f"{file_type}/{subcategory}"
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

        # Update batch record
        batch.processed_files = processed
        batch.failed_files = failed
        batch.status = 'completed'
        batch.completed_at = datetime.now()
        batch.save()

        return Response(
            {
                'success': True,
                'batch_id': batch.batch_id,
                'total': len(files),
                'processed': processed,
                'failed': failed,
                'results': results
            },
            status=status.HTTP_201_CREATED
        )


class JSONDataUploadView(APIView):
    """
    Handle JSON data uploads with intelligent SQL/NoSQL decision.
    """

    def post(self, request):
        """
        Upload JSON data for storage.

        Accepts:
        - data: JSON object or array
        - name: Optional name for the dataset
        - user_comment: Optional comment to aid schema generation
        - force_db_type: Optional 'SQL' or 'NoSQL' to override AI decision
        """
        serializer = JSONUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        json_data = serializer.validated_data['data']
        user_comment = serializer.validated_data.get('user_comment', '')
        force_db_type = serializer.validated_data.get('force_db_type')
        name = serializer.validated_data.get('name') or \
               f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Get AI recommendation
            ai_result = ai_analyzer.analyze_json_for_db_choice(
                json_data, user_comment
            )

            # Use forced type or AI recommendation
            db_type = force_db_type or ai_result.get('database_type', 'NoSQL')

            # Generate names
            if db_type == 'SQL':
                table_name = name.lower().replace(' ', '_')
                collection_name = None
            else:
                table_name = None
                collection_name = name.lower().replace(' ', '_')

            # Store data
            storage_result = db_manager.store_json_data(
                data=json_data,
                db_type=db_type,
                collection_name=collection_name,
                table_name=table_name,
                user_comment=user_comment
            )

            if not storage_result.get('success'):
                return Response(
                    {'error': storage_result.get('error')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Create tracking record
            record_count = len(json_data) if isinstance(json_data, list) else 1

            json_store = JSONDataStore.objects.create(
                name=name,
                description=user_comment,
                database_type=db_type,
                confidence_score=ai_result.get('confidence', 0),
                table_name=storage_result.get('table'),
                collection_name=storage_result.get('collection'),
                inferred_schema=ai_result.get('suggested_schema', {}),
                sample_data=json_data[0] if isinstance(json_data, list) and json_data else json_data,
                structure_depth=self._get_depth(json_data),
                has_nested_objects=self._has_nested(json_data),
                has_arrays=self._has_arrays(json_data),
                ai_reasoning=ai_result.get('reasoning'),
                user_comment=user_comment,
                record_count=record_count,
            )

            # Prepare schema display
            schema_display = {}
            if db_type == 'SQL':
                schema_display = {
                    'type': 'SQL',
                    'table_name': storage_result.get('table'),
                    'create_statement': storage_result.get('sql_schema'),
                    'columns': storage_result.get('schema')
                }
            else:
                schema_display = {
                    'type': 'NoSQL',
                    'collection_name': storage_result.get('collection'),
                    'document_structure': storage_result.get('mongo_schema'),
                }

            return Response(
                {
                    'success': True,
                    'storage': JSONDataStoreSerializer(json_store).data,
                    'ai_analysis': ai_result,
                    'generated_schema': schema_display,
                    'message': f"Data stored in {db_type} database"
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"JSON upload failed: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_depth(self, obj, current=0):
        """Calculate nesting depth."""
        if isinstance(obj, dict):
            return max([self._get_depth(v, current + 1) for v in obj.values()] or [current])
        elif isinstance(obj, list) and obj:
            return max([self._get_depth(item, current) for item in obj] or [current])
        return current

    def _has_nested(self, obj):
        """Check for nested objects."""
        if isinstance(obj, dict):
            return any(isinstance(v, dict) for v in obj.values())
        elif isinstance(obj, list) and obj:
            return any(isinstance(item, dict) and
                      any(isinstance(v, dict) for v in item.values())
                      for item in obj if isinstance(item, dict))
        return False

    def _has_arrays(self, obj):
        """Check for arrays."""
        if isinstance(obj, dict):
            return any(isinstance(v, list) for v in obj.values())
        elif isinstance(obj, list) and obj:
            return any(isinstance(item, dict) and
                      any(isinstance(v, list) for v in item.values())
                      for item in obj if isinstance(item, dict))
        return False


class JSONDataViewSet(viewsets.ModelViewSet):
    """ViewSet for JSONDataStore operations."""

    queryset = JSONDataStore.objects.all()
    serializer_class = JSONDataStoreSerializer

    @action(detail=True, methods=['GET'])
    def query(self, request, pk=None):
        """Query data from the stored dataset."""
        json_store = self.get_object()
        limit = int(request.query_params.get('limit', 100))

        try:
            if json_store.database_type == 'NoSQL':
                results = db_manager.query_mongodb(
                    json_store.collection_name,
                    limit=limit
                )
            else:
                results = db_manager.query_postgresql(
                    json_store.table_name,
                    limit=limit
                )

            return Response({
                'success': True,
                'data': results,
                'count': len(results)
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'])
    def list_databases(self, request):
        """List all available collections and tables."""
        try:
            return Response({
                'mongodb_collections': db_manager.get_collection_list(),
                'postgresql_tables': db_manager.get_table_list(),
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
def health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'services': {
            'django': True,
            'postgresql': _check_postgres(),
            'mongodb': _check_mongodb(),
            'ollama': _check_ollama(),
        }
    })


def _check_postgres():
    """Check PostgreSQL connection."""
    try:
        from django.db import connection
        connection.ensure_connection()
        return True
    except Exception:
        return False


def _check_mongodb():
    """Check MongoDB connection."""
    try:
        return db_manager.mongo_db is not None
    except Exception:
        return False


def _check_ollama():
    """Check Ollama availability."""
    try:
        import requests
        response = requests.get(
            f"{settings.OLLAMA_SETTINGS['HOST']}/api/tags",
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False


# ============================================================================
# RAG (Retrieval Augmented Generation) API Endpoints
# ============================================================================

@api_view(['POST'])
def index_document(request, file_id):
    """
    Index a specific document for semantic search.

    Args:
        file_id: MediaFile ID to index
    """
    try:
        media_file = MediaFile.objects.get(id=file_id)
        result = rag_service.index_document(media_file)

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except MediaFile.DoesNotExist:
        return Response(
            {'error': 'File not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def semantic_search(request):
    """
    Perform semantic search across indexed documents.

    Request body:
        {
            "query": "search query text",
            "limit": 10,  // optional
            "file_type": "documents"  // optional filter
        }
    """
    try:
        query = request.data.get('query')
        if not query:
            return Response(
                {'error': 'Query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = request.data.get('limit', 10)
        file_type_filter = request.data.get('file_type')

        results = rag_service.search(
            query=query,
            limit=limit,
            file_type_filter=file_type_filter
        )

        return Response({
            'success': True,
            'query': query,
            'results_count': len(results),
            'results': results
        })

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def rag_query(request):
    """
    Ask a question and get an AI-generated answer with sources.

    Request body:
        {
            "question": "What is this about?",
            "max_sources": 5,  // optional
            "file_type": "documents"  // optional filter
        }
    """
    try:
        question = request.data.get('question')
        if not question:
            return Response(
                {'error': 'Question is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        max_sources = request.data.get('max_sources', 5)
        file_type_filter = request.data.get('file_type')

        result = rag_service.generate_rag_response(
            query=question,
            max_context_chunks=max_sources,
            file_type_filter=file_type_filter
        )

        if result['success']:
            return Response(result)
        else:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def reindex_all(request):
    """
    Reindex all documents in the system.
    """
    try:
        result = rag_service.reindex_all_documents()
        return Response(result)

    except Exception as e:
        logger.error(f"Reindexing failed: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def rag_stats(request):
    """
    Get RAG system statistics.
    """
    try:
        total_chunks = DocumentChunk.objects.count()
        indexed_files = DocumentChunk.objects.values('media_file').distinct().count()
        file_types = DocumentChunk.objects.values('file_type').distinct()

        return Response({
            'total_chunks': total_chunks,
            'indexed_files': indexed_files,
            'file_types': list(file_types)
        })

    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===== Gemini-style File Search Store Views =====

class FileSearchStoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for File Search Store management.
    Provides Gemini-style document organization and storage management.
    """
    queryset = FileSearchStore.objects.all()
    serializer_class = FileSearchStoreSerializer
    lookup_field = 'store_id'

    def create(self, request):
        """Create a new file search store."""
        serializer = FileSearchStoreCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if store with this name already exists
            if FileSearchStore.objects.filter(name=serializer.validated_data['name']).exists():
                return Response(
                    {'error': 'Store with this name already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create the store
            store = FileSearchStore.objects.create(**serializer.validated_data)

            return Response(
                FileSearchStoreSerializer(store).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Failed to create file search store: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['GET'])
    def files(self, request, store_id=None):
        """Get all files in this store."""
        try:
            store = self.get_object()
            files = MediaFile.objects.filter(file_search_store=store)
            serializer = MediaFileSerializer(files, many=True)
            return Response(serializer.data)
        except FileSearchStore.DoesNotExist:
            return Response(
                {'error': 'Store not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['GET'])
    def chunks(self, request, store_id=None):
        """Get all chunks in this store."""
        try:
            store = self.get_object()
            chunks = DocumentChunk.objects.filter(file_search_store=store)
            serializer = DocumentChunkSerializer(chunks, many=True)
            return Response(serializer.data)
        except FileSearchStore.DoesNotExist:
            return Response(
                {'error': 'Store not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['GET'])
    def stats(self, request, store_id=None):
        """Get statistics for this store."""
        try:
            store = self.get_object()
            return Response({
                'store_id': str(store.store_id),
                'name': store.name,
                'display_name': store.display_name,
                'total_files': store.total_files,
                'total_chunks': store.total_chunks,
                'storage_size_bytes': store.storage_size_bytes,
                'embeddings_size_bytes': store.embeddings_size_bytes,
                'total_size_bytes': store.total_size_bytes,
                'storage_quota': store.storage_quota,
                'storage_used_percentage': store.storage_used_percentage,
                'is_quota_exceeded': store.is_quota_exceeded(),
                'is_active': store.is_active,
            })
        except FileSearchStore.DoesNotExist:
            return Response(
                {'error': 'Store not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['DELETE'])
    def force_delete(self, request, store_id=None):
        """Force delete a store and all its associated data."""
        try:
            store = self.get_object()

            # Delete associated chunks
            DocumentChunk.objects.filter(file_search_store=store).delete()

            # Update files to remove store reference
            MediaFile.objects.filter(file_search_store=store).update(
                file_search_store=None,
                is_indexed=False
            )

            # Delete the store
            store.delete()

            return Response(
                {'message': 'Store and associated data deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )

        except FileSearchStore.DoesNotExist:
            return Response(
                {'error': 'Store not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['POST'])
def index_file_to_store(request):
    """
    Index a file into a File Search Store with custom chunking configuration.
    Gemini-style file indexing with configurable parameters.
    """
    serializer = FileIndexRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    file_id = serializer.validated_data['file_id']
    store_name = serializer.validated_data.get('file_search_store_name')
    chunking_strategy = serializer.validated_data.get('chunking_strategy')
    max_tokens = serializer.validated_data.get('max_tokens_per_chunk')
    max_overlap = serializer.validated_data.get('max_overlap_tokens')
    custom_metadata = serializer.validated_data.get('custom_metadata', {})

    try:
        # Get the file
        media_file = MediaFile.objects.get(id=file_id)

        # Get or use default store
        store = None
        if store_name:
            store = FileSearchStore.objects.get(name=store_name)
            # Use store's configuration if not overridden
            if not chunking_strategy:
                chunking_strategy = store.chunking_strategy
            if not max_tokens:
                max_tokens = store.max_tokens_per_chunk
            if not max_overlap:
                max_overlap = store.max_overlap_tokens

        # Check quota if store is specified
        if store and store.is_quota_exceeded():
            return Response(
                {'error': 'Storage quota exceeded for this store'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Index the file using RAG service
        from .chunking_service import ChunkingService
        from .embedding_service import embedding_service

        chunker = ChunkingService(
            strategy=chunking_strategy or 'auto',
            max_tokens_per_chunk=max_tokens or 512,
            max_overlap_tokens=max_overlap or 50
        )

        # Extract text from file
        text = chunker.extract_text_from_file(media_file.file_path)

        if not text:
            return Response(
                {'error': 'Could not extract text from file'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Chunk the text
        chunks = chunker.chunk_text(text, metadata=custom_metadata, strategy=chunking_strategy)

        # Create document chunks with embeddings
        created_chunks = []
        for chunk_data in chunks:
            # Generate embedding
            embedding = embedding_service.generate_embedding(chunk_data['chunk_text'])

            # Create chunk
            chunk = DocumentChunk.objects.create(
                media_file=media_file,
                file_search_store=store,
                chunk_index=chunk_data['chunk_index'],
                chunk_text=chunk_data['chunk_text'],
                chunk_size=chunk_data['chunk_size'],
                token_count=chunk_data.get('token_count', 0),
                embedding=embedding,
                file_name=media_file.original_name,
                file_type=media_file.detected_type,
                metadata=chunk_data.get('metadata', {}),
                chunking_strategy=chunk_data.get('chunking_strategy', 'auto'),
                overlap_tokens=chunk_data.get('overlap_tokens', 0),
                source_reference=f"{media_file.original_name}, chunk {chunk_data['chunk_index']}"
            )
            created_chunks.append(chunk)

        # Update media file
        media_file.is_indexed = True
        media_file.indexed_at = datetime.now()
        media_file.file_search_store = store
        media_file.custom_metadata.update(custom_metadata)
        media_file.save()

        # Update store statistics
        if store:
            store.total_files = MediaFile.objects.filter(file_search_store=store).count()
            store.total_chunks = DocumentChunk.objects.filter(file_search_store=store).count()
            store.storage_size_bytes += media_file.file_size
            # Estimate embeddings size (~3x data size)
            store.embeddings_size_bytes += media_file.file_size * 3
            store.save()

        return Response({
            'message': 'File indexed successfully',
            'file_id': file_id,
            'store': store.name if store else None,
            'chunks_created': len(created_chunks),
            'total_tokens': sum(c.token_count for c in created_chunks),
            'chunking_strategy': chunking_strategy or 'auto'
        }, status=status.HTTP_201_CREATED)

    except MediaFile.DoesNotExist:
        return Response(
            {'error': 'File not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except FileSearchStore.DoesNotExist:
        return Response(
            {'error': 'File search store not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Failed to index file: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def semantic_search_with_filters(request):
    """
    Perform semantic search with Gemini-style filtering.
    Supports store filtering and metadata filtering.
    """
    serializer = SemanticSearchRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    query = serializer.validated_data['query']
    store_names = serializer.validated_data.get('file_search_store_names', [])
    metadata_filter = serializer.validated_data.get('metadata_filter', {})
    limit = serializer.validated_data.get('limit', 10)
    include_citations = serializer.validated_data.get('include_citations', True)

    try:
        from .embedding_service import embedding_service
        from django.db.models import Q

        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(query)

        # Build filter query
        filter_q = Q()

        # Filter by stores
        if store_names:
            stores = FileSearchStore.objects.filter(name__in=store_names)
            filter_q &= Q(file_search_store__in=stores)

        # Filter by metadata
        if metadata_filter:
            for key, value in metadata_filter.items():
                filter_q &= Q(**{f'metadata__{key}': value})

        # Search using pgvector
        chunks = DocumentChunk.objects.filter(filter_q).order_by(
            DocumentChunk.embedding.cosine_distance(query_embedding)
        )[:limit]

        # Build response
        results = []
        for chunk in chunks:
            result = {
                'chunk_id': chunk.id,
                'chunk_text': chunk.chunk_text,
                'file_name': chunk.file_name,
                'file_type': chunk.file_type,
                'chunk_index': chunk.chunk_index,
                'metadata': chunk.metadata,
            }

            if include_citations:
                result['citation'] = {
                    'citation_id': str(chunk.citation_id),
                    'source_reference': chunk.source_reference,
                    'source_file': chunk.file_name,
                    'chunk_index': chunk.chunk_index,
                }

            results.append(result)

        # Save search query
        search_query = SearchQuery.objects.create(
            query_text=query,
            query_embedding=query_embedding,
            results_count=len(results),
            metadata_filter=metadata_filter
        )

        if store_names:
            stores = FileSearchStore.objects.filter(name__in=store_names)
            search_query.file_search_stores.set(stores)

        return Response({
            'query': query,
            'results_count': len(results),
            'results': results,
            'filters_applied': {
                'stores': store_names,
                'metadata': metadata_filter
            }
        })

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

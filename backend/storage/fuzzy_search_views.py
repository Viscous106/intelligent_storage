"""
Fuzzy Search API Views using Trie Algorithm
Professional endpoints for intelligent file search
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import MediaFile
from .trie_fuzzy_search import trie_search_engine

logger = logging.getLogger(__name__)


def _file_to_dict(media_file):
    """Convert MediaFile model to dictionary for indexing."""
    return {
        'id': media_file.id,
        'name': media_file.original_name,
        'type': media_file.detected_type or 'other',
        'size': media_file.file_size or 0,
        'uploaded_at': media_file.uploaded_at.isoformat() if media_file.uploaded_at else None,
        'tags': media_file.ai_tags or [],
        'extension': media_file.file_extension or '',
        'path': media_file.relative_path or media_file.file_path,
        'mime_type': media_file.mime_type or '',
        'description': media_file.ai_description or '',
        'category': media_file.ai_category or media_file.detected_type or 'other',
        'metadata': media_file.custom_metadata or {}
    }


@api_view(['POST'])
def initialize_search_index(request):
    """
    Initialize or rebuild the search index with all files.
    This should be called after bulk uploads or periodically.

    Returns:
        JSON response with indexing statistics
    """
    try:
        # Get all files from database
        all_files = MediaFile.objects.all()

        indexed_count = 0
        for media_file in all_files:
            try:
                file_dict = _file_to_dict(media_file)
                trie_search_engine.index_file(file_dict)
                indexed_count += 1
            except Exception as e:
                logger.error(f"Error indexing file {media_file.id}: {e}")
                continue

        stats = trie_search_engine.get_stats()

        return Response({
            'success': True,
            'message': f'Successfully indexed {indexed_count} files',
            'stats': stats
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error initializing search index: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def index_single_file(request, file_id):
    """
    Index a single file for search.

    Args:
        file_id: ID of the file to index

    Returns:
        JSON response confirming indexing
    """
    try:
        media_file = MediaFile.objects.get(id=file_id)
        file_dict = _file_to_dict(media_file)
        trie_search_engine.index_file(file_dict)

        return Response({
            'success': True,
            'message': f'File "{media_file.original_name}" indexed successfully',
            'file_id': file_id
        }, status=status.HTTP_200_OK)

    except MediaFile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'File not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error indexing file {file_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
def fuzzy_search(request):
    """
    Perform adaptive fuzzy search using Trie algorithm.

    Query parameters (GET) or body parameters (POST):
        - q or query: Search query (required)
        - limit: Maximum number of results (default: 50)
        - fuzzy: Enable fuzzy matching (default: true)

    Advanced filters supported in query:
        - @type:image - Filter by file type
        - @size:>1mb - Filter by file size
        - @date:>2024-01-01 - Filter by date
        - @ext:pdf - Filter by extension

    Examples:
        - "vacation photo" - Semantic search for vacation photos
        - "report @type:document @ext:pdf" - PDFs containing "report"
        - "screenshot @date:>2024-01-01" - Recent screenshots
        - "@type:image @size:<1mb" - Small images

    Returns:
        JSON response with ranked search results
    """
    try:
        # Get parameters
        if request.method == 'POST':
            query = request.data.get('q') or request.data.get('query', '')
            limit = int(request.data.get('limit', 50))
            use_fuzzy = request.data.get('fuzzy', True)
        else:
            query = request.GET.get('q', '') or request.GET.get('query', '')
            limit = int(request.GET.get('limit', 50))
            use_fuzzy = request.GET.get('fuzzy', 'true').lower() != 'false'

        if not query:
            return Response({
                'success': False,
                'error': 'Search query is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Auto-index if empty or small index
        from .trie_fuzzy_search import trie_search_engine as search_engine
        stats = search_engine.get_stats()
        db_file_count = MediaFile.objects.filter(is_deleted=False).count()

        # Re-index if index is empty or significantly out of sync
        if stats['total_files_indexed'] == 0 or stats['total_files_indexed'] < db_file_count * 0.5:
            logger.info(f"Auto-indexing files. DB: {db_file_count}, Indexed: {stats['total_files_indexed']}")

            # Index all non-deleted files
            all_files = MediaFile.objects.filter(is_deleted=False)
            for media_file in all_files:
                try:
                    file_dict = _file_to_dict(media_file)
                    search_engine.index_file(file_dict)
                except Exception as e:
                    logger.error(f"Error indexing file {media_file.id}: {e}")
                    continue

        # Perform search
        results = search_engine.search(
            query=query,
            limit=limit,
            use_fuzzy=use_fuzzy
        )

        # Return results
        return Response({
            'success': True,
            'query': query,
            'results_count': len(results),
            'results': results,
            'filters_detected': trie_search_engine.parse_advanced_filters(query),
            'fuzzy_enabled': use_fuzzy
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error performing fuzzy search: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def record_file_interaction(request, file_id):
    """
    Record user interaction with a file for ML learning.

    Body parameters:
        - interaction_type: 'view', 'download', or 'select'
        - query: Optional search query that led to this interaction

    This helps the search engine learn and adapt to user behavior.

    Returns:
        JSON response confirming interaction recording
    """
    try:
        interaction_type = request.data.get('interaction_type', 'view')
        query = request.data.get('query')

        # Validate interaction type
        if interaction_type not in ['view', 'download', 'select']:
            return Response({
                'success': False,
                'error': 'Invalid interaction type. Must be: view, download, or select'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify file exists
        try:
            MediaFile.objects.get(id=file_id)
        except MediaFile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'File not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Record interaction
        trie_search_engine.record_interaction(
            file_id=file_id,
            interaction_type=interaction_type,
            query=query
        )

        return Response({
            'success': True,
            'message': f'{interaction_type.capitalize()} interaction recorded',
            'file_id': file_id
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error recording interaction: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_search_stats(request):
    """
    Get search engine statistics.

    Returns:
        JSON response with statistics about the search engine
    """
    try:
        stats = trie_search_engine.get_stats()

        # Add database file count for comparison
        db_file_count = MediaFile.objects.count()
        stats['database_files'] = db_file_count
        stats['index_coverage'] = (
            stats['total_files_indexed'] / db_file_count * 100
            if db_file_count > 0 else 0
        )

        return Response({
            'success': True,
            'stats': stats
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_suggestions(request):
    """
    Get search suggestions as user types.

    Query parameters:
        - q or query: Partial search query
        - limit: Maximum number of suggestions (default: 5)

    Returns:
        JSON response with suggested completions
    """
    try:
        query = request.GET.get('q', '') or request.GET.get('query', '')
        limit = int(request.GET.get('limit', 5))

        if not query:
            return Response({
                'success': True,
                'query': '',
                'suggestions': []
            }, status=status.HTTP_200_OK)

        # Get suggestions using fuzzy search
        results = trie_search_engine.search(
            query=query,
            limit=limit,
            use_fuzzy=True
        )

        # Format suggestions
        suggestions = []
        for result in results:
            suggestions.append({
                'id': result['id'],
                'name': result['name'],
                'type': result['type'],
                'score': result.get('search_score', 0),
                'match_type': result.get('match_type', 'unknown')
            })

        return Response({
            'success': True,
            'query': query,
            'suggestions': suggestions
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def clear_search_cache(request):
    """
    Clear all search learning data and history.

    This resets all user behavior learning but keeps the file index.

    Returns:
        JSON response confirming cache clearance
    """
    try:
        # Note: The Trie search engine stores data in memory
        # For production, you'd want to persist and clear from database
        trie_search_engine.search_history = []
        trie_search_engine.user_interactions.clear()

        return Response({
            'success': True,
            'message': 'Search cache and learning data cleared successfully'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error clearing search cache: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

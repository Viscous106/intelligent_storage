"""
Search Suggestion API Views

Provides intelligent search suggestions using history, cache, and AI
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .admin_auth import require_admin
from .intelligent_search_suggestions import get_suggestion_engine

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_search_suggestions(request, admin_id):
    """
    Get intelligent search suggestions

    Query parameters:
    - q: Partial query string
    - limit: Max suggestions to return (default: 10)

    Returns suggestions from:
    - Recent searches
    - Popular searches
    - Trending searches
    - AI-powered semantic suggestions
    - Context-aware suggestions
    """
    try:
        engine = get_suggestion_engine()

        query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 10))

        suggestions = engine.get_suggestions(query, admin_id, limit)

        return JsonResponse({
            'success': True,
            'query': query,
            'suggestions': suggestions,
            'count': len(suggestions)
        })

    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def record_search_query(request, admin_id):
    """
    Record a search query for learning

    Request body:
    {
        "query": "search term",
        "results_count": 10,
        "results": [...],  // optional
        "clicked_file": "path/to/file"  // optional
    }
    """
    try:
        engine = get_suggestion_engine()

        data = json.loads(request.body)
        query = data.get('query', '').strip()
        results_count = data.get('results_count', 0)
        results = data.get('results', [])
        clicked_file = data.get('clicked_file')

        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)

        engine.record_search(
            query=query,
            admin_id=admin_id,
            results_count=results_count,
            results=results,
            clicked_file=clicked_file
        )

        return JsonResponse({
            'success': True,
            'message': 'Search recorded'
        })

    except Exception as e:
        logger.error(f"Error recording search: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def record_search_click(request, admin_id):
    """
    Record when user clicks a search result

    Request body:
    {
        "query": "search term",
        "clicked_file": "path/to/file",
        "position": 3
    }
    """
    try:
        engine = get_suggestion_engine()

        data = json.loads(request.body)
        query = data.get('query', '').strip()
        clicked_file = data.get('clicked_file')
        position = data.get('position', 0)

        if not query or not clicked_file:
            return JsonResponse({
                'success': False,
                'error': 'Query and clicked_file are required'
            }, status=400)

        engine.record_click(query, clicked_file, position)

        return JsonResponse({
            'success': True,
            'message': 'Click recorded'
        })

    except Exception as e:
        logger.error(f"Error recording click: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_search_analytics(request, admin_id):
    """
    Get search analytics and statistics

    Query parameters:
    - user_only: Set to 'true' to get only user's statistics
    """
    try:
        engine = get_suggestion_engine()

        user_only = request.GET.get('user_only', 'false').lower() == 'true'

        if user_only:
            analytics = engine.get_analytics(admin_id)
        else:
            analytics = engine.get_analytics()

        return JsonResponse({
            'success': True,
            'analytics': analytics
        })

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def get_trending_searches(request, admin_id):
    """
    Get trending search queries (last 24 hours)

    Query parameters:
    - limit: Max trending searches (default: 10)
    """
    try:
        engine = get_suggestion_engine()

        limit = int(request.GET.get('limit', 10))

        # Get all trending searches
        import time
        current_time = time.time()
        cutoff_time = current_time - 86400  # 24 hours

        trending = []
        for query_lower, data in engine.trending_searches.items():
            if data['last_searched'] >= cutoff_time:
                trending.append({
                    'query': data.get('query', query_lower),
                    'count': data['count'],
                    'last_searched': data['last_searched'],
                    'user_count': len(data.get('users', []))
                })

        # Sort by count
        trending.sort(key=lambda x: x['count'], reverse=True)

        return JsonResponse({
            'success': True,
            'trending': trending[:limit],
            'count': len(trending)
        })

    except Exception as e:
        logger.error(f"Error getting trending searches: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_admin
def clear_search_history(request, admin_id):
    """
    Clear user's search history
    """
    try:
        engine = get_suggestion_engine()

        engine.clear_user_history(admin_id)

        return JsonResponse({
            'success': True,
            'message': 'Search history cleared'
        })

    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def save_search_data(request, admin_id):
    """
    Manually trigger save of search data
    (normally auto-saved periodically)
    """
    try:
        engine = get_suggestion_engine()

        engine.save_data()

        return JsonResponse({
            'success': True,
            'message': 'Search data saved'
        })

    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

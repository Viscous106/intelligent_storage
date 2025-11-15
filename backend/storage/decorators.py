"""
Django Decorators for Intelligent Storage System.
Custom decorators for views, functions, and classes.
"""

from functools import wraps
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings
import time
import logging

logger = logging.getLogger(__name__)


# ===== Performance Decorators =====

def measure_performance(view_func):
    """
    Decorator to measure and log view performance.
    Usage: @measure_performance
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()

        response = view_func(request, *args, **kwargs)

        duration = time.time() - start_time

        logger.info(
            f'Performance: {view_func.__name__} took {duration:.3f}s - '
            f'Method: {request.method}, Path: {request.path}'
        )

        # Add custom header with timing
        if hasattr(response, '__setitem__'):
            response['X-Processing-Time'] = f'{duration:.3f}s'

        return response

    return wrapper


def cache_result(timeout=300, key_prefix=''):
    """
    Decorator to cache function results.
    Usage: @cache_result(timeout=600, key_prefix='my_func')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f'{key_prefix or func.__name__}_{str(args)}_{str(kwargs)}'

            # Try to get from cache
            result = cache.get(cache_key)

            if result is not None:
                logger.debug(f'Cache hit for {func.__name__}')
                return result

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, timeout)
            logger.debug(f'Cache miss for {func.__name__} - result cached')

            return result

        return wrapper
    return decorator


# ===== API Decorators =====

def api_response(view_func):
    """
    Decorator to standardize API responses.
    Wraps response in {'success': True, 'data': ...} format.
    Usage: @api_response
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            result = view_func(request, *args, **kwargs)

            # If already a JsonResponse, return as-is
            if isinstance(result, JsonResponse):
                return result

            # Wrap in standard format
            return JsonResponse({
                'success': True,
                'data': result,
            })

        except Exception as e:
            logger.error(f'API error in {view_func.__name__}: {str(e)}', exc_info=True)

            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)

    return wrapper


def ajax_required(view_func):
    """
    Decorator to require AJAX requests.
    Usage: @ajax_required
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'This endpoint requires AJAX'
            }, status=400)

        return view_func(request, *args, **kwargs)

    return wrapper


def require_post(view_func):
    """
    Decorator to require POST method.
    Usage: @require_post
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method != 'POST':
            return JsonResponse({
                'error': 'POST method required'
            }, status=405)

        return view_func(request, *args, **kwargs)

    return wrapper


# ===== Validation Decorators =====

def validate_json(view_func):
    """
    Decorator to validate that request contains valid JSON.
    Usage: @validate_json
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        import json

        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.body:
                    request.json_data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'Invalid JSON in request body'
                }, status=400)

        return view_func(request, *args, **kwargs)

    return wrapper


def validate_file_upload(max_size=None, allowed_types=None):
    """
    Decorator to validate file uploads.
    Usage: @validate_file_upload(max_size=10*1024*1024, allowed_types=['pdf', 'docx'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.FILES:
                for uploaded_file in request.FILES.values():
                    # Check file size
                    if max_size and uploaded_file.size > max_size:
                        return JsonResponse({
                            'error': f'File {uploaded_file.name} exceeds maximum size of {max_size} bytes'
                        }, status=400)

                    # Check file type
                    if allowed_types:
                        import os
                        ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
                        if ext not in allowed_types:
                            return JsonResponse({
                                'error': f'File type {ext} not allowed. Allowed types: {", ".join(allowed_types)}'
                            }, status=400)

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# ===== Error Handling Decorators =====

def handle_exceptions(default_response=None):
    """
    Decorator to handle exceptions gracefully.
    Usage: @handle_exceptions(default_response={'error': 'Something went wrong'})
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except Exception as e:
                logger.error(
                    f'Exception in {view_func.__name__}: {str(e)}',
                    exc_info=True
                )

                if default_response:
                    return JsonResponse(default_response, status=500)
                else:
                    return JsonResponse({
                        'error': 'An error occurred',
                        'message': str(e) if settings.DEBUG else 'Internal server error'
                    }, status=500)

        return wrapper
    return decorator


# ===== Logging Decorators =====

def log_request(view_func):
    """
    Decorator to log all requests to a view.
    Usage: @log_request
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        logger.info(
            f'Request: {request.method} {request.path} - '
            f'User: {request.user.username if request.user.is_authenticated else "anonymous"} - '
            f'IP: {request.META.get("REMOTE_ADDR")}'
        )

        response = view_func(request, *args, **kwargs)

        logger.info(
            f'Response: {request.method} {request.path} - '
            f'Status: {response.status_code if hasattr(response, "status_code") else "N/A"}'
        )

        return response

    return wrapper


def log_errors_only(view_func):
    """
    Decorator to only log errors (not successful requests).
    Usage: @log_errors_only
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            response = view_func(request, *args, **kwargs)

            # Log if response indicates error
            if hasattr(response, 'status_code') and response.status_code >= 400:
                logger.warning(
                    f'Error response: {request.method} {request.path} - '
                    f'Status: {response.status_code}'
                )

            return response

        except Exception as e:
            logger.error(
                f'Exception: {request.method} {request.path} - '
                f'Error: {str(e)}',
                exc_info=True
            )
            raise

    return wrapper


# ===== Transaction Decorators =====

def atomic_transaction(view_func):
    """
    Decorator to wrap view in database transaction.
    Usage: @atomic_transaction
    """
    from django.db import transaction

    @wraps(view_func)
    @transaction.atomic
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return wrapper


# ===== Feature Flag Decorators =====

def feature_flag(flag_name):
    """
    Decorator to check if a feature flag is enabled.
    Usage: @feature_flag('new_search_ui')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if feature is enabled
            # In production, check against FeatureFlag model or settings
            is_enabled = getattr(settings, f'FEATURE_{flag_name.upper()}', False)

            if not is_enabled:
                messages.warning(request, 'This feature is not currently available.')
                return redirect('storage:dashboard')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# ===== Conditional Decorators =====

def skip_if(condition_func):
    """
    Decorator to skip view execution if condition is met.
    Usage: @skip_if(lambda request: request.user.is_staff)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if condition_func(request):
                return JsonResponse({
                    'skipped': True,
                    'reason': 'Condition met'
                })

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# ===== Utility Decorators =====

def add_context(context_dict):
    """
    Decorator to add extra context to template views.
    Usage: @add_context({'title': 'My Page'})
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)

            # Add context if response has context_data
            if hasattr(response, 'context_data'):
                response.context_data.update(context_dict)

            return response

        return wrapper
    return decorator


def json_response(view_func):
    """
    Decorator to automatically convert dict response to JsonResponse.
    Usage: @json_response
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        result = view_func(request, *args, **kwargs)

        if isinstance(result, dict):
            return JsonResponse(result)

        return result

    return wrapper

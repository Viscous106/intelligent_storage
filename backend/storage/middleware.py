"""
Django Middleware for Intelligent Storage System.
Cross-platform compatible (Windows + Linux).
"""

import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
import os
import platform

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Log all requests with timing information.
    Cross-platform compatible.
    """

    def process_request(self, request):
        """Log request start."""
        request.start_time = time.time()
        request.request_id = self._generate_request_id()

        logger.info(
            f"[{request.request_id}] {request.method} {request.path} "
            f"from {self._get_client_ip(request)}"
        )

    def process_response(self, request, response):
        """Log request completion with timing."""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(
                f"[{getattr(request, 'request_id', 'unknown')}] "
                f"Completed in {duration:.3f}s - Status: {response.status_code}"
            )

        return response

    def _generate_request_id(self):
        """Generate unique request ID (cross-platform)."""
        import uuid
        return str(uuid.uuid4())[:8]

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class StorageQuotaMiddleware(MiddlewareMixin):
    """
    Check storage quotas for file uploads.
    """

    EXEMPT_PATHS = ['/admin/', '/api/health/', '/static/', '/media/']

    def process_request(self, request):
        """Check if request involves file uploads."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
                return None

            # Check if this is a file upload
            if request.FILES:
                total_size = sum(f.size for f in request.FILES.values())

                # Check against system-wide quota (if configured)
                if hasattr(settings, 'MAX_UPLOAD_SIZE'):
                    if total_size > settings.MAX_UPLOAD_SIZE:
                        return JsonResponse({
                            'error': 'Total file size exceeds system limit',
                            'max_size': settings.MAX_UPLOAD_SIZE,
                            'your_size': total_size
                        }, status=413)

        return None


class CORSMiddleware(MiddlewareMixin):
    """
    Custom CORS handling for API endpoints.
    """

    def process_response(self, request, response):
        """Add CORS headers."""
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Access-Control-Max-Age'] = '3600'

        return response


class APIVersionMiddleware(MiddlewareMixin):
    """
    Add API version information to responses.
    """

    def process_response(self, request, response):
        """Add version header to API responses."""
        if request.path.startswith('/api/'):
            response['X-API-Version'] = getattr(settings, 'API_VERSION', '1.0')
            response['X-Server-Platform'] = platform.system()

        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware.
    Uses Django cache (works cross-platform).
    """

    RATE_LIMIT = 100  # requests per minute
    EXEMPT_PATHS = ['/admin/', '/static/', '/media/']

    def process_request(self, request):
        """Check rate limit."""
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return None

        client_ip = self._get_client_ip(request)
        cache_key = f'ratelimit_{client_ip}'

        # Get current request count
        request_count = cache.get(cache_key, 0)

        if request_count >= self.RATE_LIMIT:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'limit': self.RATE_LIMIT,
                'retry_after': 60
            }, status=429)

        # Increment counter
        cache.set(cache_key, request_count + 1, 60)  # 1 minute TTL

        return None

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to responses.
    """

    def process_response(self, request, response):
        """Add security headers."""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Only add HSTS in production
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


class RequestTimingMiddleware(MiddlewareMixin):
    """
    Add timing information to responses.
    """

    def process_request(self, request):
        """Record request start time."""
        request._middleware_start_time = time.time()

    def process_response(self, request, response):
        """Add timing header."""
        if hasattr(request, '_middleware_start_time'):
            duration = time.time() - request._middleware_start_time
            response['X-Request-Duration'] = f'{duration:.3f}s'

        return response


class ErrorLoggingMiddleware(MiddlewareMixin):
    """
    Log errors with detailed information.
    """

    def process_exception(self, request, exception):
        """Log exception details."""
        logger.error(
            f"Exception in {request.method} {request.path}: {str(exception)}",
            exc_info=True,
            extra={
                'request_method': request.method,
                'request_path': request.path,
                'request_user': getattr(request.user, 'username', 'anonymous'),
                'request_ip': self._get_client_ip(request),
                'platform': platform.system(),
            }
        )

        # Return None to let Django handle the exception normally
        return None

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Enable maintenance mode when needed.
    """

    EXEMPT_PATHS = ['/admin/', '/health/']

    def process_request(self, request):
        """Check if maintenance mode is enabled."""
        maintenance_mode = getattr(settings, 'MAINTENANCE_MODE', False)

        if maintenance_mode:
            if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
                return None

            return JsonResponse({
                'error': 'Service temporarily unavailable',
                'message': 'System is under maintenance. Please try again later.',
                'status': 'maintenance'
            }, status=503)

        return None


class CacheControlMiddleware(MiddlewareMixin):
    """
    Add cache control headers based on content type.
    """

    def process_response(self, request, response):
        """Add cache control headers."""
        # Static files
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=31536000'  # 1 year

        # Media files
        elif request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=604800'  # 1 week

        # API responses
        elif request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response


class DatabaseRouterMiddleware(MiddlewareMixin):
    """
    Set database routing hints based on request.
    """

    def process_request(self, request):
        """Set database hints."""
        # This can be used to route read-only requests to read replicas
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            request._db_hint = 'read'
        else:
            request._db_hint = 'write'

        return None


class CompressionMiddleware(MiddlewareMixin):
    """
    Compress responses when appropriate.
    Note: GZipMiddleware is built into Django, use that in production.
    This is a custom implementation for demonstration.
    """

    def process_response(self, request, response):
        """Add compression hint header."""
        if request.path.startswith('/api/'):
            # Check if client accepts gzip
            accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
            if 'gzip' in accept_encoding.lower():
                response['X-Compression-Available'] = 'gzip'

        return response


# ===== Utility Middleware Functions =====

def get_request_metadata(request):
    """
    Extract useful metadata from request (cross-platform).
    """
    return {
        'method': request.method,
        'path': request.path,
        'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
        'ip_address': get_client_ip(request),
        'platform': platform.system(),
        'python_version': platform.python_version(),
    }


def get_client_ip(request):
    """Get client IP address (standalone utility)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_ajax(request):
    """Check if request is AJAX (cross-platform)."""
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

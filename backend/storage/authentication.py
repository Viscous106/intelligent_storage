"""
Django Authentication System for Intelligent Storage.
Custom authentication backends, user models, and authentication utilities.
Cross-platform compatible (Windows + Linux).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with either
    username or email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate user by username or email."""
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        if username is None or password is None:
            return None

        try:
            # Try to fetch user by username first
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Try to fetch user by email
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                # Run the default password hasher once to reduce timing
                # difference between existing and non-existing users
                User().set_password(password)
                return None

        # Check password and active status
        if user.check_password(password) and self.user_can_authenticate(user):
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            logger.info(f'User {user.username} logged in successfully')
            return user

        logger.warning(f'Failed login attempt for username: {username}')
        return None


class APIKeyBackend:
    """
    Custom authentication backend for API key authentication.
    Checks for 'X-API-Key' header in requests.
    """

    def authenticate(self, request, api_key=None, **kwargs):
        """Authenticate user by API key."""
        if api_key is None and request:
            api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            return None

        # Check cache first
        cache_key = f'api_key_{api_key}'
        user_id = cache.get(cache_key)

        if user_id:
            try:
                user = User.objects.get(id=user_id, is_active=True)
                return user
            except User.DoesNotExist:
                cache.delete(cache_key)

        # Check database (assuming you have an APIKey model)
        # For now, this is a placeholder
        # In production, you'd check against APIKey model
        logger.warning(f'API key authentication attempted: {api_key[:8]}...')
        return None

    def get_user(self, user_id):
        """Get user by ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class RateLimitedAuthBackend(ModelBackend):
    """
    Authentication backend with built-in rate limiting to prevent brute force attacks.
    """

    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 300  # 5 minutes in seconds

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate with rate limiting."""
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        if not username:
            return None

        # Check rate limit
        cache_key = f'login_attempts_{username}'
        attempts = cache.get(cache_key, 0)

        if attempts >= self.MAX_ATTEMPTS:
            logger.warning(
                f'Account locked due to too many failed attempts: {username}'
            )
            return None

        # Try authentication
        user = super().authenticate(request, username=username, password=password, **kwargs)

        if user:
            # Clear failed attempts on success
            cache.delete(cache_key)
            return user
        else:
            # Increment failed attempts
            cache.set(cache_key, attempts + 1, self.LOCKOUT_DURATION)
            return None


# ===== Authentication Utilities =====

def get_client_ip(request):
    """Get client IP address from request (cross-platform)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_authentication_event(user, event_type, request=None, details=None):
    """
    Log authentication events.

    Args:
        user: User instance or username string
        event_type: 'login', 'logout', 'failed_login', 'password_change', etc.
        request: HTTP request object (optional)
        details: Additional details dict (optional)
    """
    username = user.username if hasattr(user, 'username') else str(user)
    ip_address = get_client_ip(request) if request else 'unknown'

    log_entry = {
        'username': username,
        'event_type': event_type,
        'ip_address': ip_address,
        'timestamp': timezone.now().isoformat(),
        'details': details or {},
    }

    logger.info(f'Auth Event: {event_type} - User: {username} - IP: {ip_address}')

    # Store in cache for recent activity (last 100 events)
    cache_key = 'recent_auth_events'
    recent_events = cache.get(cache_key, [])
    recent_events.insert(0, log_entry)
    recent_events = recent_events[:100]  # Keep only last 100
    cache.set(cache_key, recent_events, 3600 * 24)  # 24 hours


def check_password_strength(password):
    """
    Check password strength.

    Returns:
        dict: {
            'is_strong': bool,
            'score': int (0-100),
            'issues': list of str
        }
    """
    issues = []
    score = 0

    # Length check
    if len(password) >= 8:
        score += 20
    else:
        issues.append('Password must be at least 8 characters')

    if len(password) >= 12:
        score += 10

    # Character variety checks
    if any(c.islower() for c in password):
        score += 20
    else:
        issues.append('Password must contain lowercase letters')

    if any(c.isupper() for c in password):
        score += 20
    else:
        issues.append('Password must contain uppercase letters')

    if any(c.isdigit() for c in password):
        score += 20
    else:
        issues.append('Password must contain numbers')

    if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        score += 10
    else:
        issues.append('Password should contain special characters')

    is_strong = score >= 70 and len(issues) == 0

    return {
        'is_strong': is_strong,
        'score': score,
        'issues': issues,
    }


def generate_api_key():
    """Generate a random API key."""
    import secrets
    return secrets.token_urlsafe(32)


def verify_api_key(api_key, user_id):
    """
    Verify API key for a specific user.

    Args:
        api_key: The API key to verify
        user_id: The user ID to verify against

    Returns:
        bool: True if valid, False otherwise
    """
    # This is a placeholder - in production you'd check against APIKey model
    cache_key = f'api_key_{api_key}'
    cached_user_id = cache.get(cache_key)

    if cached_user_id == user_id:
        return True

    # Check database
    # In production: return APIKey.objects.filter(key=api_key, user_id=user_id, is_active=True).exists()
    return False


def get_user_permissions(user):
    """
    Get all permissions for a user.
    Cached for performance.

    Args:
        user: User instance

    Returns:
        set: Set of permission strings
    """
    if not user.is_authenticated:
        return set()

    cache_key = f'user_permissions_{user.id}'
    permissions = cache.get(cache_key)

    if permissions is None:
        # Get user permissions
        permissions = set(
            user.user_permissions.values_list('codename', flat=True)
        )

        # Get group permissions
        group_permissions = set(
            user.groups.values_list('permissions__codename', flat=True)
        )

        permissions.update(group_permissions)

        # Superusers have all permissions
        if user.is_superuser:
            from django.contrib.auth.models import Permission
            all_permissions = Permission.objects.values_list('codename', flat=True)
            permissions = set(all_permissions)

        # Cache for 5 minutes
        cache.set(cache_key, permissions, 300)

    return permissions


def invalidate_user_cache(user):
    """
    Invalidate all cached data for a user.
    Call this when user permissions or groups change.

    Args:
        user: User instance
    """
    cache_keys = [
        f'user_permissions_{user.id}',
        f'user_profile_{user.id}',
        f'user_stores_{user.id}',
    ]

    for key in cache_keys:
        cache.delete(key)

    logger.info(f'Cache invalidated for user: {user.username}')


# ===== Session Management =====

def get_active_sessions(user):
    """
    Get all active sessions for a user.

    Args:
        user: User instance

    Returns:
        list: List of session data dictionaries
    """
    from django.contrib.sessions.models import Session
    from django.contrib.auth.models import AnonymousUser

    sessions = []
    user_sessions = Session.objects.filter(
        expire_date__gte=timezone.now()
    )

    for session in user_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.id):
            sessions.append({
                'session_key': session.session_key,
                'expire_date': session.expire_date,
                'data': session_data,
            })

    return sessions


def revoke_all_sessions(user):
    """
    Revoke all sessions for a user (force logout everywhere).

    Args:
        user: User instance

    Returns:
        int: Number of sessions revoked
    """
    from django.contrib.sessions.models import Session

    count = 0
    user_sessions = Session.objects.filter(
        expire_date__gte=timezone.now()
    )

    for session in user_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.id):
            session.delete()
            count += 1

    logger.info(f'Revoked {count} sessions for user: {user.username}')
    return count


# ===== Two-Factor Authentication (Placeholder) =====

def generate_totp_secret():
    """Generate a TOTP secret for two-factor authentication."""
    import secrets
    return secrets.token_hex(16)


def verify_totp_token(secret, token):
    """
    Verify a TOTP token.

    Args:
        secret: The TOTP secret
        token: The 6-digit token to verify

    Returns:
        bool: True if valid, False otherwise
    """
    # This is a placeholder - in production use pyotp library
    # import pyotp
    # totp = pyotp.TOTP(secret)
    # return totp.verify(token)
    return False

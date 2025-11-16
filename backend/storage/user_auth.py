"""
Multi-User Authentication System(Future Implementation(work-in-progress))

Provides JWT-based authentication for regular users with:
- User registration
- User login/logout
- Profile management
- Token-based authentication
- Data isolation per user
"""

import jwt
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from .models import User

logger = logging.getLogger(__name__)

# JWT Settings
JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 24


class UserAuthManager:
    """
    Manages user authentication with JWT tokens

    Features:
    - User registration with email verification
    - JWT token generation and validation
    - Password hashing (Django's built-in)
    - User profile management
    - Storage quota management
    """

    @staticmethod
    def create_jwt_token(user: User, expiry_hours: int = JWT_EXPIRY_HOURS) -> str:
        """
        Create JWT token for user

        Args:
            user: User instance
            expiry_hours: Token expiration time in hours

        Returns:
            JWT token string
        """
        payload = {
            'user_id': str(user.user_id),
            'email': user.email,
            'username': user.username,
            'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
            'iat': datetime.utcnow()
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    @staticmethod
    def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """
        Get user instance from JWT token

        Args:
            token: JWT token string

        Returns:
            User instance or None
        """
        payload = UserAuthManager.decode_jwt_token(token)
        if not payload:
            return None

        try:
            user = User.objects.get(user_id=payload['user_id'], is_active=True)
            return user
        except User.DoesNotExist:
            return None


def require_user(func):
    """
    Decorator to require user authentication for views

    Usage:
        @require_user
        def my_view(request, user):
            # user is automatically injected
            pass
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Get token from header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'success': False,
                'error': 'Missing or invalid authorization header'
            }, status=401)

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        # Validate token and get user
        user = UserAuthManager.get_user_from_token(token)

        if not user:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or expired token'
            }, status=401)

        # Inject user into kwargs
        kwargs['user'] = user

        return func(request, *args, **kwargs)

    return wrapper


# ========== User Authentication Views ==========

@csrf_exempt
@require_http_methods(["POST"])
def user_register(request):
    """
    Register a new user

    POST /api/users/register
    Content-Type: application/json

    Body:
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "secure_password",
        "full_name": "John Doe",  // optional
        "phone": "+1234567890"      // optional
    }

    Response:
    {
        "success": true,
        "user_id": "uuid",
        "username": "john_doe",
        "email": "john@example.com",
        "token": "jwt_token",
        "message": "User registered successfully"
    }
    """
    try:
        import json
        data = json.loads(request.body)

        # Validate required fields
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not username or not email or not password:
            return JsonResponse({
                'success': False,
                'error': 'Username, email, and password are required'
            }, status=400)

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'error': 'Username already exists'
            }, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Email already registered'
            }, status=400)

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            full_name=data.get('full_name', ''),
            phone=data.get('phone', ''),
            is_active=True,
            is_verified=False  # Email verification can be added later
        )

        # Generate JWT token
        token = UserAuthManager.create_jwt_token(user)

        # Update last login
        user.last_login = timezone.now()
        user.save()

        logger.info(f"New user registered: {username} ({user.user_id})")

        return JsonResponse({
            'success': True,
            'user_id': str(user.user_id),
            'username': user.username,
            'email': user.email,
            'token': token,
            'storage_quota': user.storage_quota,
            'storage_used': user.storage_used,
            'message': 'User registered successfully'
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def user_login(request):
    """
    Login user and get JWT token

    POST /api/users/login
    Content-Type: application/json

    Body:
    {
        "email": "john@example.com",
        "password": "secure_password"
    }

    Response:
    {
        "success": true,
        "user_id": "uuid",
        "username": "john_doe",
        "email": "john@example.com",
        "token": "jwt_token",
        "message": "Login successful"
    }
    """
    try:
        import json
        data = json.loads(request.body)

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return JsonResponse({
                'success': False,
                'error': 'Email and password are required'
            }, status=400)

        # Get user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid credentials'
            }, status=401)

        # Check if user is active
        if not user.is_active:
            return JsonResponse({
                'success': False,
                'error': 'Account is disabled'
            }, status=401)

        # Verify password
        if not user.check_password(password):
            return JsonResponse({
                'success': False,
                'error': 'Invalid credentials'
            }, status=401)

        # Generate JWT token
        token = UserAuthManager.create_jwt_token(user)

        # Update last login
        user.last_login = timezone.now()
        user.save()

        logger.info(f"User logged in: {user.username} ({user.user_id})")

        return JsonResponse({
            'success': True,
            'user_id': str(user.user_id),
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'token': token,
            'storage_quota': user.storage_quota,
            'storage_used': user.storage_used,
            'storage_used_percentage': user.storage_used_percentage,
            'message': 'Login successful'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_user
def user_logout(request, user):
    """
    Logout user (client-side token removal)

    POST /api/users/logout
    Authorization: Bearer <token>

    Response:
    {
        "success": true,
        "message": "Logged out successfully"
    }
    """
    logger.info(f"User logged out: {user.username} ({user.user_id})")

    return JsonResponse({
        'success': True,
        'message': 'Logged out successfully'
    })


@csrf_exempt
@require_http_methods(["GET"])
@require_user
def user_profile(request, user):
    """
    Get user profile information

    GET /api/users/profile
    Authorization: Bearer <token>

    Response:
    {
        "success": true,
        "user": {
            "user_id": "uuid",
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "phone": "+1234567890",
            "storage_quota": 5368709120,
            "storage_used": 12345678,
            "storage_used_percentage": 0.23,
            "is_verified": false,
            "created_at": "2025-01-15T10:30:00Z",
            "last_login": "2025-01-16T08:15:00Z"
        }
    }
    """
    return JsonResponse({
        'success': True,
        'user': {
            'user_id': str(user.user_id),
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'phone': user.phone,
            'storage_quota': user.storage_quota,
            'storage_used': user.storage_used,
            'storage_used_percentage': round(user.storage_used_percentage, 2),
            'is_verified': user.is_verified,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'metadata': user.metadata
        }
    })


@csrf_exempt
@require_http_methods(["PUT"])
@require_user
def update_profile(request, user):
    """
    Update user profile

    PUT /api/users/profile
    Authorization: Bearer <token>
    Content-Type: application/json

    Body:
    {
        "full_name": "John Smith",
        "phone": "+1234567890",
        "metadata": {"key": "value"}
    }

    Response:
    {
        "success": true,
        "message": "Profile updated successfully"
    }
    """
    try:
        import json
        data = json.loads(request.body)

        # Update allowed fields
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'metadata' in data and isinstance(data['metadata'], dict):
            user.metadata.update(data['metadata'])

        user.save()

        logger.info(f"Profile updated for user: {user.username} ({user.user_id})")

        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Profile update error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_user
def change_password(request, user):
    """
    Change user password

    POST /api/users/change-password
    Authorization: Bearer <token>
    Content-Type: application/json

    Body:
    {
        "current_password": "old_password",
        "new_password": "new_password"
    }

    Response:
    {
        "success": true,
        "message": "Password changed successfully"
    }
    """
    try:
        import json
        data = json.loads(request.body)

        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return JsonResponse({
                'success': False,
                'error': 'Current password and new password are required'
            }, status=400)

        # Verify current password
        if not user.check_password(current_password):
            return JsonResponse({
                'success': False,
                'error': 'Current password is incorrect'
            }, status=400)

        # Set new password
        user.set_password(new_password)
        user.save()

        logger.info(f"Password changed for user: {user.username} ({user.user_id})")

        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Password change error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

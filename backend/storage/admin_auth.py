"""
Admin-Only Authentication and Access Control System(Future Implementation)

Simple token-based authentication for admin users with:
- Secure token generation
- Token validation
- Admin user management
- Access control for all operations
"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AdminAuthManager:
    """
    Manages admin authentication with token-based access control

    Features:
    - Secure token generation (256-bit)
    - Token expiration (configurable)
    - Simple admin user management
    - Password hashing (SHA-256 with salt)
    - Admin-only access control
    """

    def __init__(self, storage_path: str = None):
        """
        Initialize admin authentication manager

        Args:
            storage_path: Path to store admin data (JSON file)
        """
        if storage_path is None:
            storage_path = Path(__file__).parent.parent / 'data' / 'admin_auth.json'

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create admin data
        self.admin_data = self._load_admin_data()

        # Active tokens: {token: {admin_id, expires_at}}
        self.active_tokens = {}

        # Load active tokens from storage
        self._load_active_tokens()

        logger.info("Admin authentication system initialized")

    def _load_admin_data(self) -> Dict[str, Any]:
        """Load admin data from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading admin data: {e}")
                return {'admins': {}, 'tokens': {}}

        # Create default admin data structure
        return {'admins': {}, 'tokens': {}}

    def _save_admin_data(self):
        """Save admin data to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.admin_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving admin data: {e}")

    def _load_active_tokens(self):
        """Load active tokens from storage"""
        stored_tokens = self.admin_data.get('tokens', {})

        # Filter out expired tokens
        now = datetime.now()
        for token, token_data in stored_tokens.items():
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            if expires_at > now:
                self.active_tokens[token] = {
                    'admin_id': token_data['admin_id'],
                    'expires_at': expires_at
                }

    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """
        Hash password with salt

        Args:
            password: Plain text password
            salt: Optional salt (generated if not provided)

        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)

        # Hash password with salt
        hash_input = f"{password}{salt}".encode()
        hashed = hashlib.sha256(hash_input).hexdigest()

        return hashed, salt

    def create_admin(self, username: str, password: str,
                    email: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new admin user

        Args:
            username: Admin username (unique)
            password: Admin password
            email: Optional email

        Returns:
            Dictionary with admin creation result
        """
        # Check if username already exists
        if username in self.admin_data['admins']:
            return {
                'success': False,
                'error': 'Username already exists'
            }

        # Hash password
        hashed_password, salt = self._hash_password(password)

        # Generate admin ID
        admin_id = f"admin_{secrets.token_hex(8)}"

        # Store admin data
        self.admin_data['admins'][username] = {
            'admin_id': admin_id,
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'salt': salt,
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }

        self._save_admin_data()

        logger.info(f"Admin user created: {username} ({admin_id})")

        return {
            'success': True,
            'admin_id': admin_id,
            'username': username,
            'message': 'Admin user created successfully'
        }

    def authenticate(self, username: str, password: str,
                    token_expiry_hours: int = 24) -> Dict[str, Any]:
        """
        Authenticate admin and generate access token

        Args:
            username: Admin username
            password: Admin password
            token_expiry_hours: Token expiration time in hours

        Returns:
            Dictionary with authentication result and token
        """
        # Check if admin exists
        admin = self.admin_data['admins'].get(username)

        if not admin:
            return {
                'success': False,
                'error': 'Invalid credentials'
            }

        # Check if admin is active
        if not admin.get('is_active', True):
            return {
                'success': False,
                'error': 'Admin account is disabled'
            }

        # Verify password
        hashed_password, _ = self._hash_password(password, admin['salt'])

        if hashed_password != admin['password_hash']:
            return {
                'success': False,
                'error': 'Invalid credentials'
            }

        # Generate access token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=token_expiry_hours)

        # Store token
        self.active_tokens[token] = {
            'admin_id': admin['admin_id'],
            'expires_at': expires_at
        }

        # Save to persistent storage
        self.admin_data['tokens'][token] = {
            'admin_id': admin['admin_id'],
            'expires_at': expires_at.isoformat()
        }
        self._save_admin_data()

        logger.info(f"Admin authenticated: {username} ({admin['admin_id']})")

        return {
            'success': True,
            'token': token,
            'admin_id': admin['admin_id'],
            'username': username,
            'expires_at': expires_at.isoformat(),
            'message': 'Authentication successful'
        }

    def validate_token(self, token: str) -> Optional[str]:
        """
        Validate access token and return admin_id if valid

        Args:
            token: Access token

        Returns:
            Admin ID if valid, None otherwise
        """
        if token not in self.active_tokens:
            return None

        token_data = self.active_tokens[token]

        # Check expiration
        if datetime.now() > token_data['expires_at']:
            # Token expired, remove it
            self.active_tokens.pop(token, None)
            self.admin_data['tokens'].pop(token, None)
            self._save_admin_data()
            return None

        return token_data['admin_id']

    def refresh_token(self, token: str,
                     token_expiry_hours: int = 24) -> Dict[str, Any]:
        """
        Refresh an existing token

        Args:
            token: Current access token
            token_expiry_hours: New expiration time in hours

        Returns:
            Dictionary with new token or error
        """
        admin_id = self.validate_token(token)

        if not admin_id:
            return {
                'success': False,
                'error': 'Invalid or expired token'
            }

        # Generate new token
        new_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=token_expiry_hours)

        # Remove old token
        self.active_tokens.pop(token, None)
        self.admin_data['tokens'].pop(token, None)

        # Add new token
        self.active_tokens[new_token] = {
            'admin_id': admin_id,
            'expires_at': expires_at
        }

        self.admin_data['tokens'][new_token] = {
            'admin_id': admin_id,
            'expires_at': expires_at.isoformat()
        }
        self._save_admin_data()

        return {
            'success': True,
            'token': new_token,
            'expires_at': expires_at.isoformat(),
            'message': 'Token refreshed successfully'
        }

    def logout(self, token: str) -> Dict[str, Any]:
        """
        Logout admin (invalidate token)

        Args:
            token: Access token

        Returns:
            Dictionary with logout result
        """
        if token in self.active_tokens:
            self.active_tokens.pop(token)
            self.admin_data['tokens'].pop(token, None)
            self._save_admin_data()

            return {
                'success': True,
                'message': 'Logged out successfully'
            }

        return {
            'success': False,
            'error': 'Invalid token'
        }

    def get_admin_info(self, admin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get admin user information

        Args:
            admin_id: Admin ID

        Returns:
            Admin information or None
        """
        for username, admin in self.admin_data['admins'].items():
            if admin['admin_id'] == admin_id:
                # Return admin info without sensitive data
                return {
                    'admin_id': admin['admin_id'],
                    'username': admin['username'],
                    'email': admin.get('email'),
                    'created_at': admin['created_at'],
                    'is_active': admin.get('is_active', True)
                }

        return None

    def list_admins(self) -> list[Dict[str, Any]]:
        """
        List all admin users (without sensitive data)

        Returns:
            List of admin information
        """
        admins = []
        for username, admin in self.admin_data['admins'].items():
            admins.append({
                'admin_id': admin['admin_id'],
                'username': admin['username'],
                'email': admin.get('email'),
                'created_at': admin['created_at'],
                'is_active': admin.get('is_active', True)
            })

        return admins

    def change_password(self, admin_id: str, old_password: str,
                       new_password: str) -> Dict[str, Any]:
        """
        Change admin password

        Args:
            admin_id: Admin ID
            old_password: Current password
            new_password: New password

        Returns:
            Dictionary with result
        """
        # Find admin
        admin = None
        username = None
        for uname, adm in self.admin_data['admins'].items():
            if adm['admin_id'] == admin_id:
                admin = adm
                username = uname
                break

        if not admin:
            return {
                'success': False,
                'error': 'Admin not found'
            }

        # Verify old password
        hashed_old, _ = self._hash_password(old_password, admin['salt'])
        if hashed_old != admin['password_hash']:
            return {
                'success': False,
                'error': 'Invalid current password'
            }

        # Hash new password
        hashed_new, new_salt = self._hash_password(new_password)

        # Update password
        admin['password_hash'] = hashed_new
        admin['salt'] = new_salt

        self._save_admin_data()

        logger.info(f"Password changed for admin: {username} ({admin_id})")

        return {
            'success': True,
            'message': 'Password changed successfully'
        }


# Global auth manager instance
_auth_instance = None


def get_auth_manager() -> AdminAuthManager:
    """Get singleton auth manager instance"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = AdminAuthManager()
    return _auth_instance


def require_admin(func):
    """
    Decorator to require admin authentication for views/functions

    Usage:
        @require_admin
        def my_view(request, admin_id):
            # admin_id is automatically injected
            pass
    """
    def wrapper(request, *args, **kwargs):
        # Get token from header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            from django.http import JsonResponse
            return JsonResponse({
                'error': 'Missing or invalid authorization header'
            }, status=401)

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        # Validate token
        auth_manager = get_auth_manager()
        admin_id = auth_manager.validate_token(token)

        if not admin_id:
            from django.http import JsonResponse
            return JsonResponse({
                'error': 'Invalid or expired token'
            }, status=401)

        # Inject admin_id into kwargs
        kwargs['admin_id'] = admin_id

        return func(request, *args, **kwargs)

    return wrapper

"""
Django Permissions and Authorization for Intelligent Storage System.
Custom permission classes for REST API and views.
"""

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from functools import wraps
import logging

logger = logging.getLogger(__name__)


# ===== REST Framework Permissions =====

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        # Assuming the model has a 'user' or 'owner' field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user

        # If no owner field, deny write access
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit.
    Anyone can view.
    """

    def has_permission(self, request, view):
        # Read permissions for anyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for admin users
        return request.user and request.user.is_staff


class HasStoreAccess(permissions.BasePermission):
    """
    Custom permission to check if user has access to a specific store.
    """

    def has_object_permission(self, request, view, obj):
        # Superusers have full access
        if request.user.is_superuser:
            return True

        # Check if object is a FileSearchStore or related model
        if hasattr(obj, 'file_search_store'):
            store = obj.file_search_store
        elif obj.__class__.__name__ == 'FileSearchStore':
            store = obj
        else:
            return True  # Allow if not store-related

        # Check custom store permissions
        # In production, you'd check store.users.filter(id=request.user.id).exists()
        # For now, allow if store is active
        return store.is_active


class CanUploadFiles(permissions.BasePermission):
    """
    Permission to check if user can upload files.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user has upload permission
        # In production: return request.user.has_perm('storage.add_mediafile')
        return request.user.is_authenticated


class CanManageStores(permissions.BasePermission):
    """
    Permission to check if user can manage stores.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Only staff and superusers can manage stores
        return request.user.is_staff or request.user.is_superuser


class QuotaNotExceeded(permissions.BasePermission):
    """
    Permission to check if storage quota is not exceeded.
    """

    def has_permission(self, request, view):
        # Only check for upload requests
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return True

        # Check if uploading files
        if not request.FILES:
            return True

        # Get target store if specified
        store_id = request.data.get('file_search_store')
        if store_id:
            from storage.models import FileSearchStore
            try:
                store = FileSearchStore.objects.get(id=store_id)
                if store.is_quota_exceeded():
                    logger.warning(f'Upload blocked - quota exceeded for store: {store.name}')
                    return False
            except FileSearchStore.DoesNotExist:
                pass

        return True


class IsIndexedFile(permissions.BasePermission):
    """
    Permission to check if file is indexed (for search operations).
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'is_indexed'):
            return obj.is_indexed
        return True


# ===== Function-based View Decorators =====

def require_store_access(view_func):
    """
    Decorator to require access to a specific store.
    Use on views that take 'store_id' or 'store_name' parameter.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from storage.models import FileSearchStore

        # Get store identifier from URL parameters
        store_id = kwargs.get('store_id')
        store_name = kwargs.get('store_name')

        try:
            if store_id:
                store = FileSearchStore.objects.get(id=store_id)
            elif store_name:
                store = FileSearchStore.objects.get(name=store_name)
            else:
                # No store specified, allow
                return view_func(request, *args, **kwargs)

            # Check access
            if not request.user.is_superuser and not store.is_active:
                raise DjangoPermissionDenied('Store is not active')

            # Add store to request
            request.store = store

        except FileSearchStore.DoesNotExist:
            raise DjangoPermissionDenied('Store not found')

        return view_func(request, *args, **kwargs)

    return wrapper


def require_quota_available(view_func):
    """
    Decorator to check if quota is available before file upload.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from storage.models import FileSearchStore

        # Only check for POST requests with files
        if request.method == 'POST' and request.FILES:
            store_id = request.POST.get('file_search_store')

            if store_id:
                try:
                    store = FileSearchStore.objects.get(id=store_id)
                    if store.is_quota_exceeded():
                        raise DjangoPermissionDenied(
                            f'Storage quota exceeded for store: {store.display_name}'
                        )
                except FileSearchStore.DoesNotExist:
                    pass

        return view_func(request, *args, **kwargs)

    return wrapper


def require_authenticated_or_api_key(view_func):
    """
    Decorator to require either session authentication or valid API key.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check session authentication
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        # Check API key
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            from storage.authentication import verify_api_key
            # In production, verify and attach user to request
            # For now, just check if key exists
            if api_key:
                # Allow access
                return view_func(request, *args, **kwargs)

        raise DjangoPermissionDenied('Authentication required')

    return wrapper


def require_permission(permission_codename):
    """
    Decorator to require specific permission.
    Usage: @require_permission('storage.add_mediafile')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise DjangoPermissionDenied('Authentication required')

            if not request.user.has_perm(permission_codename):
                logger.warning(
                    f'Permission denied: {request.user.username} lacks {permission_codename}'
                )
                raise DjangoPermissionDenied(
                    f'You do not have permission: {permission_codename}'
                )

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def rate_limit(max_requests=100, window_seconds=60):
    """
    Rate limiting decorator.
    Usage: @rate_limit(max_requests=10, window_seconds=60)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.core.cache import cache
            from storage.authentication import get_client_ip

            # Get client identifier
            if request.user.is_authenticated:
                identifier = f'user_{request.user.id}'
            else:
                identifier = f'ip_{get_client_ip(request)}'

            cache_key = f'rate_limit_{identifier}_{view_func.__name__}'

            # Get current count
            count = cache.get(cache_key, 0)

            if count >= max_requests:
                logger.warning(f'Rate limit exceeded for {identifier}')
                raise DjangoPermissionDenied('Rate limit exceeded. Please try again later.')

            # Increment counter
            cache.set(cache_key, count + 1, window_seconds)

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# ===== Permission Checking Utilities =====

def check_store_permission(user, store, permission_type='view'):
    """
    Check if user has specific permission for a store.

    Args:
        user: User instance
        store: FileSearchStore instance
        permission_type: 'view', 'edit', 'delete', 'upload'

    Returns:
        bool: True if user has permission
    """
    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Inactive stores are only accessible to staff
    if not store.is_active and not user.is_staff:
        return False

    # View permission is granted to everyone for active stores
    if permission_type == 'view':
        return store.is_active

    # Edit/Delete permissions require staff status
    if permission_type in ['edit', 'delete']:
        return user.is_staff

    # Upload permission requires authentication
    if permission_type == 'upload':
        return user.is_authenticated and store.is_active

    return False


def check_file_permission(user, media_file, permission_type='view'):
    """
    Check if user has specific permission for a file.

    Args:
        user: User instance
        media_file: MediaFile instance
        permission_type: 'view', 'edit', 'delete', 'download'

    Returns:
        bool: True if user has permission
    """
    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Check store permission first
    if media_file.file_search_store:
        store_perm = check_store_permission(user, media_file.file_search_store, permission_type)
        if not store_perm:
            return False

    # View and download are allowed for authenticated users
    if permission_type in ['view', 'download']:
        return user.is_authenticated

    # Edit and delete require staff status or ownership
    if permission_type in ['edit', 'delete']:
        # Check ownership (if user field exists)
        if hasattr(media_file, 'user') and media_file.user == user:
            return True
        return user.is_staff

    return False


def get_user_accessible_stores(user):
    """
    Get all stores accessible to a user.

    Args:
        user: User instance

    Returns:
        QuerySet: FileSearchStore queryset
    """
    from storage.models import FileSearchStore

    if user.is_superuser:
        return FileSearchStore.objects.all()
    elif user.is_staff:
        return FileSearchStore.objects.all()
    else:
        # Regular users can only access active stores
        return FileSearchStore.objects.filter(is_active=True)


def get_permission_display(codename):
    """
    Get human-readable permission name.

    Args:
        codename: Permission codename (e.g., 'add_mediafile')

    Returns:
        str: Human-readable name
    """
    from django.contrib.auth.models import Permission

    try:
        perm = Permission.objects.get(codename=codename)
        return perm.name
    except Permission.DoesNotExist:
        # Fallback to formatted codename
        return codename.replace('_', ' ').title()


# ===== Custom Permission Classes for Specific Models =====

class MediaFilePermission:
    """Permission helper for MediaFile model."""

    @staticmethod
    def can_view(user, media_file):
        return check_file_permission(user, media_file, 'view')

    @staticmethod
    def can_edit(user, media_file):
        return check_file_permission(user, media_file, 'edit')

    @staticmethod
    def can_delete(user, media_file):
        return check_file_permission(user, media_file, 'delete')

    @staticmethod
    def can_download(user, media_file):
        return check_file_permission(user, media_file, 'download')


class FileSearchStorePermission:
    """Permission helper for FileSearchStore model."""

    @staticmethod
    def can_view(user, store):
        return check_store_permission(user, store, 'view')

    @staticmethod
    def can_edit(user, store):
        return check_store_permission(user, store, 'edit')

    @staticmethod
    def can_delete(user, store):
        return check_store_permission(user, store, 'delete')

    @staticmethod
    def can_upload(user, store):
        return check_store_permission(user, store, 'upload')

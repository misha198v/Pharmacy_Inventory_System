from rest_framework import permissions


class IsManager(permissions.BasePermission):
    """Authenticated users with the 'manager' role (or superusers) only."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            return request.user.userprofile.role == 'manager'
        except Exception:
            return False


class IsManagerOrReadOnly(permissions.BasePermission):
    """
    Everything requires login.
    GET/HEAD/OPTIONS: any logged-in user.
    POST (create): any logged-in user.
    PUT/PATCH/DELETE: managers (or superusers) only.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == 'POST':
            return True

        if request.user.is_superuser:
            return True

        try:
            return request.user.userprofile.role == 'manager'
        except Exception:
            return False
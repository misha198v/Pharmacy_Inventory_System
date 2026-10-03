from rest_framework import permissions


class IsManager(permissions.BasePermission):
    """Allows access only to authenticated users with the 'manager' role."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.userprofile.role == 'manager'
        except Exception:
            return False


class IsManagerOrReadOnly(permissions.BasePermission):
    """
    GET/HEAD/OPTIONS (read): any authenticated user.
    POST (create): any authenticated user.
    PUT/PATCH/DELETE (edit/delete): manager role only.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == 'POST':
            return True

        # PUT, PATCH, DELETE all require manager role
        try:
            return request.user.userprofile.role == 'manager'
        except Exception:
            return False
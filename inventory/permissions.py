from rest_framework import permissions

class IsManagerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        if not request.user.is_authenticated:
            return False

        try:
            return request.user.userprofile.role == "manager"
        except Exception:
            return False
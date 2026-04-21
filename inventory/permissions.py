from rest_framework import permissions

class IsManagerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Anyone logged in can see (GET)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only Managers can Delete (DELETE)
        if request.method == 'DELETE':
            return request.user.groups.filter(name='Manager').exists()
        return True
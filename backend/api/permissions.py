from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
                request.method in SAFE_METHODS
                or request.user.is_authenticated
                and (request.user.is_staff
                     or obj.author == request.user)
        )
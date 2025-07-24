from rest_framework.permissions import BasePermission


class IsAuthorOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.method in ['GET', 'HEAD', 'OPTIONS']
            or request.user.is_authenticated
            and (request.user.is_staff
                 or obj.author == request.user)
        )

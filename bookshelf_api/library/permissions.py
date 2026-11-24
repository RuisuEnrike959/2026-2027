from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrReadOnlyApiStaff(BasePermission):
    message = "Only API staff can read the API; administrators have full access."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if request.method in SAFE_METHODS:
            return user.groups.filter(name="API Staff").exists()
        return False

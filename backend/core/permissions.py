"""
Role-based DRF permissions for the Breathe ESG platform.
"""

from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Only super-admin users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "super_admin"
        )


class IsAdminOrAbove(BasePermission):
    """Super-admin or tenant admin."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("super_admin", "admin")
        )


class IsAnalystOrAbove(BasePermission):
    """Super-admin, admin, or analyst."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("super_admin", "admin", "analyst")
        )


class IsTenantMember(BasePermission):
    """
    Ensures the authenticated user belongs to the same tenant as the
    resource being accessed.  Super-admins bypass this check.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == "super_admin":
            return True
        obj_tenant = getattr(obj, "tenant_id", None) or getattr(obj, "tenant", None)
        return obj_tenant == request.user.tenant_id

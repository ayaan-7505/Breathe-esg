"""
Tenant-aware middleware.

Attaches ``request.tenant`` for authenticated users so downstream code
can filter querysets without manually looking up the tenant each time.
"""

from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    """
    After authentication, reads the user's tenant and pins it to
    ``request.tenant``.  Anonymous / super-admin requests get ``None``.
    """

    def process_request(self, request):
        if hasattr(request, "user") and request.user.is_authenticated:
            request.tenant = getattr(request.user, "tenant", None)
        else:
            request.tenant = None

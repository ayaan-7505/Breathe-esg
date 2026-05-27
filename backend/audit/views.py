"""Audit views — read-only list of audit log entries."""

from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/audit/
    Returns audit log entries scoped to the user's tenant.
    Super-admins see everything.
    """

    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "entity_type", "entity_id", "user"]
    ordering_fields = ["timestamp"]

    def get_queryset(self):
        user = self.request.user
        qs = AuditLog.objects.select_related("user")
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)

        # 1. Date filters
        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        # 2. Search query
        search = self.request.query_params.get("search")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(action__icontains=search) |
                Q(entity_id__icontains=search)
            )

        return qs

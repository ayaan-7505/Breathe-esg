"""Audit serializers."""

from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id", "tenant", "user", "user_username", "action",
            "entity_type", "entity_id", "changes", "metadata", "timestamp",
        ]
        read_only_fields = fields  # audit logs are immutable

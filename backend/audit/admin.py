"""Audit admin — read-only in Django admin."""

from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "action", "entity_type", "entity_id", "user", "tenant"]
    list_filter = ["action", "entity_type"]
    search_fields = ["entity_id", "entity_type"]
    readonly_fields = [
        "id", "tenant", "user", "action", "entity_type",
        "entity_id", "changes", "metadata", "timestamp",
    ]
    ordering = ["-timestamp"]

    def has_add_permission(self, request):
        return False  # Audit logs are append-only via code

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

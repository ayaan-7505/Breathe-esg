"""
AuditLog model — immutable record of every mutation in the system.

Each entry captures:
- who performed the action
- what entity was affected (via generic content_type + object_id)
- what changed (JSON diff of old vs new values)
- when it happened
"""

import uuid
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Append-only audit trail entry.

    Entries are created by Django signals (see ``audit.signals``) or
    explicitly via ``AuditLog.log()`` helper.
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        STATUS_CHANGE = "status_change", "Status Change"
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        FLAG = "flag", "Flag"
        LOCK = "lock", "Lock"
        UPLOAD = "upload", "Upload"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    entity_type = models.CharField(
        max_length=100,
        help_text="App label + model name, e.g. 'emissions.EmissionRecord'",
    )
    entity_id = models.CharField(
        max_length=255,
        help_text="PK of the affected object (stringified UUID).",
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON diff: {field: {old: ..., new: ...}}",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary extra context (e.g. reason for flagging).",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["tenant", "timestamp"]),
        ]

    def __str__(self):
        return f"[{self.action}] {self.entity_type}:{self.entity_id} by {self.user}"

    # ------------------------------------------------------------------
    # Convenience helper
    # ------------------------------------------------------------------
    @classmethod
    def log(
        cls,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        tenant=None,
        user=None,
        changes: dict | None = None,
        metadata: dict | None = None,
    ):
        """Create an audit entry in one call."""
        return cls.objects.create(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            tenant=tenant,
            user=user,
            changes=changes or {},
            metadata=metadata or {},
        )

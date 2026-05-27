"""
Django signals for automatic audit-log creation.

Listens to post_save and post_delete on key models:
- emissions.EmissionRecord
- ingestion.IngestionJob

The signals compare old vs new field values and write an AuditLog entry.
"""

import json
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from .models import AuditLog

# -----------------------------------------------------------------------
# We store pre-save snapshots on the instance so post_save can diff them.
# -----------------------------------------------------------------------
_TRACKED_MODELS = set()


def register_audited_model(model_class):
    """
    Call this at app-ready time to register a model for automatic
    audit tracking via signals.
    """
    _TRACKED_MODELS.add(model_class)


def _serializable(value):
    """Coerce a model field value to something JSON-safe."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


@receiver(pre_save)
def _snapshot_before_save(sender, instance, **kwargs):
    """Capture field values before save for diffing."""
    if sender not in _TRACKED_MODELS:
        return
    if not instance.pk:
        instance._audit_is_new = True
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_is_new = True
        return
    instance._audit_is_new = False
    instance._audit_old_values = {
        f.attname: _serializable(getattr(old, f.attname))
        for f in sender._meta.fields
    }


@receiver(post_save)
def _audit_post_save(sender, instance, created, **kwargs):
    """Write an AuditLog entry after a tracked model is saved."""
    if sender not in _TRACKED_MODELS:
        return

    entity_type = f"{sender._meta.app_label}.{sender.__name__}"
    tenant = getattr(instance, "tenant", None)

    if created or getattr(instance, "_audit_is_new", True):
        AuditLog.log(
            action=AuditLog.Action.CREATE,
            entity_type=entity_type,
            entity_id=str(instance.pk),
            tenant=tenant,
        )
        return

    # Compute diff
    old_vals = getattr(instance, "_audit_old_values", {})
    changes = {}
    for field in sender._meta.fields:
        new_val = _serializable(getattr(instance, field.attname))
        old_val = old_vals.get(field.attname)
        if new_val != old_val:
            changes[field.name] = {"old": old_val, "new": new_val}

    if changes:
        AuditLog.log(
            action=AuditLog.Action.UPDATE,
            entity_type=entity_type,
            entity_id=str(instance.pk),
            tenant=tenant,
            changes=changes,
        )


@receiver(post_delete)
def _audit_post_delete(sender, instance, **kwargs):
    """Log deletions of tracked models."""
    if sender not in _TRACKED_MODELS:
        return
    entity_type = f"{sender._meta.app_label}.{sender.__name__}"
    tenant = getattr(instance, "tenant", None)
    AuditLog.log(
        action=AuditLog.Action.DELETE,
        entity_type=entity_type,
        entity_id=str(instance.pk),
        tenant=tenant,
    )

"""
Core models — Tenant and CustomUser.

Every tenant-scoped model in the project carries a FK to Tenant.
CustomUser extends AbstractUser with UUID pk, role, and tenant FK.
"""

import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    """
    Represents an organisation / company on the platform.

    All domain data is scoped to a single tenant via ForeignKey.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """
    Extended user with UUID pk, tenant association, and role.

    Roles
    -----
    - super_admin : platform-wide access (no tenant required)
    - admin       : tenant administrator
    - analyst     : can review / approve emission records
    - viewer      : read-only access
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        ANALYST = "analyst", "Analyst"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
        help_text="NULL for super-admins who operate across tenants.",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

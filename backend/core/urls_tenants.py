"""Tenant CRUD URL patterns mounted at /api/tenants/."""

from django.urls import path
from .views import TenantListView

urlpatterns = [
    path("", TenantListView.as_view(), name="tenant-list"),
]

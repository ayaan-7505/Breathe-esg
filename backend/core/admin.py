from django.contrib import admin
from .models import Tenant, CustomUser


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    search_fields = ["name", "slug"]


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "role", "tenant", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["username", "email"]

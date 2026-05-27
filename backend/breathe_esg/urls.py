"""
Root URL configuration for Breathe ESG.

Routes are split per-app under /api/.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("core.urls")),
    path("api/tenants/", include("core.urls_tenants")),
    path("api/ingestion/", include("ingestion.urls")),
    path("api/emissions/", include("emissions.urls")),
    path("api/audit/", include("audit.urls")),
]

"""Ingestion URL patterns mounted at /api/ingestion/."""

from django.urls import path
from .views import UploadView, IngestionJobListView, IngestionJobDetailView, JobErrorsView

urlpatterns = [
    path("upload/", UploadView.as_view(), name="ingestion-upload"),
    path("jobs/", IngestionJobListView.as_view(), name="ingestion-job-list"),
    path("jobs/<uuid:pk>/", IngestionJobDetailView.as_view(), name="ingestion-job-detail"),
    path("jobs/<uuid:pk>/errors/", JobErrorsView.as_view(), name="ingestion-job-errors"),
]

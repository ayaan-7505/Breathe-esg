"""Emissions URL patterns mounted at /api/emissions/."""

from django.urls import path
from .views import (
    EmissionRecordListView,
    EmissionRecordDetailView,
    EmissionRecordUpdateView,
    ApproveRecordView,
    FlagRecordView,
    LockRecordView,
    BulkActionView,
    EmissionSummaryView,
    EmissionChartView,
    EmissionFactorListView,
    PlantCodeMappingListView,
)

urlpatterns = [
    # Emission records
    path("", EmissionRecordListView.as_view(), name="emission-list"),
    path("summary/", EmissionSummaryView.as_view(), name="emission-summary"),
    path("charts/", EmissionChartView.as_view(), name="emission-charts"),
    path("bulk-action/", BulkActionView.as_view(), name="emission-bulk-action"),
    path("factors/", EmissionFactorListView.as_view(), name="emission-factor-list"),
    path("plant-mappings/", PlantCodeMappingListView.as_view(), name="plant-mapping-list"),
    # Single record
    path("<uuid:pk>/", EmissionRecordDetailView.as_view(), name="emission-detail"),
    path("<uuid:pk>/update/", EmissionRecordUpdateView.as_view(), name="emission-update"),
    path("<uuid:pk>/approve/", ApproveRecordView.as_view(), name="emission-approve"),
    path("<uuid:pk>/flag/", FlagRecordView.as_view(), name="emission-flag"),
    path("<uuid:pk>/lock/", LockRecordView.as_view(), name="emission-lock"),
]

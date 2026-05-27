"""Ingestion admin registrations."""

from django.contrib import admin
from .models import IngestionJob, SAPRawRow, UtilityRawRow, TravelRawRow


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = [
        "id", "tenant", "source_type", "file_name", "status",
        "total_rows", "valid_rows", "error_rows", "duplicate_rows",
        "created_at",
    ]
    list_filter = ["source_type", "status"]
    search_fields = ["file_name"]
    readonly_fields = ["id", "created_at", "completed_at"]


@admin.register(SAPRawRow)
class SAPRawRowAdmin(admin.ModelAdmin):
    list_display = [
        "row_number", "document_number", "material_number",
        "plant_code", "quantity", "posting_date", "is_valid", "is_duplicate",
    ]
    list_filter = ["is_valid", "is_duplicate"]


@admin.register(UtilityRawRow)
class UtilityRawRowAdmin(admin.ModelAdmin):
    list_display = [
        "row_number", "meter_id", "facility_name",
        "billing_start", "billing_end", "consumption_kwh",
        "is_valid", "is_duplicate",
    ]
    list_filter = ["is_valid", "is_duplicate"]


@admin.register(TravelRawRow)
class TravelRawRowAdmin(admin.ModelAdmin):
    list_display = [
        "row_number", "trip_id", "origin_iata", "destination_iata",
        "travel_date", "distance_km", "is_valid", "is_duplicate",
    ]
    list_filter = ["is_valid", "is_duplicate", "transport_mode"]

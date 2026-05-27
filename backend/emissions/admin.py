"""Emissions admin registrations."""

from django.contrib import admin
from .models import EmissionRecord, EmissionFactor, PlantCodeMapping


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id", "tenant", "source_type", "scope", "activity_type",
        "co2e_kg", "status", "record_date",
    ]
    list_filter = ["source_type", "scope", "status"]
    search_fields = ["activity_type", "facility"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = [
        "name", "category", "unit", "factor_kg_co2e",
        "source", "year", "region", "is_active",
    ]
    list_filter = ["category", "source", "year", "is_active"]
    search_fields = ["name"]


@admin.register(PlantCodeMapping)
class PlantCodeMappingAdmin(admin.ModelAdmin):
    list_display = ["plant_code", "facility_name", "tenant", "location", "country"]
    list_filter = ["tenant"]
    search_fields = ["plant_code", "facility_name"]

"""
Emissions models — the normalized, scope-classified output of ingestion.

Key models
----------
- **EmissionFactor**: lookup table of kg CO₂e per unit for various
  fuel types, electricity grids, and travel classes.
- **PlantCodeMapping**: maps SAP WERKS codes to human-readable facility
  names and locations.
- **EmissionRecord**: the unified emission record produced by the
  normalizer. Carries review status and immutability enforcement.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# -----------------------------------------------------------------------
# EmissionFactor  (pre-seeded lookup table)
# -----------------------------------------------------------------------
class EmissionFactor(models.Model):
    """
    kg CO₂-equivalent per unit for a given activity / fuel / grid.

    Sourced from EPA / DEFRA / custom overrides.
    """

    class Category(models.TextChoices):
        FUEL = "fuel", "Fuel Combustion"
        ELECTRICITY = "electricity", "Electricity Grid"
        TRAVEL_AIR = "travel_air", "Air Travel"
        TRAVEL_RAIL = "travel_rail", "Rail Travel"
        TRAVEL_ROAD = "travel_road", "Road Travel"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=30, choices=Category.choices)
    name = models.CharField(
        max_length=255,
        help_text="e.g. 'Diesel', 'Natural Gas', 'US Grid Average', 'Air Economy'",
    )
    unit = models.CharField(
        max_length=30,
        help_text="Input unit, e.g. 'L', 'kWh', 'km'",
    )
    factor_kg_co2e = models.DecimalField(
        max_digits=12, decimal_places=6,
        help_text="kg CO₂e per one unit",
    )
    source = models.CharField(
        max_length=50, blank=True, default="EPA",
        help_text="EPA, DEFRA, custom, etc.",
    )
    year = models.PositiveSmallIntegerField(
        default=2024,
        help_text="Reference year for the factor.",
    )
    region = models.CharField(
        max_length=100, blank=True, default="Global",
        help_text="Geographical applicability.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]
        unique_together = ["category", "name", "unit", "year", "region"]

    def __str__(self):
        return f"{self.name} ({self.unit}) — {self.factor_kg_co2e} kg CO₂e [{self.source}]"


# -----------------------------------------------------------------------
# PlantCodeMapping  (SAP WERKS → facility)
# -----------------------------------------------------------------------
class PlantCodeMapping(models.Model):
    """Maps SAP WERKS plant codes to readable facility names."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant", on_delete=models.CASCADE, related_name="plant_mappings"
    )
    plant_code = models.CharField(max_length=10)
    facility_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ["tenant", "plant_code"]
        ordering = ["plant_code"]

    def __str__(self):
        return f"{self.plant_code} → {self.facility_name}"


# -----------------------------------------------------------------------
# EmissionRecord  (unified normalised output)
# -----------------------------------------------------------------------
class EmissionRecord(models.Model):
    """
    A single normalised emission data point.

    Created by the normalizer from validated raw rows.
    Subject to the review workflow:
        pending → reviewed → approved → locked
    With a parallel 'flagged' state for suspicious data.

    **Immutability**: once ``status == locked``, the record cannot be
    modified (enforced in ``save()``).
    """

    class Scope(models.TextChoices):
        SCOPE_1 = "scope_1", "Scope 1 — Direct"
        SCOPE_2 = "scope_2", "Scope 2 — Indirect (Energy)"
        SCOPE_3 = "scope_3", "Scope 3 — Value Chain"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        FLAGGED = "flagged", "Flagged"
        LOCKED = "locked", "Locked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant", on_delete=models.CASCADE, related_name="emission_records"
    )
    job = models.ForeignKey(
        "ingestion.IngestionJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emission_records",
    )

    # Source traceability
    source_type = models.CharField(max_length=10)  # sap / utility / travel
    source_row_id = models.UUIDField(
        null=True, blank=True,
        help_text="PK of the raw row that produced this record.",
    )

    # GHG classification
    scope = models.CharField(max_length=10, choices=Scope.choices)
    scope_category = models.CharField(
        max_length=100, blank=True,
        help_text="Sub-category, e.g. 'Scope 3 Cat 6 — Business Travel'",
    )

    # Core data
    activity_type = models.CharField(
        max_length=100,
        help_text="e.g. 'Diesel Combustion', 'Grid Electricity', 'Air Travel'",
    )
    facility = models.CharField(max_length=255, blank=True)
    activity_amount = models.DecimalField(
        max_digits=18, decimal_places=4,
        help_text="Quantity in the original unit (litres, kWh, km, etc.)",
    )
    activity_unit = models.CharField(max_length=30)
    emission_factor_id = models.UUIDField(
        null=True, blank=True,
        help_text="FK to EmissionFactor used (stored as UUID for flexibility).",
    )
    emission_factor_value = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True,
        help_text="Snapshot of the factor at computation time.",
    )
    co2e_kg = models.DecimalField(
        max_digits=18, decimal_places=4,
        help_text="Computed CO₂e in kilograms.",
    )

    # Temporal
    record_date = models.DateField(
        help_text="The date the underlying activity occurred.",
    )
    reporting_period = models.CharField(
        max_length=7, blank=True,
        help_text="YYYY-MM format for aggregation.",
    )

    # Review workflow
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_emissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    flag_reason = models.TextField(blank=True)

    # Analyst override
    scope_override = models.CharField(
        max_length=10, blank=True,
        help_text="Analyst-overridden scope (with audit trail).",
    )
    override_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-record_date", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "scope", "record_date"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "reporting_period"]),
        ]

    def __str__(self):
        return (
            f"{self.get_scope_display()} | {self.activity_type} | "
            f"{self.co2e_kg} kg CO₂e ({self.status})"
        )

    @property
    def effective_scope(self):
        """Return the analyst-overridden scope if set, else auto-classified."""
        return self.scope_override or self.scope

    def save(self, *args, **kwargs):
        """Enforce immutability for locked records."""
        if self.pk:
            try:
                existing = EmissionRecord.objects.get(pk=self.pk)
                if existing.status == self.Status.LOCKED:
                    raise ValidationError(
                        "Locked records are immutable and cannot be modified."
                    )
            except EmissionRecord.DoesNotExist:
                pass

        # Auto-compute reporting_period from record_date
        if self.record_date:
            self.reporting_period = self.record_date.strftime("%Y-%m")

        super().save(*args, **kwargs)

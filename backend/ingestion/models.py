"""
Ingestion models — IngestionJob and per-source raw row tables.

Each CSV upload creates an IngestionJob. The appropriate parser reads each
row into the matching raw-row table (SAPRawRow, UtilityRawRow, TravelRawRow).
Rows carry per-row ``validation_errors`` so the frontend can show row-level
feedback.
"""

import hashlib
import uuid

from django.conf import settings
from django.db import models


# -----------------------------------------------------------------------
# IngestionJob
# -----------------------------------------------------------------------
class IngestionJob(models.Model):
    """
    Tracks a single CSV file upload and its processing outcome.
    """

    class SourceType(models.TextChoices):
        SAP = "sap", "SAP (Fuel / Procurement)"
        UTILITY = "utility", "Utility (Electricity)"
        TRAVEL = "travel", "Corporate Travel"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant", on_delete=models.CASCADE, related_name="ingestion_jobs"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ingestion_jobs",
    )
    source_type = models.CharField(max_length=10, choices=SourceType.choices)
    file_name = models.CharField(max_length=500)
    file = models.FileField(upload_to="uploads/csv/%Y/%m/")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    processing_errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source_type} upload {self.file_name} ({self.status})"


# -----------------------------------------------------------------------
# Mixin for common raw-row fields
# -----------------------------------------------------------------------
class RawRowBase(models.Model):
    """Abstract base for all raw-row tables."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant", on_delete=models.CASCADE, related_name="+"
    )
    job = models.ForeignKey(
        IngestionJob, on_delete=models.CASCADE, related_name="%(class)s_rows"
    )
    row_number = models.PositiveIntegerField(help_text="1-based row index in the CSV")
    raw_data = models.JSONField(
        help_text="The entire original CSV row as key-value pairs."
    )
    is_valid = models.BooleanField(default=True)
    is_duplicate = models.BooleanField(default=False)
    validation_errors = models.JSONField(
        default=list,
        blank=True,
        help_text='List of {type, field, message} dicts.',
    )
    row_hash = models.CharField(
        max_length=64,
        db_index=True,
        blank=True,
        help_text="SHA-256 of key fields for duplicate detection.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @staticmethod
    def compute_hash(*values) -> str:
        """SHA-256 hash of concatenated string values."""
        payload = "|".join(str(v) for v in values)
        return hashlib.sha256(payload.encode()).hexdigest()


# -----------------------------------------------------------------------
# SAP raw rows  (fuel / procurement)
# -----------------------------------------------------------------------
class SAPRawRow(RawRowBase):
    """
    Parsed columns from an SAP material-document export.

    German header mapping:
      MBLNR → document_number
      BWART → movement_type
      MATNR → material_number
      WERKS → plant_code
      MENGE → quantity
      MEINS → unit_of_measure
      BUDAT → posting_date
      WAERS → currency
      DMBTR → amount_local
    """

    document_number = models.CharField(max_length=50, blank=True)
    movement_type = models.CharField(max_length=10, blank=True)
    material_number = models.CharField(max_length=50, blank=True)
    plant_code = models.CharField(max_length=10, blank=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=10, blank=True)
    posting_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=5, blank=True)
    amount_local = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["job", "row_number"]),
        ]

    def __str__(self):
        return f"SAP row {self.row_number}: {self.document_number}"


# -----------------------------------------------------------------------
# Utility raw rows (electricity)
# -----------------------------------------------------------------------
class UtilityRawRow(RawRowBase):
    """
    Parsed columns from a utility / electricity bill CSV.
    """

    meter_id = models.CharField(max_length=50, blank=True)
    facility_name = models.CharField(max_length=255, blank=True)
    billing_start = models.DateField(null=True, blank=True)
    billing_end = models.DateField(null=True, blank=True)
    consumption_kwh = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    unit = models.CharField(max_length=20, blank=True, default="kWh")
    cost = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, blank=True)
    provider = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["job", "row_number"]),
        ]

    def __str__(self):
        return f"Utility row {self.row_number}: {self.meter_id}"


# -----------------------------------------------------------------------
# Travel raw rows (corporate travel)
# -----------------------------------------------------------------------
class TravelRawRow(RawRowBase):
    """
    Parsed columns from a corporate-travel CSV.

    Distances can be computed from IATA airport codes via great-circle.
    """

    trip_id = models.CharField(max_length=50, blank=True)
    employee_id = models.CharField(max_length=50, blank=True)
    travel_date = models.DateField(null=True, blank=True)
    origin_iata = models.CharField(max_length=5, blank=True)
    destination_iata = models.CharField(max_length=5, blank=True)
    travel_class = models.CharField(max_length=30, blank=True)
    trip_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="one_way or round_trip",
    )
    distance_km = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Great-circle distance; computed if IATA codes present.",
    )
    transport_mode = models.CharField(
        max_length=30, blank=True, default="air",
        help_text="air, rail, road, etc.",
    )

    class Meta:
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["job", "row_number"]),
        ]

    def __str__(self):
        return f"Travel row {self.row_number}: {self.origin_iata}→{self.destination_iata}"

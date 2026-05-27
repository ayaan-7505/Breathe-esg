"""Ingestion serializers."""

from rest_framework import serializers
from .models import IngestionJob, SAPRawRow, UtilityRawRow, TravelRawRow


class IngestionJobSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )
    success_count = serializers.IntegerField(source="valid_rows", read_only=True)
    records_created = serializers.IntegerField(source="valid_rows", read_only=True)
    error_count = serializers.IntegerField(source="error_rows", read_only=True)
    records_failed = serializers.IntegerField(source="error_rows", read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            "id", "tenant", "uploaded_by", "uploaded_by_username",
            "source_type", "file_name", "status",
            "total_rows", "valid_rows", "error_rows", "duplicate_rows",
            "success_count", "records_created", "error_count", "records_failed",
            "processing_errors", "created_at", "completed_at",
        ]
        read_only_fields = [
            "id", "tenant", "uploaded_by", "status",
            "total_rows", "valid_rows", "error_rows", "duplicate_rows",
            "success_count", "records_created", "error_count", "records_failed",
            "processing_errors", "created_at", "completed_at",
        ]


class UploadSerializer(serializers.Serializer):
    """Validates the upload request."""

    file = serializers.FileField()
    source_type = serializers.CharField()

    def validate_file(self, value):
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Only CSV files are accepted.")
        return value

    def validate_source_type(self, value):
        val_lower = value.strip().lower()
        # choices are 'sap', 'utility', 'travel'
        if val_lower not in ("sap", "utility", "travel"):
            raise serializers.ValidationError(
                f"'{value}' is not a valid choice. Choose from ['sap', 'utility', 'travel']."
            )
        return val_lower


class SAPRawRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = SAPRawRow
        fields = [
            "id", "row_number", "raw_data", "is_valid", "is_duplicate",
            "validation_errors", "document_number", "movement_type",
            "material_number", "plant_code", "quantity", "unit_of_measure",
            "posting_date", "currency", "amount_local",
        ]


class UtilityRawRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityRawRow
        fields = [
            "id", "row_number", "raw_data", "is_valid", "is_duplicate",
            "validation_errors", "meter_id", "facility_name",
            "billing_start", "billing_end", "consumption_kwh",
            "unit", "cost", "currency", "provider",
        ]


class TravelRawRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelRawRow
        fields = [
            "id", "row_number", "raw_data", "is_valid", "is_duplicate",
            "validation_errors", "trip_id", "employee_id",
            "travel_date", "origin_iata", "destination_iata",
            "travel_class", "trip_type", "distance_km", "transport_mode",
        ]


class IngestionJobDetailSerializer(serializers.ModelSerializer):
    """Job detail with nested raw rows based on source_type."""

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )
    success_count = serializers.IntegerField(source="valid_rows", read_only=True)
    records_created = serializers.IntegerField(source="valid_rows", read_only=True)
    error_count = serializers.IntegerField(source="error_rows", read_only=True)
    records_failed = serializers.IntegerField(source="error_rows", read_only=True)
    raw_rows = serializers.SerializerMethodField()

    class Meta:
        model = IngestionJob
        fields = [
            "id", "tenant", "uploaded_by", "uploaded_by_username",
            "source_type", "file_name", "status",
            "total_rows", "valid_rows", "error_rows", "duplicate_rows",
            "success_count", "records_created", "error_count", "records_failed",
            "processing_errors", "created_at", "completed_at",
            "raw_rows",
        ]

    def get_raw_rows(self, obj):
        if obj.source_type == "sap":
            qs = SAPRawRow.objects.filter(job=obj)
            return SAPRawRowSerializer(qs, many=True).data
        elif obj.source_type == "utility":
            qs = UtilityRawRow.objects.filter(job=obj)
            return UtilityRawRowSerializer(qs, many=True).data
        elif obj.source_type == "travel":
            qs = TravelRawRow.objects.filter(job=obj)
            return TravelRawRowSerializer(qs, many=True).data
        return []

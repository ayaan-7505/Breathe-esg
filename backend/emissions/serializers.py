"""
Emissions serializers — EmissionRecord CRUD, bulk actions, summary.

Includes scope-override validation and immutability checks.
"""

from rest_framework import serializers
from .models import EmissionRecord, EmissionFactor, PlantCodeMapping


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = [
            "id", "category", "name", "unit", "factor_kg_co2e",
            "source", "year", "region", "is_active",
        ]
        read_only_fields = ["id"]


class PlantCodeMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantCodeMapping
        fields = [
            "id", "tenant", "plant_code", "facility_name",
            "location", "country",
        ]
        read_only_fields = ["id", "tenant"]


class EmissionRecordSerializer(serializers.ModelSerializer):
    """Full emission record serializer — used for list / detail views."""

    effective_scope = serializers.CharField(read_only=True)
    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username", read_only=True, default=None
    )

    class Meta:
        model = EmissionRecord
        fields = [
            "id", "tenant", "job", "source_type", "source_row_id",
            "scope", "scope_category", "effective_scope",
            "activity_type", "facility",
            "activity_amount", "activity_unit",
            "emission_factor_id", "emission_factor_value", "co2e_kg",
            "record_date", "reporting_period",
            "status", "reviewed_by", "reviewed_by_username", "reviewed_at",
            "flag_reason",
            "scope_override", "override_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "tenant", "job", "source_type", "source_row_id",
            "scope", "scope_category", "effective_scope",
            "emission_factor_id", "emission_factor_value", "co2e_kg",
            "reporting_period",
            "reviewed_by", "reviewed_by_username", "reviewed_at",
            "created_at", "updated_at",
        ]


class EmissionRecordUpdateSerializer(serializers.ModelSerializer):
    """
    Partial-update serializer for emission records.

    Allows analysts to override scope, flag, or adjust activity data.
    Locked records are rejected at the view level.
    """

    class Meta:
        model = EmissionRecord
        fields = [
            "scope_override", "override_reason",
            "flag_reason", "activity_amount", "activity_unit",
            "facility", "activity_type",
        ]

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.status == EmissionRecord.Status.LOCKED:
            raise serializers.ValidationError(
                "Locked records cannot be modified."
            )
        return attrs

    def update(self, instance, validated_data):
        """Recompute CO₂e if activity_amount changed."""
        new_amount = validated_data.get("activity_amount")
        if new_amount is not None and instance.emission_factor_value:
            validated_data["co2e_kg"] = new_amount * instance.emission_factor_value
        return super().update(instance, validated_data)


class BulkActionSerializer(serializers.Serializer):
    """
    Validates bulk action requests.

    Actions: approve, reject, flag, lock, review
    """

    ACTIONS = ["approve", "reject", "flag", "lock", "review"]

    ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=500,
        help_text="List of EmissionRecord UUIDs to act on.",
    )
    action = serializers.ChoiceField(choices=[(a, a) for a in ACTIONS])
    reason = serializers.CharField(
        required=False, allow_blank=True, default="",
        help_text="Reason for flagging or rejecting.",
    )


class EmissionSummaryRequestSerializer(serializers.Serializer):
    """Query params for the summary endpoint."""

    group_by = serializers.ChoiceField(
        choices=[
            ("scope", "scope"),
            ("month", "month"),
            ("facility", "facility"),
            ("source_type", "source_type"),
        ],
        default="scope",
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    scope = serializers.ChoiceField(
        choices=EmissionRecord.Scope.choices,
        required=False,
    )

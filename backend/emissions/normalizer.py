"""
Normalizer — converts validated raw rows into unified EmissionRecords.

For each valid raw row the normalizer:
1. Looks up the appropriate EmissionFactor.
2. Classifies the GHG scope.
3. Computes CO₂e = activity_amount × emission_factor.
4. Creates an EmissionRecord.
"""

import logging
from decimal import Decimal

from .models import EmissionRecord, EmissionFactor, PlantCodeMapping
from .scope_classifier import classify_scope
from ingestion.models import IngestionJob, SAPRawRow, UtilityRawRow, TravelRawRow

logger = logging.getLogger(__name__)


def _find_emission_factor(category: str, name_hint: str, unit: str):
    """
    Best-effort emission factor lookup.
    Returns (factor_object, factor_value) or (None, default).
    """
    # Try exact match first
    ef = EmissionFactor.objects.filter(
        category=category, unit=unit, is_active=True
    ).first()
    if ef:
        return ef, ef.factor_kg_co2e

    # Fallback: any factor for category
    ef = EmissionFactor.objects.filter(
        category=category, is_active=True
    ).first()
    if ef:
        return ef, ef.factor_kg_co2e

    # Hard-coded defaults so normalisation never fails entirely
    defaults = {
        "fuel": Decimal("2.68"),        # ~diesel kg CO₂e / litre
        "electricity": Decimal("0.42"), # ~global avg kg CO₂e / kWh
        "travel_air": Decimal("0.255"), # ~economy kg CO₂e / passenger-km
        "travel_rail": Decimal("0.041"),
        "travel_road": Decimal("0.171"),
    }
    return None, defaults.get(category, Decimal("0.0"))


def _get_facility_name(tenant, plant_code: str) -> str:
    """Resolve plant code to facility name via PlantCodeMapping."""
    mapping = PlantCodeMapping.objects.filter(
        tenant=tenant, plant_code=plant_code
    ).first()
    return mapping.facility_name if mapping else plant_code


# =====================================================================
#  Normalise a complete ingestion job
# =====================================================================
def normalize_job(job: IngestionJob) -> int:
    """
    Create EmissionRecords for all valid, non-duplicate raw rows in a job.
    Returns the count of records created.
    """
    if job.source_type == "sap":
        return _normalize_sap(job)
    elif job.source_type == "utility":
        return _normalize_utility(job)
    elif job.source_type == "travel":
        return _normalize_travel(job)
    return 0


# -----------------------------------------------------------------------
# SAP  →  Scope 1
# -----------------------------------------------------------------------
def _normalize_sap(job: IngestionJob) -> int:
    rows = SAPRawRow.objects.filter(job=job, is_valid=True, is_duplicate=False)
    scope, scope_cat = classify_scope("sap")
    count = 0

    for row in rows:
        if row.quantity is None or row.posting_date is None:
            continue

        # Determine unit-based emission factor
        unit = (row.unit_of_measure or "L").upper()
        ef, factor_val = _find_emission_factor("fuel", row.material_number, unit)

        co2e = row.quantity * factor_val
        facility = _get_facility_name(job.tenant, row.plant_code)

        EmissionRecord.objects.create(
            tenant=job.tenant,
            job=job,
            source_type="sap",
            source_row_id=row.pk,
            scope=scope,
            scope_category=scope_cat,
            activity_type=f"Fuel — {row.material_number or 'Unknown'}",
            facility=facility,
            activity_amount=row.quantity,
            activity_unit=unit,
            emission_factor_id=ef.pk if ef else None,
            emission_factor_value=factor_val,
            co2e_kg=co2e,
            record_date=row.posting_date,
        )
        count += 1

    return count


# -----------------------------------------------------------------------
# Utility  →  Scope 2
# -----------------------------------------------------------------------
def _normalize_utility(job: IngestionJob) -> int:
    rows = UtilityRawRow.objects.filter(job=job, is_valid=True, is_duplicate=False)
    scope, scope_cat = classify_scope("utility")
    count = 0

    for row in rows:
        if row.consumption_kwh is None:
            continue

        # Use billing_start as the record date; fall back to billing_end
        record_date = row.billing_start or row.billing_end
        if not record_date:
            continue

        ef, factor_val = _find_emission_factor("electricity", "", "kWh")

        co2e = row.consumption_kwh * factor_val

        EmissionRecord.objects.create(
            tenant=job.tenant,
            job=job,
            source_type="utility",
            source_row_id=row.pk,
            scope=scope,
            scope_category=scope_cat,
            activity_type="Grid Electricity",
            facility=row.facility_name or row.meter_id,
            activity_amount=row.consumption_kwh,
            activity_unit="kWh",
            emission_factor_id=ef.pk if ef else None,
            emission_factor_value=factor_val,
            co2e_kg=co2e,
            record_date=record_date,
        )
        count += 1

    return count


# -----------------------------------------------------------------------
# Travel  →  Scope 3 Cat 6
# -----------------------------------------------------------------------
def _normalize_travel(job: IngestionJob) -> int:
    rows = TravelRawRow.objects.filter(job=job, is_valid=True, is_duplicate=False)
    scope, scope_cat = classify_scope("travel")
    count = 0

    for row in rows:
        if row.distance_km is None or row.travel_date is None:
            continue

        mode = (row.transport_mode or "air").lower()
        category_map = {
            "air": "travel_air",
            "rail": "travel_rail",
            "road": "travel_road",
        }
        ef_category = category_map.get(mode, "travel_air")

        # Factor may vary by travel class — use class as name hint
        ef, factor_val = _find_emission_factor(ef_category, row.travel_class, "km")

        co2e = row.distance_km * factor_val

        EmissionRecord.objects.create(
            tenant=job.tenant,
            job=job,
            source_type="travel",
            source_row_id=row.pk,
            scope=scope,
            scope_category=scope_cat,
            activity_type=f"{mode.title()} Travel — {row.travel_class}",
            facility=f"{row.origin_iata}→{row.destination_iata}",
            activity_amount=row.distance_km,
            activity_unit="km",
            emission_factor_id=ef.pk if ef else None,
            emission_factor_value=factor_val,
            co2e_kg=co2e,
            record_date=row.travel_date,
        )
        count += 1

    return count

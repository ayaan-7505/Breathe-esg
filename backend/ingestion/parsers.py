"""
CSV parsers for each source type.

Each parser:
1. Reads the uploaded CSV (handling encoding quirks).
2. Maps headers (including German SAP names) to canonical fields.
3. Validates each row and persists it as a raw-row model instance.
4. Detects duplicates via row_hash.
5. Returns (total, valid, errors, duplicates) counts.
"""

import csv
import io
import logging
from decimal import Decimal

from django.utils import timezone

from .models import (
    IngestionJob,
    SAPRawRow,
    UtilityRawRow,
    TravelRawRow,
)
from .date_utils import parse_date, parse_decimal
from .validators import validate_sap_row, validate_utility_row, validate_travel_row
from .iata_lookup import get_great_circle_distance_km

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Header mappings  (lowercase source header → canonical field name)
# -----------------------------------------------------------------------
SAP_HEADER_MAP = {
    # German SAP headers
    "mblnr": "document_number",
    "bwart": "movement_type",
    "matnr": "material_number",
    "werks": "plant_code",
    "menge": "quantity",
    "meins": "unit_of_measure",
    "budat": "posting_date",
    "waers": "currency",
    "dmbtr": "amount_local",
    # English fallbacks
    "document_number": "document_number",
    "movement_type": "movement_type",
    "material_number": "material_number",
    "plant_code": "plant_code",
    "quantity": "quantity",
    "unit_of_measure": "unit_of_measure",
    "unit": "unit_of_measure",
    "posting_date": "posting_date",
    "date": "posting_date",
    "currency": "currency",
    "amount": "amount_local",
    "amount_local": "amount_local",
}

UTILITY_HEADER_MAP = {
    "meter_id": "meter_id",
    "meter": "meter_id",
    "facility_name": "facility_name",
    "facility": "facility_name",
    "billing_start": "billing_start",
    "billing_period_start": "billing_start",
    "start_date": "billing_start",
    "billing_end": "billing_end",
    "billing_period_end": "billing_end",
    "end_date": "billing_end",
    "consumption_kwh": "consumption_kwh",
    "consumption": "consumption_kwh",
    "kwh": "consumption_kwh",
    "unit": "unit",
    "cost": "cost",
    "cost_usd": "cost",
    "amount": "cost",
    "currency": "currency",
    "provider": "provider",
    "supplier": "provider",
    "account_number": "account_number",
    "service_address": "service_address",
    "demand_kw": "demand_kw",
    "tariff_type": "tariff_type",
    "read_type": "read_type",
}

TRAVEL_HEADER_MAP = {
    "trip_id": "trip_id",
    "report_id": "trip_id",
    "employee_id": "employee_id",
    "employee": "employee_id",
    "employee_name": "employee_name",
    "travel_date": "travel_date",
    "date": "travel_date",
    "departure_date": "travel_date",
    "origin_iata": "origin_iata",
    "origin": "origin_iata",
    "from": "origin_iata",
    "departure": "origin_iata",
    "departure_code": "origin_iata",
    "destination_iata": "destination_iata",
    "destination": "destination_iata",
    "to": "destination_iata",
    "arrival": "destination_iata",
    "arrival_code": "destination_iata",
    "travel_class": "travel_class",
    "class": "travel_class",
    "cabin_class": "travel_class",
    "trip_type": "trip_type",
    "type": "trip_type",
    "distance_km": "distance_km",
    "distance": "distance_km",
    "transport_mode": "transport_mode",
    "mode": "transport_mode",
    "amount": "amount",
    "currency": "currency",
    "vendor": "vendor",
    "booking_reference": "booking_reference",
}


def _read_csv(file_obj) -> list[dict]:
    """
    Read a CSV file (possibly with BOM) into a list of dicts.
    Handles UTF-8-BOM and latin-1 fallback.
    """
    file_obj.seek(0)
    raw = file_obj.read()

    # Try UTF-8 (with BOM), fall back to latin-1
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except (UnicodeDecodeError, AttributeError):
            if isinstance(raw, str):
                text = raw
                break
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _map_headers(row: dict, header_map: dict) -> dict:
    """Re-key a CSV row dict using a header mapping (case-insensitive)."""
    mapped = {}
    for key, value in row.items():
        canonical = header_map.get(key.strip().lower())
        if canonical:
            mapped[canonical] = value.strip() if isinstance(value, str) else value
    return mapped


# =====================================================================
#  SAP Parser
# =====================================================================
def parse_sap(job: IngestionJob) -> None:
    """Parse an SAP fuel/procurement CSV and create SAPRawRow objects."""
    rows = _read_csv(job.file)
    total = len(rows)
    valid_count = 0
    error_count = 0
    dup_count = 0
    existing_hashes = set(
        SAPRawRow.objects.filter(tenant=job.tenant)
        .values_list("row_hash", flat=True)
    )

    for idx, raw in enumerate(rows, start=1):
        mapped = _map_headers(raw, SAP_HEADER_MAP)
        raw_data = dict(raw)  # preserve original

        # Parse fields
        quantity = parse_decimal(mapped.get("quantity"))
        posting_date = parse_date(mapped.get("posting_date"))
        amount_local = parse_decimal(mapped.get("amount_local"))

        doc_num = mapped.get("document_number", "")
        mat_num = mapped.get("material_number", "")
        plant = mapped.get("plant_code", "")
        uom = mapped.get("unit_of_measure", "")
        mvmt = mapped.get("movement_type", "")
        currency = mapped.get("currency", "")

        # Validate
        errors = validate_sap_row(
            document_number=doc_num,
            movement_type=mvmt,
            material_number=mat_num,
            plant_code=plant,
            quantity=quantity,
            unit_of_measure=uom,
            posting_date=posting_date,
        )

        # Duplicate check
        row_hash = SAPRawRow.compute_hash(
            job.tenant_id, doc_num, mat_num, plant,
            str(quantity), str(posting_date),
        )
        is_dup = row_hash in existing_hashes

        is_valid = len(errors) == 0 and not is_dup
        if errors:
            error_count += 1
        if is_dup:
            dup_count += 1
        if is_valid:
            valid_count += 1

        existing_hashes.add(row_hash)

        SAPRawRow.objects.create(
            tenant=job.tenant,
            job=job,
            row_number=idx,
            raw_data=raw_data,
            is_valid=is_valid,
            is_duplicate=is_dup,
            validation_errors=errors,
            row_hash=row_hash,
            document_number=doc_num,
            movement_type=mvmt,
            material_number=mat_num,
            plant_code=plant,
            quantity=quantity,
            unit_of_measure=uom,
            posting_date=posting_date,
            currency=currency,
            amount_local=amount_local,
        )

    job.total_rows = total
    job.valid_rows = valid_count
    job.error_rows = error_count
    job.duplicate_rows = dup_count
    job.status = IngestionJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save()


# =====================================================================
#  Utility Parser
# =====================================================================
def parse_utility(job: IngestionJob) -> None:
    """Parse a utility/electricity CSV and create UtilityRawRow objects."""
    rows = _read_csv(job.file)
    total = len(rows)
    valid_count = 0
    error_count = 0
    dup_count = 0
    existing_hashes = set(
        UtilityRawRow.objects.filter(tenant=job.tenant)
        .values_list("row_hash", flat=True)
    )

    for idx, raw in enumerate(rows, start=1):
        mapped = _map_headers(raw, UTILITY_HEADER_MAP)
        raw_data = dict(raw)

        meter_id = mapped.get("meter_id", "")
        facility_name = mapped.get("facility_name", "")
        billing_start = parse_date(mapped.get("billing_start"))
        billing_end = parse_date(mapped.get("billing_end"))
        consumption = parse_decimal(mapped.get("consumption_kwh"))
        unit = mapped.get("unit", "kWh")
        cost = parse_decimal(mapped.get("cost"))
        currency = mapped.get("currency", "")
        provider = mapped.get("provider", "")

        errors = validate_utility_row(
            meter_id=meter_id,
            billing_start=billing_start,
            billing_end=billing_end,
            consumption_kwh=consumption,
        )

        row_hash = UtilityRawRow.compute_hash(
            job.tenant_id, meter_id, str(billing_start), str(billing_end),
            str(consumption),
        )
        is_dup = row_hash in existing_hashes

        is_valid = len(errors) == 0 and not is_dup
        if errors:
            error_count += 1
        if is_dup:
            dup_count += 1
        if is_valid:
            valid_count += 1

        existing_hashes.add(row_hash)

        UtilityRawRow.objects.create(
            tenant=job.tenant,
            job=job,
            row_number=idx,
            raw_data=raw_data,
            is_valid=is_valid,
            is_duplicate=is_dup,
            validation_errors=errors,
            row_hash=row_hash,
            meter_id=meter_id,
            facility_name=facility_name,
            billing_start=billing_start,
            billing_end=billing_end,
            consumption_kwh=consumption,
            unit=unit,
            cost=cost,
            currency=currency,
            provider=provider,
        )

    job.total_rows = total
    job.valid_rows = valid_count
    job.error_rows = error_count
    job.duplicate_rows = dup_count
    job.status = IngestionJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save()


# =====================================================================
#  Travel Parser
# =====================================================================
def parse_travel(job: IngestionJob) -> None:
    """Parse a corporate-travel CSV and create TravelRawRow objects."""
    rows = _read_csv(job.file)
    total = len(rows)
    valid_count = 0
    error_count = 0
    dup_count = 0
    existing_hashes = set(
        TravelRawRow.objects.filter(tenant=job.tenant)
        .values_list("row_hash", flat=True)
    )

    for idx, raw in enumerate(rows, start=1):
        mapped = _map_headers(raw, TRAVEL_HEADER_MAP)
        raw_data = dict(raw)

        trip_id = mapped.get("trip_id", "")
        employee_id = mapped.get("employee_id", "")
        travel_date = parse_date(mapped.get("travel_date"))
        origin = mapped.get("origin_iata", "").upper()
        dest = mapped.get("destination_iata", "").upper()
        travel_class = mapped.get("travel_class", "economy")
        trip_type = mapped.get("trip_type", "one_way").lower().replace(" ", "_")
        transport_mode = mapped.get("transport_mode", "air").lower()

        # Distance: use provided value or compute from IATA codes
        dist_raw = parse_decimal(mapped.get("distance_km"))
        if dist_raw is None and origin and dest:
            dist_computed = get_great_circle_distance_km(origin, dest)
            distance_km = Decimal(str(dist_computed)) if dist_computed else None
        else:
            distance_km = dist_raw

        # Double distance for round trips
        if distance_km and trip_type == "round_trip":
            distance_km = distance_km * 2

        errors = validate_travel_row(
            origin_iata=origin,
            destination_iata=dest,
            travel_date=travel_date,
            distance_km=distance_km,
        )

        row_hash = TravelRawRow.compute_hash(
            job.tenant_id, trip_id or f"{origin}-{dest}",
            employee_id, str(travel_date),
        )
        is_dup = row_hash in existing_hashes

        is_valid = len(errors) == 0 and not is_dup
        if errors:
            error_count += 1
        if is_dup:
            dup_count += 1
        if is_valid:
            valid_count += 1

        existing_hashes.add(row_hash)

        TravelRawRow.objects.create(
            tenant=job.tenant,
            job=job,
            row_number=idx,
            raw_data=raw_data,
            is_valid=is_valid,
            is_duplicate=is_dup,
            validation_errors=errors,
            row_hash=row_hash,
            trip_id=trip_id,
            employee_id=employee_id,
            travel_date=travel_date,
            origin_iata=origin,
            destination_iata=dest,
            travel_class=travel_class,
            trip_type=trip_type,
            distance_km=distance_km,
            transport_mode=transport_mode,
        )

    job.total_rows = total
    job.valid_rows = valid_count
    job.error_rows = error_count
    job.duplicate_rows = dup_count
    job.status = IngestionJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save()


# =====================================================================
#  Dispatcher
# =====================================================================
PARSER_MAP = {
    "sap": parse_sap,
    "utility": parse_utility,
    "travel": parse_travel,
}


def run_parser(job: IngestionJob) -> None:
    """
    Dispatch to the correct parser based on ``job.source_type``.
    Wraps everything in error handling so the job gets marked failed
    on unhandled exceptions.
    """
    parser_fn = PARSER_MAP.get(job.source_type)
    if not parser_fn:
        job.status = IngestionJob.Status.FAILED
        job.processing_errors = [f"Unknown source_type: {job.source_type}"]
        job.completed_at = timezone.now()
        job.save()
        return

    job.status = IngestionJob.Status.PROCESSING
    job.save()

    try:
        parser_fn(job)
    except Exception as exc:
        logger.exception("Parser failed for job %s", job.pk)
        job.status = IngestionJob.Status.FAILED
        job.processing_errors = [str(exc)]
        job.completed_at = timezone.now()
        job.save()

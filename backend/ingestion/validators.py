"""
Row-level validators for each source type.

Each validator returns a list of error dicts:
  [{"type": "missing_field", "field": "quantity", "message": "..."}]
"""

from decimal import Decimal
from datetime import date


# -----------------------------------------------------------------------
# Error-type constants
# -----------------------------------------------------------------------
MISSING_FIELD = "missing_field"
INVALID_FORMAT = "invalid_format"
OUT_OF_RANGE = "out_of_range"
INVALID_DATE = "invalid_date"
UNKNOWN_CODE = "unknown_code"


def _err(err_type: str, field: str, message: str) -> dict:
    return {"type": err_type, "field": field, "message": message}


# -----------------------------------------------------------------------
# SAP validator
# -----------------------------------------------------------------------
def validate_sap_row(*, document_number, movement_type, material_number,
                     plant_code, quantity, unit_of_measure, posting_date,
                     **kwargs) -> list[dict]:
    """Validate a single parsed SAP row."""
    errors = []

    if not document_number:
        errors.append(_err(MISSING_FIELD, "document_number",
                           "Document number (MBLNR) is required."))
    if not material_number:
        errors.append(_err(MISSING_FIELD, "material_number",
                           "Material number (MATNR) is required."))
    if not plant_code:
        errors.append(_err(MISSING_FIELD, "plant_code",
                           "Plant code (WERKS) is required."))
    if quantity is None:
        errors.append(_err(MISSING_FIELD, "quantity",
                           "Quantity (MENGE) is required."))
    elif quantity < 0:
        errors.append(_err(OUT_OF_RANGE, "quantity",
                           "Quantity must be non-negative."))
    if not unit_of_measure:
        errors.append(_err(MISSING_FIELD, "unit_of_measure",
                           "Unit of measure (MEINS) is required."))
    if posting_date is None:
        errors.append(_err(INVALID_DATE, "posting_date",
                           "Posting date (BUDAT) could not be parsed."))

    return errors


# -----------------------------------------------------------------------
# Utility validator
# -----------------------------------------------------------------------
def validate_utility_row(*, meter_id, billing_start, billing_end,
                         consumption_kwh, **kwargs) -> list[dict]:
    """Validate a single parsed utility row."""
    errors = []

    if not meter_id:
        errors.append(_err(MISSING_FIELD, "meter_id",
                           "Meter ID is required."))
    if billing_start is None:
        errors.append(_err(INVALID_DATE, "billing_start",
                           "Billing start date could not be parsed."))
    if billing_end is None:
        errors.append(_err(INVALID_DATE, "billing_end",
                           "Billing end date could not be parsed."))
    if billing_start and billing_end and billing_start > billing_end:
        errors.append(_err(INVALID_DATE, "billing_end",
                           "Billing end date is before start date."))
    if consumption_kwh is None:
        errors.append(_err(MISSING_FIELD, "consumption_kwh",
                           "Consumption (kWh) is required."))
    elif consumption_kwh < 0:
        errors.append(_err(OUT_OF_RANGE, "consumption_kwh",
                           "Consumption must be non-negative."))

    return errors


# -----------------------------------------------------------------------
# Travel validator
# -----------------------------------------------------------------------
def validate_travel_row(*, origin_iata, destination_iata, travel_date,
                        distance_km=None, **kwargs) -> list[dict]:
    """Validate a single parsed travel row."""
    errors = []

    if not origin_iata:
        errors.append(_err(MISSING_FIELD, "origin_iata",
                           "Origin IATA code is required."))
    elif len(origin_iata) != 3:
        errors.append(_err(INVALID_FORMAT, "origin_iata",
                           "IATA code must be 3 characters."))
    if not destination_iata:
        errors.append(_err(MISSING_FIELD, "destination_iata",
                           "Destination IATA code is required."))
    elif len(destination_iata) != 3:
        errors.append(_err(INVALID_FORMAT, "destination_iata",
                           "IATA code must be 3 characters."))
    if origin_iata and destination_iata and origin_iata == destination_iata:
        errors.append(_err(OUT_OF_RANGE, "destination_iata",
                           "Origin and destination must differ."))
    if travel_date is None:
        errors.append(_err(INVALID_DATE, "travel_date",
                           "Travel date could not be parsed."))
    if distance_km is not None and distance_km <= 0:
        errors.append(_err(OUT_OF_RANGE, "distance_km",
                           "Distance must be positive."))

    return errors

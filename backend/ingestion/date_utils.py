"""
Date-parsing utilities shared by all ingestion parsers.

Handles the three required formats:
  DD.MM.YYYY  (German SAP style)
  YYYY-MM-DD  (ISO)
  MM/DD/YYYY  (US)
"""

from datetime import date, datetime
from typing import Optional

_FORMATS = [
    "%d.%m.%Y",   # 31.12.2024
    "%Y-%m-%d",   # 2024-12-31
    "%m/%d/%Y",   # 12/31/2024
    "%d/%m/%Y",   # 31/12/2024
    "%Y%m%d",     # 20241231 (SAP compact)
]


def parse_date(value: str | None) -> Optional[date]:
    """
    Try multiple date formats and return a ``date`` or ``None``.
    """
    if not value:
        return None
    value = str(value).strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(value: str | None):
    """
    Parse a decimal string that may use comma as decimal separator
    (common in German exports).  Returns ``None`` on failure.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    # German: 1.234,56 → 1234.56
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        from decimal import Decimal, InvalidOperation
        return Decimal(value)
    except (ValueError, InvalidOperation):
        return None

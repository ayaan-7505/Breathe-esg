"""
Scope classifier — determines GHG Protocol scope from source type.

Rules
-----
- SAP fuel/procurement → Scope 1 (direct combustion)
- Utility electricity   → Scope 2 (purchased energy)
- Corporate travel      → Scope 3 Category 6 (business travel)
"""


def classify_scope(source_type: str) -> tuple[str, str]:
    """
    Returns (scope, scope_category) for a given source type.

    Parameters
    ----------
    source_type : str
        One of 'sap', 'utility', 'travel'.

    Returns
    -------
    tuple[str, str]
        (scope_value, human-readable category description)
    """
    match source_type:
        case "sap":
            return "scope_1", "Scope 1 — Direct Emissions (Fuel Combustion)"
        case "utility":
            return "scope_2", "Scope 2 — Indirect Emissions (Purchased Electricity)"
        case "travel":
            return "scope_3", "Scope 3 Cat 6 — Business Travel"
        case _:
            return "scope_3", f"Scope 3 — Other ({source_type})"

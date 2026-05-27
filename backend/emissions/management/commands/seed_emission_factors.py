"""
Management command: seed_emission_factors

Pre-populates the EmissionFactor table with EPA/DEFRA factors from
the sample_data/emission_factors.json file.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from emissions.models import EmissionFactor


# -----------------------------------------------------------------------
#  Factor definitions — derived from sample_data/emission_factors.json
# -----------------------------------------------------------------------
FACTORS = [
    # ── Stationary Combustion (Scope 1) ──────────────────────────
    {
        "category": "fuel",
        "name": "Diesel (per litre)",
        "unit": "L",
        "factor_kg_co2e": "2.700000",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "fuel",
        "name": "Diesel (per gallon)",
        "unit": "GAL",
        "factor_kg_co2e": "10.280000",
        "source": "EPA",
        "year": 2024,
        "region": "US",
    },
    {
        "category": "fuel",
        "name": "Natural Gas (per m³)",
        "unit": "M3",
        "factor_kg_co2e": "1.930000",
        "source": "EPA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "fuel",
        "name": "LPG (per litre)",
        "unit": "L",
        "factor_kg_co2e": "1.560000",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "fuel",
        "name": "LPG (per kg)",
        "unit": "KG",
        "factor_kg_co2e": "2.990000",
        "source": "EPA",
        "year": 2024,
        "region": "Global",
    },
    # ── Purchased Electricity (Scope 2) ──────────────────────────
    {
        "category": "electricity",
        "name": "US National Average Grid",
        "unit": "kWh",
        "factor_kg_co2e": "0.393700",
        "source": "EPA",
        "year": 2023,
        "region": "US",
    },
    {
        "category": "electricity",
        "name": "ERCOT (Texas Grid)",
        "unit": "kWh",
        "factor_kg_co2e": "0.373200",
        "source": "EPA",
        "year": 2023,
        "region": "US-TX",
    },
    {
        "category": "electricity",
        "name": "NWPP (Northwest Power Pool)",
        "unit": "kWh",
        "factor_kg_co2e": "0.249600",
        "source": "EPA",
        "year": 2023,
        "region": "US-NW",
    },
    {
        "category": "electricity",
        "name": "SERC Midwest",
        "unit": "kWh",
        "factor_kg_co2e": "0.652300",
        "source": "EPA",
        "year": 2023,
        "region": "US-MW",
    },
    # ── Air Travel (Scope 3 Cat 6) ───────────────────────────────
    # Domestic
    {
        "category": "travel_air",
        "name": "Domestic Economy",
        "unit": "km",
        "factor_kg_co2e": "0.245870",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "travel_air",
        "name": "Domestic Business",
        "unit": "km",
        "factor_kg_co2e": "0.428820",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    # Short-haul international (<3700 km)
    {
        "category": "travel_air",
        "name": "Short-Haul Economy",
        "unit": "km",
        "factor_kg_co2e": "0.151020",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "travel_air",
        "name": "Short-Haul Premium Economy",
        "unit": "km",
        "factor_kg_co2e": "0.241640",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "travel_air",
        "name": "Short-Haul Business",
        "unit": "km",
        "factor_kg_co2e": "0.453070",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    # Long-haul international (>=3700 km)
    {
        "category": "travel_air",
        "name": "Long-Haul Economy",
        "unit": "km",
        "factor_kg_co2e": "0.147870",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "travel_air",
        "name": "Long-Haul Premium Economy",
        "unit": "km",
        "factor_kg_co2e": "0.236600",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "travel_air",
        "name": "Long-Haul Business",
        "unit": "km",
        "factor_kg_co2e": "0.428820",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    {
        "category": "travel_air",
        "name": "Long-Haul First",
        "unit": "km",
        "factor_kg_co2e": "0.591640",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    # ── Rail Travel ──────────────────────────────────────────────
    {
        "category": "travel_rail",
        "name": "National Rail (average)",
        "unit": "km",
        "factor_kg_co2e": "0.035490",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
    # ── Road Travel (Car Rental) ─────────────────────────────────
    {
        "category": "travel_road",
        "name": "Average Car (unknown fuel)",
        "unit": "km",
        "factor_kg_co2e": "0.171480",
        "source": "DEFRA",
        "year": 2024,
        "region": "Global",
    },
]


class Command(BaseCommand):
    help = "Seed the EmissionFactor table with EPA/DEFRA emission factors."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing emission factors before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = EmissionFactor.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing factors."))

        created = 0
        skipped = 0

        for f in FACTORS:
            obj, was_created = EmissionFactor.objects.get_or_create(
                category=f["category"],
                name=f["name"],
                unit=f["unit"],
                year=f["year"],
                region=f["region"],
                defaults={
                    "factor_kg_co2e": f["factor_kg_co2e"],
                    "source": f["source"],
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded emission factors: {created} created, {skipped} skipped (already exist)."
            )
        )

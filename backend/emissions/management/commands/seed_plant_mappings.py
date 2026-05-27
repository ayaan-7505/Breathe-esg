"""
Management command: seed_plant_mappings

Creates PlantCodeMapping entries for the SAP WERKS codes found in
sample_data/sap_fuel_export.csv.
"""

from django.core.management.base import BaseCommand
from core.models import Tenant
from emissions.models import PlantCodeMapping


PLANT_MAPPINGS = [
    {
        "plant_code": "1000",
        "facility_name": "Plant A — European HQ",
        "location": "Frankfurt, Germany",
        "country": "DE",
    },
    {
        "plant_code": "2000",
        "facility_name": "Plant B — European Manufacturing",
        "location": "Munich, Germany",
        "country": "DE",
    },
    {
        "plant_code": "3000",
        "facility_name": "Plant C — US Operations",
        "location": "Houston, TX, USA",
        "country": "US",
    },
]


class Command(BaseCommand):
    help = "Seed PlantCodeMapping table for demo SAP plant codes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-slug",
            type=str,
            default="demo-corp",
            help="Slug of the tenant to attach mappings to.",
        )

    def handle(self, *args, **options):
        slug = options["tenant_slug"]
        tenant = Tenant.objects.filter(slug=slug).first()

        if not tenant:
            self.stdout.write(self.style.WARNING(
                f"Tenant '{slug}' not found. Run seed_demo_data first."
            ))
            return

        created = 0
        for pm in PLANT_MAPPINGS:
            _, was_created = PlantCodeMapping.objects.get_or_create(
                tenant=tenant,
                plant_code=pm["plant_code"],
                defaults={
                    "facility_name": pm["facility_name"],
                    "location": pm["location"],
                    "country": pm["country"],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created} plant code mappings for tenant '{slug}'.")
        )

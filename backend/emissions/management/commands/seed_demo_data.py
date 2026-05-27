"""
Management command: seed_demo_data

Creates a demo tenant, admin user, analyst user, and viewer user for
local development and testing. Optionally ingests the sample CSV files.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from rest_framework.authtoken.models import Token

from core.models import Tenant, CustomUser


DEMO_TENANT = {
    "name": "Demo Corporation",
    "slug": "demo-corp",
}

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@demo-corp.com",
        "password": "admin1234",
        "first_name": "Demo",
        "last_name": "Admin",
        "role": "admin",
    },
    {
        "username": "analyst",
        "email": "analyst@demo-corp.com",
        "password": "analyst1234",
        "first_name": "Demo",
        "last_name": "Analyst",
        "role": "analyst",
    },
    {
        "username": "viewer",
        "email": "viewer@demo-corp.com",
        "password": "viewer1234",
        "first_name": "Demo",
        "last_name": "Viewer",
        "role": "viewer",
    },
]


class Command(BaseCommand):
    help = (
        "Seed demo data: tenant, users, emission factors, and plant mappings. "
        "Safe to run multiple times — uses get_or_create."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-superuser",
            action="store_true",
            help="Also create a super_admin user (username: superadmin, pw: superadmin1234).",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Seeding Demo Data ==="))

        # 1. Tenant
        tenant, created = Tenant.objects.get_or_create(
            slug=DEMO_TENANT["slug"],
            defaults={"name": DEMO_TENANT["name"]},
        )
        status = "created" if created else "already exists"
        self.stdout.write(f"  Tenant '{tenant.name}': {status}")

        # 2. Users
        for u in DEMO_USERS:
            user, created = CustomUser.objects.get_or_create(
                username=u["username"],
                defaults={
                    "email": u["email"],
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "role": u["role"],
                    "tenant": tenant,
                },
            )
            if created:
                user.set_password(u["password"])
                user.save()
            token, _ = Token.objects.get_or_create(user=user)
            self.stdout.write(
                f"  User '{user.username}' ({user.role}): "
                f"{'created' if created else 'exists'} | Token: {token.key}"
            )

        # 3. Optional superuser
        if options["with_superuser"]:
            su, created = CustomUser.objects.get_or_create(
                username="superadmin",
                defaults={
                    "email": "superadmin@breathe-esg.io",
                    "first_name": "Super",
                    "last_name": "Admin",
                    "role": "super_admin",
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            if created:
                su.set_password("superadmin1234")
                su.save()
            token, _ = Token.objects.get_or_create(user=su)
            self.stdout.write(
                f"  Superuser 'superadmin': "
                f"{'created' if created else 'exists'} | Token: {token.key}"
            )

        # 4. Emission factors
        self.stdout.write("  Seeding emission factors...")
        call_command("seed_emission_factors")

        # 5. Plant mappings
        self.stdout.write("  Seeding plant code mappings...")
        call_command("seed_plant_mappings", tenant_slug=DEMO_TENANT["slug"])

        self.stdout.write(self.style.SUCCESS("\n[OK] Demo data seeding complete."))
        self.stdout.write(
            "\nQuick-start credentials:\n"
            "  Admin   -> admin / admin1234\n"
            "  Analyst -> analyst / analyst1234\n"
            "  Viewer  -> viewer / viewer1234\n"
        )

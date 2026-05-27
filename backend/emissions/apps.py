from django.apps import AppConfig


class EmissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "emissions"
    verbose_name = "Emissions & Review"

    def ready(self):
        from audit.signals import register_audited_model
        from .models import EmissionRecord
        register_audited_model(EmissionRecord)

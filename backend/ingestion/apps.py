from django.apps import AppConfig


class IngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ingestion"
    verbose_name = "Data Ingestion"

    def ready(self):
        from audit.signals import register_audited_model
        from .models import IngestionJob
        register_audited_model(IngestionJob)

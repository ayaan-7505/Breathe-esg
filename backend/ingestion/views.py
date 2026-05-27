"""Ingestion views — file upload, job list / detail."""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from core.permissions import IsAnalystOrAbove

from .models import IngestionJob
from .serializers import (
    IngestionJobSerializer,
    IngestionJobDetailSerializer,
    UploadSerializer,
)
from .parsers import run_parser


class UploadView(APIView):
    """
    POST /api/ingestion/upload/
    Upload a CSV file with a ``source_type`` (sap | utility | travel).
    The file is parsed synchronously and raw rows are stored.
    """

    permission_classes = [permissions.IsAuthenticated, IsAnalystOrAbove]

    def post(self, request):
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        source_type = serializer.validated_data["source_type"]
        tenant = request.user.tenant

        if not tenant:
            return Response(
                {"detail": "User must belong to a tenant to upload files."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create job
        job = IngestionJob.objects.create(
            tenant=tenant,
            uploaded_by=request.user,
            source_type=source_type,
            file_name=uploaded_file.name,
            file=uploaded_file,
        )

        # Log upload
        AuditLog.log(
            action=AuditLog.Action.UPLOAD,
            entity_type="ingestion.IngestionJob",
            entity_id=str(job.pk),
            tenant=tenant,
            user=request.user,
            metadata={"file_name": uploaded_file.name, "source_type": source_type},
        )

        # Parse synchronously
        run_parser(job)
        job.refresh_from_db()

        # Trigger normalisation for valid rows
        if job.status == "completed" and job.valid_rows > 0:
            try:
                from emissions.normalizer import normalize_job
                normalize_job(job)
            except Exception:
                pass  # normalisation failure should not fail the upload

        return Response(
            IngestionJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )


class IngestionJobListView(generics.ListAPIView):
    """
    GET /api/ingestion/jobs/
    Lists ingestion jobs for the current tenant.
    """

    serializer_class = IngestionJobSerializer
    filterset_fields = ["source_type", "status"]
    ordering_fields = ["created_at", "completed_at"]

    def get_queryset(self):
        user = self.request.user
        qs = IngestionJob.objects.select_related("uploaded_by")
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)
        return qs


class IngestionJobDetailView(generics.RetrieveAPIView):
    """
    GET /api/ingestion/jobs/{id}/
    Job detail with all raw rows.
    """

    serializer_class = IngestionJobDetailSerializer
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        qs = IngestionJob.objects.select_related("uploaded_by")
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)
        return qs


class JobErrorsView(APIView):
    """
    GET /api/ingestion/jobs/{id}/errors/
    Returns list of validation errors for failed rows in the job.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        qs = IngestionJob.objects.all()
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)

        job = qs.filter(pk=pk).first()
        if not job:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        from .models import SAPRawRow, UtilityRawRow, TravelRawRow

        # Query all invalid raw rows for this job
        if job.source_type == "sap":
            invalid_rows = SAPRawRow.objects.filter(job=job, is_valid=False).order_by("row_number")
        elif job.source_type == "utility":
            invalid_rows = UtilityRawRow.objects.filter(job=job, is_valid=False).order_by("row_number")
        elif job.source_type == "travel":
            invalid_rows = TravelRawRow.objects.filter(job=job, is_valid=False).order_by("row_number")
        else:
            invalid_rows = []

        # Flatten errors
        errors_list = []
        for row in invalid_rows:
            # Safely check validation_errors
            errors = row.validation_errors
            if isinstance(errors, dict):
                # If stored as a single dict or other format
                errors = [errors]
            elif not isinstance(errors, list):
                errors = []

            for err in errors:
                if not isinstance(err, dict):
                    continue
                field_name = err.get("field")
                val = None
                if field_name and row.raw_data:
                    # Look up raw_data keys (case-insensitive or strip)
                    for k, v in row.raw_data.items():
                        if k.lower().strip() == field_name.lower().strip():
                            val = v
                            break
                    if val is None:
                        val = row.raw_data.get(field_name)

                errors_list.append({
                    "row": row.row_number,
                    "field": field_name,
                    "value": val,
                    "message": err.get("message"),
                })

        return Response(errors_list)

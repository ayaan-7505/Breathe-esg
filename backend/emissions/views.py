"""
Emissions views — list, detail, review workflow, bulk actions, dashboard summary.

Review workflow
---------------
pending → reviewed → approved → locked
           ↘ flagged ↗

Locked records are immutable.
"""

from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from core.permissions import IsAnalystOrAbove, IsAdminOrAbove

from .models import EmissionRecord, EmissionFactor, PlantCodeMapping
from .serializers import (
    EmissionRecordSerializer,
    EmissionRecordUpdateSerializer,
    EmissionFactorSerializer,
    PlantCodeMappingSerializer,
    BulkActionSerializer,
)


# =====================================================================
#  Emission Record List / Detail
# =====================================================================
class EmissionRecordListView(generics.ListAPIView):
    """
    GET /api/emissions/
    Filterable, paginated list of emission records for the user's tenant.
    """

    serializer_class = EmissionRecordSerializer
    search_fields = ["activity_type", "facility"]
    ordering_fields = ["record_date", "co2e_kg", "created_at", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = EmissionRecord.objects.select_related("reviewed_by")
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)

        # 1. Filter by scopes
        scopes = self.request.query_params.get("scope")
        if scopes:
            scope_list = []
            for s in scopes.split(","):
                s = s.strip()
                if s == "1":
                    scope_list.append("scope_1")
                elif s == "2":
                    scope_list.append("scope_2")
                elif s == "3":
                    scope_list.append("scope_3")
                else:
                    scope_list.append(s)
            qs = qs.filter(scope__in=scope_list)

        # 2. Filter by source types
        sources = self.request.query_params.get("source_type")
        if sources:
            source_list = [s.strip().lower() for s in sources.split(",")]
            qs = qs.filter(source_type__in=source_list)

        # 3. Filter by statuses
        statuses = self.request.query_params.get("status")
        if statuses:
            status_list = [s.strip() for s in statuses.split(",")]
            qs = qs.filter(status__in=status_list)

        # 4. Filter by date range
        date_from = self.request.query_params.get("date_from") or self.request.query_params.get("start_date")
        if date_from:
            qs = qs.filter(record_date__gte=date_from)

        date_to = self.request.query_params.get("date_to") or self.request.query_params.get("end_date")
        if date_to:
            qs = qs.filter(record_date__lte=date_to)

        # 5. Filter by facility (if any)
        facility = self.request.query_params.get("facility")
        if facility:
            qs = qs.filter(facility__iexact=facility)

        # 6. Filter by reporting period (if any)
        reporting_period = self.request.query_params.get("reporting_period")
        if reporting_period:
            qs = qs.filter(reporting_period=reporting_period)

        return qs


class EmissionRecordDetailView(generics.RetrieveAPIView):
    """
    GET /api/emissions/{id}/
    Single emission record detail.
    """

    serializer_class = EmissionRecordSerializer

    def get_queryset(self):
        user = self.request.user
        qs = EmissionRecord.objects.select_related("reviewed_by")
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)
        return qs


class EmissionRecordUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/emissions/{id}/
    Update an emission record (if not locked).
    Analysts and above can modify scope override, activity data, etc.
    """

    serializer_class = EmissionRecordUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAnalystOrAbove]
    http_method_names = ["patch"]

    def get_queryset(self):
        user = self.request.user
        qs = EmissionRecord.objects.all()
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)
        return qs

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.log(
            action=AuditLog.Action.UPDATE,
            entity_type="emissions.EmissionRecord",
            entity_id=str(instance.pk),
            tenant=instance.tenant,
            user=self.request.user,
            changes=serializer.validated_data,
        )


# =====================================================================
#  Single-record workflow actions
# =====================================================================
class ApproveRecordView(APIView):
    """
    POST /api/emissions/{id}/approve/
    Transitions: pending/reviewed/flagged → approved
    """

    permission_classes = [permissions.IsAuthenticated, IsAnalystOrAbove]

    def post(self, request, pk):
        record = self._get_record(request, pk)
        if not record:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if record.status == EmissionRecord.Status.LOCKED:
            return Response(
                {"detail": "Locked records cannot be modified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = record.status
        record.status = EmissionRecord.Status.APPROVED
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()

        AuditLog.log(
            action=AuditLog.Action.APPROVE,
            entity_type="emissions.EmissionRecord",
            entity_id=str(record.pk),
            tenant=record.tenant,
            user=request.user,
            changes={"status": {"old": old_status, "new": "approved"}},
        )
        return Response(EmissionRecordSerializer(record).data)

    def _get_record(self, request, pk):
        qs = EmissionRecord.objects.all()
        if request.user.role != "super_admin":
            qs = qs.filter(tenant=request.user.tenant)
        return qs.filter(pk=pk).first()


class FlagRecordView(APIView):
    """
    POST /api/emissions/{id}/flag/
    Marks a record as flagged (suspicious) with a reason.
    """

    permission_classes = [permissions.IsAuthenticated, IsAnalystOrAbove]

    def post(self, request, pk):
        record = self._get_record(request, pk)
        if not record:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if record.status == EmissionRecord.Status.LOCKED:
            return Response(
                {"detail": "Locked records cannot be modified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "")
        old_status = record.status
        record.status = EmissionRecord.Status.FLAGGED
        record.flag_reason = reason
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()

        AuditLog.log(
            action=AuditLog.Action.FLAG,
            entity_type="emissions.EmissionRecord",
            entity_id=str(record.pk),
            tenant=record.tenant,
            user=request.user,
            changes={"status": {"old": old_status, "new": "flagged"}},
            metadata={"reason": reason},
        )
        return Response(EmissionRecordSerializer(record).data)

    def _get_record(self, request, pk):
        qs = EmissionRecord.objects.all()
        if request.user.role != "super_admin":
            qs = qs.filter(tenant=request.user.tenant)
        return qs.filter(pk=pk).first()


class LockRecordView(APIView):
    """
    POST /api/emissions/{id}/lock/
    Locks a record for audit. Only approved records can be locked.
    Admin+ only.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminOrAbove]

    def post(self, request, pk):
        record = self._get_record(request, pk)
        if not record:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if record.status == EmissionRecord.Status.LOCKED:
            return Response(
                {"detail": "Record is already locked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if record.status != EmissionRecord.Status.APPROVED:
            return Response(
                {"detail": "Only approved records can be locked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = record.status
        record.status = EmissionRecord.Status.LOCKED
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()

        AuditLog.log(
            action=AuditLog.Action.LOCK,
            entity_type="emissions.EmissionRecord",
            entity_id=str(record.pk),
            tenant=record.tenant,
            user=request.user,
            changes={"status": {"old": old_status, "new": "locked"}},
        )
        return Response(EmissionRecordSerializer(record).data)

    def _get_record(self, request, pk):
        qs = EmissionRecord.objects.all()
        if request.user.role != "super_admin":
            qs = qs.filter(tenant=request.user.tenant)
        return qs.filter(pk=pk).first()


# =====================================================================
#  Bulk Actions
# =====================================================================
class BulkActionView(APIView):
    """
    POST /api/emissions/bulk-action/
    Apply an action (approve/reject/flag/lock/review) to multiple records.
    """

    permission_classes = [permissions.IsAuthenticated, IsAnalystOrAbove]

    def post(self, request):
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data["ids"]
        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        qs = EmissionRecord.objects.filter(pk__in=ids)
        if request.user.role != "super_admin":
            qs = qs.filter(tenant=request.user.tenant)

        # Exclude locked records from mutation
        qs = qs.exclude(status=EmissionRecord.Status.LOCKED)

        # For lock action, only allow approved records
        if action == "lock":
            qs = qs.filter(status=EmissionRecord.Status.APPROVED)

        status_map = {
            "approve": EmissionRecord.Status.APPROVED,
            "reject": EmissionRecord.Status.PENDING,  # Reset to pending
            "flag": EmissionRecord.Status.FLAGGED,
            "lock": EmissionRecord.Status.LOCKED,
            "review": EmissionRecord.Status.REVIEWED,
        }
        action_map = {
            "approve": AuditLog.Action.APPROVE,
            "reject": AuditLog.Action.REJECT,
            "flag": AuditLog.Action.FLAG,
            "lock": AuditLog.Action.LOCK,
            "review": AuditLog.Action.STATUS_CHANGE,
        }

        new_status = status_map[action]
        affected_count = 0

        for record in qs:
            old_status = record.status
            record.status = new_status
            record.reviewed_by = request.user
            record.reviewed_at = timezone.now()
            if action == "flag":
                record.flag_reason = reason
            record.save()

            AuditLog.log(
                action=action_map[action],
                entity_type="emissions.EmissionRecord",
                entity_id=str(record.pk),
                tenant=record.tenant,
                user=request.user,
                changes={"status": {"old": old_status, "new": new_status}},
                metadata={"reason": reason} if reason else {},
            )
            affected_count += 1

        return Response({
            "action": action,
            "requested": len(ids),
            "affected": affected_count,
            "skipped": len(ids) - affected_count,
        })


# =====================================================================
#  Dashboard Summary
# =====================================================================
class EmissionSummaryView(APIView):
    """
    GET /api/emissions/summary/
    Dashboard aggregations — total CO₂e grouped by scope, month, facility,
    or source_type.

    Query params
    ------------
    - group_by: scope | month | facility | source_type (default: scope)
    - start_date, end_date: filter by record_date range
    - scope: filter by specific scope
    - status: filter by status (default: only approved + locked)
    """

    def get(self, request):
        user = request.user
        qs = EmissionRecord.objects.all()
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)

        # 1. Filter by scopes
        scopes = request.query_params.get("scope")
        if scopes:
            scope_list = []
            for s in scopes.split(","):
                s = s.strip()
                if s == "1":
                    scope_list.append("scope_1")
                elif s == "2":
                    scope_list.append("scope_2")
                elif s == "3":
                    scope_list.append("scope_3")
                else:
                    scope_list.append(s)
            qs = qs.filter(scope__in=scope_list)

        # 2. Filter by source types
        sources = request.query_params.get("source_type")
        if sources:
            source_list = [s.strip().lower() for s in sources.split(",")]
            qs = qs.filter(source_type__in=source_list)

        # 3. Filter by statuses
        statuses = request.query_params.get("status")
        if statuses:
            status_list = [s.strip() for s in statuses.split(",")]
            qs = qs.filter(status__in=status_list)

        # 4. Filter by date range
        date_from = request.query_params.get("date_from") or request.query_params.get("start_date")
        if date_from:
            qs = qs.filter(record_date__gte=date_from)

        date_to = request.query_params.get("date_to") or request.query_params.get("end_date")
        if date_to:
            qs = qs.filter(record_date__lte=date_to)

        group_by = request.query_params.get("group_by", "scope")

        # Grand totals
        totals = qs.aggregate(
            total_co2e_kg=Sum("co2e_kg"),
            total_records=Count("id"),
        )

        # Status breakdown
        status_breakdown = list(
            qs.values("status").annotate(
                count=Count("id"),
                co2e_kg=Sum("co2e_kg"),
            ).order_by("status")
        )

        # Grouped breakdown
        if group_by == "month":
            breakdown = list(
                qs.annotate(month=TruncMonth("record_date"))
                .values("month")
                .annotate(
                    co2e_kg=Sum("co2e_kg"),
                    count=Count("id"),
                )
                .order_by("month")
            )
            # Serialise month to string
            for item in breakdown:
                if item["month"]:
                    item["month"] = item["month"].strftime("%Y-%m")
        elif group_by == "facility":
            breakdown = list(
                qs.values("facility")
                .annotate(
                    co2e_kg=Sum("co2e_kg"),
                    count=Count("id"),
                )
                .order_by("-co2e_kg")[:20]
            )
        elif group_by == "source_type":
            breakdown = list(
                qs.values("source_type")
                .annotate(
                    co2e_kg=Sum("co2e_kg"),
                    count=Count("id"),
                )
                .order_by("source_type")
            )
        else:  # scope
            breakdown = list(
                qs.values("scope")
                .annotate(
                    co2e_kg=Sum("co2e_kg"),
                    count=Count("id"),
                )
                .order_by("scope")
            )

        # Build a status mapping for easy count lookup
        status_counts = {item["status"]: item["count"] for item in status_breakdown}

        total_co2e_kg = totals.get("total_co2e_kg") or 0
        total_co2e_tonnes = float(total_co2e_kg) / 1000.0

        return Response({
            "totals": totals,
            "status_breakdown": status_breakdown,
            "breakdown": breakdown,
            "group_by": group_by,
            # Frontend compatibility fields at the top level
            "total_co2e": round(total_co2e_tonnes, 2),
            "pending": status_counts.get("pending", 0),
            "approved": status_counts.get("approved", 0),
            "flagged": status_counts.get("flagged", 0),
            "locked": status_counts.get("locked", 0),
        })


# =====================================================================
#  Emission Factor & PlantCodeMapping CRUD
# =====================================================================
class EmissionFactorListView(generics.ListCreateAPIView):
    """
    GET  /api/emissions/factors/ — list all emission factors
    POST /api/emissions/factors/ — create a new factor (admin+)
    """

    serializer_class = EmissionFactorSerializer
    filterset_fields = ["category", "source", "year", "is_active"]

    def get_queryset(self):
        return EmissionFactor.objects.all()

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsAdminOrAbove()]
        return [permissions.IsAuthenticated()]


class PlantCodeMappingListView(generics.ListCreateAPIView):
    """
    GET  /api/emissions/plant-mappings/ — list plant code mappings
    POST /api/emissions/plant-mappings/ — create mapping (admin+)
    """

    serializer_class = PlantCodeMappingSerializer
    filterset_fields = ["plant_code"]

    def get_queryset(self):
        user = self.request.user
        qs = PlantCodeMapping.objects.all()
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)
        return qs

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsAdminOrAbove()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


# =====================================================================
#  Dashboard Charts
# =====================================================================
class EmissionChartView(APIView):
    """
    GET /api/emissions/charts/
    Returns monthly breakdown by scope and distribution by source type,
    filtered according to dashboard parameters.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = EmissionRecord.objects.all()
        if user.role != "super_admin":
            qs = qs.filter(tenant=user.tenant)

        # Filters
        scopes = request.query_params.get("scope")
        if scopes:
            qs = qs.filter(scope__in=scopes.split(","))

        sources = request.query_params.get("source_type")
        if sources:
            qs = qs.filter(source_type__in=sources.split(","))

        statuses = request.query_params.get("status")
        if statuses:
            qs = qs.filter(status__in=statuses.split(","))

        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(record_date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(record_date__lte=date_to)

        # 1. Bar Data (Monthly breakdown by scope)
        monthly_data = (
            qs.annotate(month_date=TruncMonth("record_date"))
            .values("month_date", "scope")
            .annotate(total_co2e=Sum("co2e_kg"))
            .order_by("month_date")
        )

        scope_mapping = {
            "scope_1": "Scope 1",
            "scope_2": "Scope 2",
            "scope_3": "Scope 3",
        }

        months_dict = {}
        for row in monthly_data:
            m_date = row["month_date"]
            if not m_date:
                continue
            month_label = m_date.strftime("%b")  # e.g., 'Jan', 'Feb'
            scope_key = row["scope"]
            scope_label = scope_mapping.get(scope_key, scope_key)
            co2e_val_tonnes = float(row["total_co2e"] or 0) / 1000.0

            if month_label not in months_dict:
                months_dict[month_label] = {
                    "month": month_label,
                    "Scope 1": 0.0,
                    "Scope 2": 0.0,
                    "Scope 3": 0.0,
                    "_order": m_date,
                }
            if scope_label in months_dict[month_label]:
                months_dict[month_label][scope_label] = round(co2e_val_tonnes, 2)

        sorted_bar_data = sorted(months_dict.values(), key=lambda x: x["_order"])
        for item in sorted_bar_data:
            item.pop("_order", None)

        # 2. Pie Data (Distribution by source type)
        source_data = (
            qs.values("source_type")
            .annotate(total_co2e=Sum("co2e_kg"))
            .order_by("-total_co2e")
        )

        source_labels_map = {
            "sap": "SAP (Energy)",
            "utility": "Utility Bills",
            "travel": "Travel Records",
        }

        sorted_pie_data = []
        for row in source_data:
            src = row["source_type"]
            val_tonnes = float(row["total_co2e"] or 0) / 1000.0
            name = source_labels_map.get(src, src.upper() if src else "Other")
            sorted_pie_data.append({
                "name": name,
                "value": round(val_tonnes, 2),
            })

        return Response({
            "scope_data": sorted_bar_data,
            "source_data": sorted_pie_data,
        })

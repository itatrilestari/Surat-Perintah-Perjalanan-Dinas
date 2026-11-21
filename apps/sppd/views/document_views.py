from django.db import transaction
from apps.sppd.utils import validate_current_approver
from rest_framework import generics, status, viewsets, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Value, DecimalField
from decimal import Decimal
from django.db.models.functions import Coalesce
from django.template.loader import render_to_string
from apps.api.utils import CustomPagination, create_log
from sppd.models import Document, Approver, PaguSPPD, TravelAssignment, Province, SPJ
from apps.sppd.serializers.document_serializers import SPPDSerializer, SPPDEstimateCostSerializer, SPPDUploadSPJ, SPPDDashboardSerializer, SPJDetail, AddressbookListSerializer
from django.contrib.auth.models import Group, User
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import re, os, base64
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile

class ApproverActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, help_text="Optional note for the approval action.")

class HTMLDocumentResponseSerializer(serializers.Serializer):
    html = serializers.CharField()

@extend_schema_view(
    get=extend_schema(
        tags=["SPPD"],
        summary="List SPPD documents",
        parameters=[
            OpenApiParameter(
                name="state",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filter documents by state. One of: All, Need Approved, Waiting PPK, "
                    "Waiting KPA, Approved, Process SPJ, Rejected, Cancelled."
                ),
            ),
        ],
    ),
    post=extend_schema(tags=["SPPD"], summary="Create a new SPPD document"),
)
class SPPDListCreateAPIView(generics.ListCreateAPIView):
    pagination_class = CustomPagination
    serializer_class = SPPDSerializer

    def list(self, request, *args, **kwargs):
        query = self.get_queryset()
        paginated_queryset = self.paginate_queryset(query)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instances = serializer.save() 
        response_serializer = self.get_serializer(instances, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        get_state = self.request.query_params.get("state")
        get_search = self.request.query_params.get("search")
        queryset = Document.objects.filter(is_delete=False, readers=self.request.user)

        print("q", queryset)

        user = self.request.user
        if get_state == "All":
            queryset = queryset
        elif get_state == "Need Approved":
            queryset = queryset.filter(authors=self.request.user).exclude(state__in=['rejected', 'complete', 'cancelled'])
        elif get_state == "Waiting PPK":
            queryset = queryset.filter(state='waiting_ppk')
        elif get_state == "Waiting KPA":
            queryset = queryset.filter(state='waiting_kpa')
        elif get_state == "Approved":
            queryset = queryset.filter(state='approved')
        elif get_state == "Process SPJ":
            queryset = queryset.filter(
                # Q(state='draft_spj') |
                Q(state='spj_verification') |
                Q(state='spj_ratification') |
                Q(state='spj_revision') |
                # Q(state='rejected') |
                Q(state='waiting_spj_rejection')
            )
        elif get_state == "Rejected":
            queryset = queryset.filter(state='rejected')
        elif get_state == "Cancelled":
            queryset = queryset.filter(state='cancelled')
        elif get_state == "Revision":
            queryset = queryset.filter(state='revision')
        elif get_state == "Done":
            queryset = queryset.filter(state='complete')
        if get_search:
            queryset = queryset.filter(Q(assignment_basis__icontains = get_search) | Q(travel_assignment__destination_city__icontains=get_search) | Q(departure_date__icontains=get_search) | Q(submission_type__icontains=get_search) | Q(total_allowance__icontains=get_search) | Q(state__icontains=get_search)) 
        return queryset.exclude(state='sppd_draft').order_by('-updated_at')

@extend_schema(tags=["SPPD"], summary="Estimate SPPD travel costs")
class SPPDEstimateCostCreateAPIView(generics.CreateAPIView):
    serializer_class = SPPDEstimateCostSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema_view(
    get=extend_schema(tags=["SPPD"], summary="Retrieve an SPPD document"),
    put=extend_schema(tags=["SPPD"], summary="Update an SPPD document"),
    patch=extend_schema(tags=["SPPD"], summary="Partially update an SPPD document"),
    delete=extend_schema(tags=["SPPD"], summary="Delete (soft-delete) an SPPD document"),
)
class SPPDRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SPPDSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        queryset = Document.objects.filter(is_delete=False)
        # lock row hanya untuk operasi tulis
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            queryset = queryset.select_for_update()
        return queryset

    def get_object(self):
        document = super().get_object()
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            validate_current_approver(document.id, self.request)
        return document

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        document = serializer.save()
        create_log(self.request.user, 'Update', 'SPPD', document)

    def perform_destroy(self, instance):
        instance.is_delete = True
        instance.save()
        create_log(self.request.user, 'Delete', 'SPPD', instance)


class SPPDAPIView(viewsets.GenericViewSet):
    serializer_class = SPPDSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        return Document.objects.filter(is_delete=False).select_for_update()


    def response(self, document):
        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["SPPD"],
        summary="Approve an SPPD document",
        request=ApproverActionSerializer,
        responses={200: SPPDSerializer},
    )
    @transaction.atomic
    def approve(self, request, *args, **kwargs):
        document = self.get_object()
        validate_current_approver(document.id, request)

        # Update approver action
        current_approver = document.get_current_approver
        if current_approver:
            current_approver.action = 'approve'
            current_approver.save(update_fields=['action'])

        document.current = (document.current or 0) + 1
        document.set_document_state()
        document.authors = document.get_current_approver.user
        document.save(update_fields=['current', 'state', 'authors'])

        create_log(request.user, 'approve', document, request.data.get('notes'))
        return self.response(document)

    @extend_schema(
        tags=["SPPD"],
        summary="Reject an SPPD document",
        request=ApproverActionSerializer,
        responses={200: SPPDSerializer},
    )
    @transaction.atomic
    def reject(self, request, *args, **kwargs):
        document = self.get_object()
        validate_current_approver(document.id, request)

        # Update approver action
        if document.spj.exists():
            document.current = document.get_approvers_list(type='spj', role='employee').last().sequence
            document.set_document_state(declined=True)
            document.authors = document.get_current_approver.user
        current_approver = document.get_current_approver
        if current_approver:
            current_approver.action = 'reject'
            current_approver.save(update_fields=['action'])

        document.set_document_state(declined=True)
        document.authors = document.get_current_approver.user
        document.save(update_fields=['state', 'authors'])

        create_log(request.user, 'reject', document, request.data.get('notes'))
        return self.response(document)

    @transaction.atomic
    def cancel(self, request, *args, **kwargs):
        document = self.get_object()
        validate_current_approver(document.id, request, action="cancel")

        # Update approver action
        current_approver = document.get_current_approver
        if current_approver:
            current_approver.action = 'cancel'
            current_approver.save(update_fields=['action'])

        document.get_approvers_list(role='ppk')[0].action = 'cancel'
        
        document.set_document_state(cancel=True)
        document.authors = document.get_current_approver.user
        document.save(update_fields=['state', 'authors'])

        create_log(request.user, 'cancel', document, request.data.get('notes'))
        return self.response(document)

class AddressbookListAPIView(generics.ListAPIView):
    pagination_class = CustomPagination
    serializer_class = AddressbookListSerializer

    def list(self, request, *args, **kwargs):
        query = self.get_queryset()
        paginated_queryset = self.paginate_queryset(query)
        serializer = self.get_serializer(paginated_queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        type = self.kwargs.get('type')
        name = f'sppd_{type}'
        group = Group.objects.filter(name=name).first()
        if not group:
            return User.objects.none()
        return group.user_set.all()

@extend_schema(
    tags=["SPPD"],
    summary="Generate the SPPD HTML document",
    responses={200: HTMLDocumentResponseSerializer},
)
class GenerateHTMLDocumentSPPDRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Document.objects.filter(is_delete=False)
    serializer_class = SPPDSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.file:
            instance.file.open("r")
            html = instance.file.read()
            instance.file.close()
            return Response({
                "html": html
            })
        else:
            logo_path = os.path.join(
                settings.BASE_DIR,
                'data',
                'logo.jpg'
            )

            with open(logo_path, 'rb') as image_file:
                logo_base64 = base64.b64encode(
                    image_file.read()
                ).decode('utf-8')

            kpa = instance.approver_document.filter(role='kpa').first()

            ppk = instance.approver_document.filter(role='ppk')
            ppk_list = []
            for p in ppk:
                ppk_list.append({
                    "name": p.user.profile_set.first().name
                })

            html = render_to_string(
                "main/template_sppd.html",
                {
                    "doc": instance,
                    "logo_base64": logo_base64,
                    "kpa_name": kpa.user.profile_set.first(),
                    "ppk_list": ppk_list 
                },
                request=request
            )

            html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
            html = re.sub(r">\s+<", "><", html)
            html = re.sub(r">\s+([^<]*?)\s+<", r">\1<", html)
            html = re.sub(r"\s+", " ", html)
            html = html.strip()

            subject = instance.subject if instance.subject else f"SPPD - {instance.assignment_basis}"

            instance.file.save(subject + '.html', ContentFile(html.encode('utf8')))

            return Response({
                "html": html
            })

@extend_schema(tags=["SPJ"], summary="Upload SPJ (travel report) documents")
class SPPDUploadSPJCreateAPIView(generics.CreateAPIView):
    serializer_class = SPPDUploadSPJ
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instances = serializer.save() 
        response_serializer = self.get_serializer(instances, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class SPPDDashboardAPIView(viewsets.GenericViewSet):
    def get(self, request):
        current_year = timezone.now().year

        documents = Document.objects.filter(
            is_delete=False,
            created_at__year=current_year,
            readers=self.request.user
        ).exclude(state='sppd_draft')

        # 1. Document statistics
        stats = documents.aggregate(
            total_document=Count("id"),

            complete=Count(
                "id",
                filter=Q(state="complete")
            ),

            approved=Count(
                "id",
                filter=Q(state="approved")
            ),

            waiting_ppk=Count(
                "id",
                filter=Q(state="waiting_ppk")
            ),

            verification=Count(
                "id",
                filter=Q(state="spj_verification")
            ),

            rejected=Count(
                "id",
                filter=Q(state="rejected")
            ),

            need_approval=Count(
                "id",
                filter=(
                    Q(authors=self.request.user)
                    & ~Q(state__in=['rejected', 'complete'])
                )
            ),

            total_allowance_all=Coalesce(
                Sum(
                    "total_allowance",
                    filter=Q(state="complete")
                ),
                Value(Decimal("0")),
                output_field=DecimalField(
                    max_digits=20,
                    decimal_places=0
                )
            )
        )

        # 2. Total pagu
        total_pagu = PaguSPPD.objects.filter(
            is_delete=False
        ).aggregate(
            total=Coalesce(
                Sum("pagu"),
                Value(Decimal("0"))
            )
        )["total"]

        # 3. Budget realization
        total_allowance = stats["total_allowance_all"]

        percentage = (
            (total_allowance / total_pagu) * 100
            if total_pagu > 0 else 0
        )

        budget_realization = {
            "pagu": total_pagu,
            "budget_spent": total_allowance,
            "budget_spent_persen": round(percentage, 2),
            "remaining_budget": total_pagu - total_allowance
        }

        # 4. Latest activities
        latest_documents = Document.objects.filter(
            is_delete=False,
            created_at__year=current_year
        ).select_related(
            "travel_purpose"
        ).prefetch_related(
            "travel_assignment"
        ).order_by(
            "-created_at", "-id"
        )[:4]

        latest_activities = []

        for d in latest_documents:
            latest_activities.append({
                "id": d.id,
                "assignment_basis": d.assignment_basis,
                "destination_city": [
                    t.destination_city
                    for t in d.travel_assignment.all()
                ],
                "departure_date": d.departure_date,
                "travel_purpose": (
                    d.travel_purpose.name
                    if d.travel_purpose else None
                ),
                "state": d.state
            })

        # 5. Popular destinations
        popular_destinations = list(
            TravelAssignment.objects.filter(
                document__is_delete=False,
                document__created_at__year=current_year
            )
            .exclude(destination_city__isnull=True)
            .exclude(destination_city="")
            .values("destination_city")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
            .values("destination_city", "total")
        )

        popular_destinations = [
            {
                "name": p["destination_city"],
                "total": p["total"]
            }
            for p in popular_destinations
        ]

        # 6. Badge
        badge = {
            "total_document": stats["total_document"],
            "need_approval": stats["need_approval"],
            "approved": stats["approved"],
            "province": Province.objects.filter(
                is_delete=False
            ).count(),
            "realization": total_allowance
        }

        return Response({
            "latest_activities": latest_activities,

            "status_distribution": {
                "total_document": stats["total_document"],
                "complete": stats["complete"],
                "approved": stats["approved"],
                "waiting_ppk": stats["waiting_ppk"],
                "verification": stats["verification"],
                "rejected": stats["rejected"]
            },

            "popular_destinations": popular_destinations,

            "budget_realization": budget_realization,

            "badge": badge
        })

class SPJRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SPJ.objects.filter(is_delete=False)
    # serializer_class = SPJDetail
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method == "PUT" or self.request.method == "PATCH":
            return SPPDUploadSPJ
        return SPJDetail

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_delete = True
        instance.save()
        return Response({
            "message": "Berhasil hapus SPJ",
            "data": {
                "id": str(instance.id)
            }
        }, status=status.HTTP_200_OK)
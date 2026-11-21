import json
from rest_framework import serializers
from django.db import transaction
from sppd.models import Document, TravelAssignment, Approver, TravelPurpose, Transportation, SBMMaster, BudgetAccount, Issuer, SPJ, PaguSPPD, Province
from django.contrib.auth.models import User, Group
from sppd.utils import estimate_cost, get_budget_comparison, get_approver_data
from api.utils import create_log
from django.db.models import Count
from api.models import Profile

class TravelAssignmentSerializer(serializers.Serializer):
    origin_city = serializers.CharField(max_length=100)
    destination_city = serializers.CharField(max_length=100)
    duration_days = serializers.IntegerField(min_value=1)
    persons = serializers.IntegerField(min_value=1)
    daily_allowance = serializers.CharField()
    accommodation_allowance = serializers.CharField()
    lodging_allowance = serializers.CharField()
    sub_total_allowance = serializers.CharField()

class ApproverSerializer(serializers.ModelSerializer):
    nip = serializers.CharField(source='user.username', default=None, read_only=True)

    class Meta:
        model = Approver
        fields = ['nip', 'role', 'sequence', 'type', 'action', 'flag']

class SPPDSerializer(serializers.ModelSerializer):
    travel_assignment = TravelAssignmentSerializer(many=True)
    nip = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    approvers = serializers.SerializerMethodField()
    return_date = serializers.SerializerMethodField()
    travel_purpose = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    issuer = serializers.SerializerMethodField()
    nip_ppk = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    nip_kpa = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    total_allowance = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    subject = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    action = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_operator = serializers.BooleanField(required=False)
    nip_operator = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nip_issuer = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    travel_purpose_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    transportation_type_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    cost_category_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    budget_account_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    total_duration_days = serializers.SerializerMethodField()
    submission_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dp = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    doc_issuer = serializers.FileField(required=False)
    spj_id = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "nip",
            "travel_purpose_id",
            "travel_purpose",
            "assignment_basis",
            "travel_assignment",
            "departure_date",
            "return_date",
            "transportation_type_id",
            "issuer",
            "state",
            "approvers",
            "current",
            "nip_ppk",
            "nip_kpa",
            "total_allowance",
            "subject",
            "cost_category_id",
            "budget_account_id",
            "program_output_code",
            "submission_type",
            "dp",
            "action",
            "is_operator",
            "nip_operator",
            "nip_issuer",
            "total_duration_days",
            "dp",
            "doc_issuer",
            "spj_id",
            "authors",
            "file_issuer"
        ]
        
        read_only_fields = ["id"]


    def get_travel_purpose(self, obj):
        if obj.travel_purpose:
            return obj.travel_purpose.name
        return None

    def get_return_date(self, obj):
        if obj.departure_date:
            return obj.return_date
        return None

    def get_state(self, obj):
        return obj.get_state_display()

    def get_issuer(self, obj):
        if obj.issuer:
            profile_issuer = obj.issuer.user.profile_set.first()
            return {
                "nip": profile_issuer.nik,
                "name": profile_issuer.name,
                "working_unit": profile_issuer.working_unit.name
            }
        return None

    def get_total_duration_days(self, obj):
        total = 0
        travel = obj.travel_assignment.filter(is_delete=False).all()
        for t in travel:
            total += t.duration_days
        return total

    def get_spj_id(self, obj):
        spj = obj.spj.filter(is_delete=False)
        data = []
        for s in spj:
            data.append({
                "id": s.id
            })
        return data

    
    def to_internal_value(self, data):
        if hasattr(data, "getlist"):
            data = {
                key: data.get(key)
                for key in data.keys()
            }
        else:
            data = data.copy()

        # Parse travel_assignment
        travel_assignment = data.get("travel_assignment")
        if isinstance(travel_assignment, str):
            try:
                data["travel_assignment"] = json.loads(travel_assignment)
            except json.JSONDecodeError:
                raise serializers.ValidationError({
                    "travel_assignment": "Invalid JSON format"
                })

        # Parse nip_ppk
        nip_ppk = data.get("nip_ppk")
        if isinstance(nip_ppk, str):
            try:
                data["nip_ppk"] = json.loads(nip_ppk)
            except json.JSONDecodeError:
                raise serializers.ValidationError({
                    "nip_ppk": "Invalid JSON format"
                })

        return super().to_internal_value(data)
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        nip = validated_data.pop("nip", None)
        nip_operator = validated_data.pop("nip_operator", None)
        nip_ppk = validated_data.pop("nip_ppk", None)
        nip_kpa = validated_data.pop("nip_kpa", None)
        travel_assignments = validated_data.pop("travel_assignment", [])
        total_allowance = validated_data.pop("total_allowance", None)
        travel_purpose_id = validated_data.pop("travel_purpose_id", None)
        transportation_type_id = validated_data.pop("transportation_type_id", None)
        budget_account_id = validated_data.pop("budget_account_id", None)
        cost_category_id = validated_data.pop("cost_category_id", None)
        action = validated_data.pop("action", None)
        is_operator = validated_data.pop("is_operator", None)
        nip_issuer = validated_data.pop("nip_issuer", None)
        dp = validated_data.pop("dp", None)
        doc_issuer = validated_data.pop("doc_issuer", None)

        employee = None
        operator = None
        ppk = []
        kpa = None
        issuer = None
        issuer_data = None

        if nip:
            employee = Profile.objects.filter(nik=nip).first()
            if not employee:
                raise serializers.ValidationError("Employee doesn't exists")

        if nip_operator:
            operator = Profile.objects.filter(nik=nip_operator).first()
            if not operator:
                raise serializers.ValidationError("Operator doesn't exists")

        if nip_ppk:
            ppk = Profile.objects.filter(nik__in=nip_ppk)
            if not ppk.exists():
                raise serializers.ValidationError("PPK doesn't exists")

        if nip_kpa:
            kpa = Profile.objects.filter(nik=nip_kpa).first()
            if not kpa:
                raise serializers.ValidationError("User KPA doesn't exists")

        if nip_issuer:
            issuer = Profile.objects.filter(nik=nip_issuer).first()
            if issuer:
                issuer_data = Issuer.objects.create(
                    user=issuer.user,
                )
            else:
                raise serializers.ValidationError("User Issuer doesn't exists")
        
        doc = Document.objects.create(
            **validated_data,
            creator=user,
            employee=employee.user,
            issuer=issuer_data,
            current=1,
            total_allowance=total_allowance,
            file_issuer=doc_issuer
        )

        # action
        if action.lower() == "draft":
            doc.state = "sppd_draft"
        elif action.lower() == "submit":
            if is_operator == True:
                doc.state = "waiting_ppk"
            else:
                doc.state = "verification"
        else:
            raise serializers.ValidationError('Action is not valid')

        # travel purpose
        if travel_purpose_id:
            travel = TravelPurpose.objects.filter(id=travel_purpose_id, is_delete=False).first()
            if travel:
                doc.travel_purpose = travel
                doc.save()
            else:
                raise serializers.ValidationError('Travel Purpose Not Found')

        # transportation type
        if transportation_type_id:
            transport = Transportation.objects.filter(id=transportation_type_id, is_delete=False).first()
            if transport:
                doc.transportation_type = transport
                doc.save()
            else:
                raise serializers.ValidationError('Transportation Not Found')

        # cost category
        if cost_category_id:
            cost = SBMMaster.objects.filter(id=cost_category_id, is_delete=False).first()
            if cost:
                doc.cost_category = cost
                doc.save()
            else:
                raise serializers.ValidationError('Cost Category Not Found')

        # budget account
        if budget_account_id:
            budget_account = BudgetAccount.objects.filter(id=budget_account_id, is_delete=False).first()
            if budget_account:
                doc.budget_account = budget_account
                doc.save()
            else:
                raise serializers.ValidationError('Budget_account Not Found')

        TravelAssignment.objects.bulk_create([
            TravelAssignment(
                document=doc,
                **assignment,
            )
            for assignment in travel_assignments
        ])

        approver_list = []
        if request.user.active_role.active_role == 'operator':
            # Operator -> PPK -> KPA -> Employee
            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "sppd",
                "flag": "Membuat Dokumen SPPD"
            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "sppd",
                    "flag": "Verifikasi PPK"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "sppd",
                "flag": "Verifikasi KPA"
            })

            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "sppd",
                "flag": "Melaksanakan SPPD & Membuat SPJ"
            })

            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"
            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "spj",
                    "flag": "Pengesahan SPJ"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"
            })
            
            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "spj",
                "flag": "SPPD Selesai"
            })

        elif request.user.active_role.active_role == 'employee':
            # Employee -> Operator -> PPK -> KPA -> Employee
            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "sppd",
                "flag": "Membuat Dokumen SPPD"
            })

            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "sppd",
                "flag": "Verifikasi"
            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "sppd",
                    "flag": "Verifikasi PPK"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "sppd",
                "flag": "Verifikasi KPA"
            })

            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "sppd",
                "flag": "Melaksanakan SPPD & Membuat SPJ"
            })

            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"

            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "spj",
                    "flag": "Pengesahan SPJ"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"
            })

            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "spj",
                "flag": "SPPD Selesai"
            })
        else:
            raise serializers.ValidationError("You can't create SPPD Document")

        # Create approvers with sequence
        approvers = []
        for sequence, item in enumerate(approver_list, start=0):
            user = item["user"]

            if not user:
                continue

            approver_data = get_approver_data(doc, user)

            approvers.append(
                Approver(
                    **approver_data,
                    role=item["role"],
                    type=item["type"],
                    flag=item["flag"],
                    sequence=sequence,
                )
            )

        Approver.objects.bulk_create(approvers)

        # readers
        readers = [item["user"] for item in approver_list if item["user"]]
        doc.readers.set(readers)

        # authors
        doc.authors = doc.get_current_approver.user

        if doc.submission_type == 'dp':
            doc.dp = dp
            doc.save()

        create_log(user, 'create', 'SPPD', doc)
        return doc

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user
        nip = validated_data.pop("nip", None)
        nip_operator = validated_data.pop("nip_operator", None)
        nip_ppk = validated_data.pop("nip_ppk", None)
        nip_kpa = validated_data.pop("nip_kpa", None)
        travel_assignments = validated_data.pop("travel_assignment", [])
        total_allowance = validated_data.pop("total_allowance", None)
        travel_purpose_id = validated_data.pop("travel_purpose_id", None)
        transportation_type_id = validated_data.pop("transportation_type_id", None)
        budget_account_id = validated_data.pop("budget_account_id", None)
        cost_category_id = validated_data.pop("cost_category_id", None)
        action = validated_data.pop("action", None)
        is_operator = validated_data.pop("is_operator", None)
        nip_issuer = validated_data.pop("nip_issuer", None)
        dp = validated_data.pop("dp", None)
        doc_issuer = validated_data.pop("doc_issuer", None)

        employee = None
        operator = None
        ppk = []
        kpa = None
        issuer = None
        issuer_data = None

        if nip:
            employee = Profile.objects.filter(nik=nip).first()
            if not employee:
                raise serializers.ValidationError("Employee doesn't exists")

        if nip_operator:
            operator = Profile.objects.filter(nik=nip_operator).first()
            if not operator:
                raise serializers.ValidationError("Operator doesn't exists")

        if nip_ppk:
            ppk = Profile.objects.filter(nik__in=nip_ppk)
            if not ppk.exists():
                raise serializers.ValidationError("PPK doesn't exists")

        if nip_kpa:
            kpa = Profile.objects.filter(nik=nip_kpa).first()
            if not kpa:
                raise serializers.ValidationError("User KPA doesn't exists")

        if nip_issuer:
            issuer = Profile.objects.filter(nik=nip_issuer).first()
            if issuer:
                issuer_data = Issuer.objects.create(
                    user=issuer.user,
                )
            else:
                raise serializers.ValidationError("User Issuer doesn't exists")

        # Update document fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update travel purpose
        if travel_purpose_id:
            travel = TravelPurpose.objects.filter(id=travel_purpose_id, is_delete=False).first()
            if travel:
                instance.travel_purpose = travel
            else:
                raise serializers.ValidationError('Travel Purpose Not Found')

        # Update transportation type
        if transportation_type_id:
            transport = Transportation.objects.filter(id=transportation_type_id, is_delete=False).first()
            if transport:
                instance.transportation_type = transport
            else:
                raise serializers.ValidationError('Transportation Not Found')

        # Update cost category
        if cost_category_id:
            cost = SBMMaster.objects.filter(id=cost_category_id, is_delete=False).first()
            if cost:
                instance.cost_category = cost
            else:
                raise serializers.ValidationError('Cost Category Not Found')

        # Update budget account
        if budget_account_id:
            budget_account = BudgetAccount.objects.filter(id=budget_account_id, is_delete=False).first()
            if budget_account:
                instance.budget_account = budget_account
            else:
                raise serializers.ValidationError('Budget_account Not Found')

        # Update travel assignments
        TravelAssignment.objects.filter(document=instance, is_delete=False).update(is_delete=True, document=None)
        TravelAssignment.objects.bulk_create([
            TravelAssignment(
                document=instance,
                **assignment,
            )
            for assignment in travel_assignments
        ])

        # Update approvers
        approver_list = []
        if request.user.active_role.active_role == 'operator':
            # Operator -> PPK -> KPA -> Employee
            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "sppd",
                "flag": "Membuat Dokumen SPPD"
            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "sppd",
                    "flag": "Verifikasi PPK"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "sppd",
                "flag": "Verifikasi KPA"
            })

            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "sppd",
                "flag": "Melaksanakan SPPD & Membuat SPJ"
            })

            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"
            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "spj",
                    "flag": "Pengesahan SPJ"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"
            })
            
            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "spj",
                "flag": "SPPD Selesai"
            })

        elif request.user.active_role.active_role == 'employee':
            # Employee -> Operator -> PPK -> KPA -> Employee
            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "sppd",
                "flag": "Membuat Dokumen SPPD"
            })

            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "sppd",
                "flag": "Verifikasi"
            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "sppd",
                    "flag": "Verifikasi PPK"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "sppd",
                "flag": "Verifikasi KPA"
            })

            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "sppd",
                "flag": "Melaksanakan SPPD & Membuat SPJ"
            })

            approver_list.append({
                "role": "operator",
                "user": operator.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"

            })

            for ppk_user in ppk:
                approver_list.append({
                    "role": "ppk",
                    "user": ppk_user.user,
                    "type": "spj",
                    "flag": "Pengesahan SPJ"
                })

            approver_list.append({
                "role": "kpa",
                "user": kpa.user,
                "type": "spj",
                "flag": "Verifikasi SPJ"
            })

            approver_list.append({
                "role": "employee",
                "user": employee.user,
                "type": "spj",
                "flag": "SPPD Selesai"
            })
        else:
            raise serializers.ValidationError("You can't update SPPD Document")
        
        # Delete existing approvers
        Approver.objects.filter(document=instance, is_delete=False).update(is_delete=True, document=None)

        # Create new approvers with sequence
        approvers = []
        for sequence, item in enumerate(approver_list, start=0):
            approver_user = item["user"]

            if not approver_user:
                continue

            approver_data = get_approver_data(instance, approver_user)

            approvers.append(
                Approver(
                    **approver_data,
                    role=item["role"],
                    type=item["type"],
                    flag=item["flag"],
                    sequence=sequence,
                )
            )

        Approver.objects.bulk_create(approvers)

        # readers
        readers = [item["user"] for item in approver_list if item["user"]]
        instance.readers.set(readers)

        # authors
        instance.authors = instance.get_current_approver.user

        # action
        if action.lower() == "draft":
            instance.state = "sppd_draft"
        elif action.lower() == "submit":
            if is_operator == True:
                instance.state = "waiting_ppk"
            else:
                instance.state = "verification"
        else:
            raise serializers.ValidationError('Action is not valid')

        # Update dp
        if instance.submission_type == 'dp':
            instance.dp = dp

        instance.save()

        return instance

    def get_approvers(self, instance):
        approvers = instance.get_approvers_list()
        data = ApproverSerializer(approvers, many=True).data
        return data

    def get_authors(self, instance):
        return instance.authors.username
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        data_travel = []
        travels = TravelAssignment.objects.filter(document=instance, is_delete=False)
        for t in travels:
            data_travel.append({
                "origin_city": t.origin_city if t.origin_city else None,
                "destination_city": t.destination_city if t.destination_city else None,
                "duration_days": t.duration_days if t.duration_days else None,
                "persons": t.persons if t.persons else None,
                "daily_allowance": t.daily_allowance if t.daily_allowance else None,
                "accommodation_allowance": t.accommodation_allowance if t.accommodation_allowance else None,
                "lodging_allowance": t.lodging_allowance if t.lodging_allowance else None,
                "sub_total_allowance": t.sub_total_allowance if t.sub_total_allowance else None,
            })

        data["travel_assignment"] = data_travel
        data["travel_purpose"] = instance.travel_purpose.name if instance.travel_purpose else None
        data["transportation_type"] = instance.transportation_type.name if instance.transportation_type else None
        data["cost_category"] = f"{instance.cost_category.grade} - {instance.cost_category.description}" if instance.cost_category else None
        data["submission_type"] = instance.get_submission_type_display()
        return data

class SPPDEstimateCostListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        return [
            estimate_cost(item)
            for item in validated_data
        ]

class SPPDEstimateCostSerializer(serializers.Serializer):
    cost_category = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    origin_city = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    destination_province = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    duration_days = serializers.IntegerField(required=False)
    persons = serializers.IntegerField(write_only=True)

    daily_allowance = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    lodging = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    transport = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    representation = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    sub_total = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)

    class Meta:
        list_serializer_class = SPPDEstimateCostListSerializer

class SPPDUploadSPJ(serializers.ModelSerializer):
    doc_id = serializers.CharField(required=True, allow_blank=True, allow_null=True)
    departure_date = serializers.DateField(format="%d-%m-%Y", input_formats=["%d-%m-%Y"])
    return_date = serializers.DateField(format="%d-%m-%Y", input_formats=["%d-%m-%Y"])
    summary_activity = serializers.CharField(required=True, allow_blank=True, allow_null=True)
    recommendation = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    report_activity = serializers.FileField(required=True)
    sppd_signed = serializers.FileField(required=True)
    ticket_and_boarding_pass = serializers.FileField(required=True)
    accommodation_invoice = serializers.FileField(required=True)
    evidence_local_transport = serializers.FileField(required=False)
    documentation_activity = serializers.FileField(required=False)
    daily_allowance = serializers.DecimalField(max_digits=14, decimal_places=0)
    accommodation_allowance = serializers.DecimalField(max_digits=14, decimal_places=0)
    lodging_allowance = serializers.DecimalField(max_digits=14, decimal_places=0)
    local_lodging = serializers.DecimalField(max_digits=14, decimal_places=0, default=0)
    action = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = SPJ
        fields = [
            "doc_id",
            "departure_date",
            "return_date",
            "summary_activity",
            "recommendation",
            "report_activity",
            "sppd_signed",
            "ticket_and_boarding_pass",
            "accommodation_invoice",
            "evidence_local_transport",
            "documentation_activity",
            "daily_allowance",
            "accommodation_allowance",
            "lodging_allowance",
            "local_lodging",
            "action"
        ]

    @transaction.atomic
    def create(self, validated_data):
        doc_id = validated_data.pop("doc_id", None)
        action = validated_data.pop("action", None)
        daily_allowance = validated_data.pop("daily_allowance", None)
        accommodation_allowance = validated_data.pop("accommodation_allowance", None)
        lodging_allowance = validated_data.pop("lodging_allowance", None)
        local_lodging = validated_data.pop("local_lodging", None)

        request = self.context.get("request")
        
        total = daily_allowance + accommodation_allowance + lodging_allowance + local_lodging

        if doc_id:
            doc = Document.objects.filter(id=doc_id).first()
            
            if doc:
                spj = SPJ.objects.create(
                    document=doc,
                    total_allowance=total,
                    daily_allowance=daily_allowance,
                    accommodation_allowance=accommodation_allowance,
                    lodging_allowance=lodging_allowance,
                    local_lodging=local_lodging,
                    **validated_data
                )

            if action.lower() == "draft":
                doc.state = "draft_spj"
            elif action.lower() == "submit":
                doc.current += 1
                doc.authors = doc.get_current_approver.user
                doc.set_document_state()
            else:
                raise serializers.ValidationError("Action is not valid")

            doc.save()

            data = get_budget_comparison(spj)

            total = data.get("total")
            comparison_type = data.get("type")

            if comparison_type == "kurang_bayar":
                spj.underpayment = total
            elif comparison_type == "lebih_bayar":
                spj.overpayment = abs(total)
            else:
                raise serializers.ValidationError("Type comparison is not valid")

            spj.save()
            create_log(request.user, 'Create', 'SPJ', spj)
        return spj

    @transaction.atomic
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class SPPDDashboardSerializer(serializers.ModelSerializer):
    latest_activities = serializers.SerializerMethodField()
    status_distribution = serializers.SerializerMethodField()
    popular_destinations = serializers.SerializerMethodField()
    budget_realization = serializers.SerializerMethodField()
    badge = serializers.SerializerMethodField()
    class Meta:
        model = Document
        fields = [
            "latest_activities",
            "status_distribution",
            "popular_destinations",
            "budget_realization",
            "badge"
        ]

    def get_latest_activities(self, obj):
        data = []
        doc = Document.objects.filter(is_delete=False).order_by('-created_at')[:4]
        for d in doc:
            travel_assignments = d.travel_assignment.all()

            destination = [
                t.destination_city for t in travel_assignments
            ]

            data.append({
                "id": d.id,
                "assignment_basis": d.assignment_basis,
                "destination_city": destination,
                "departure_date": d.departure_date,
                "travel_purpose": d.travel_purpose.name,
                "state": d.state
            })

        return data

    def get_status_distribution(self, obj):
        return {
            "total_document": obj.total_document,
            "complete": obj.complete,
            "approved": obj.approved,
            "waiting_ppk": obj.waiting_ppk,
            "verification": obj.verification,
            "rejected": obj.rejected
        }

    def get_popular_destinations(self, obj):
        popular_destination = (
            Document.objects
            .filter(is_delete=False)
            .filter(
                travel_assignment__destination_city__isnull=False
            )
            .exclude(travel_assignment__destination_city='')
            .values('travel_assignment__destination_city')
            .annotate(
                total=Count('travel_assignment__id', distinct=True)
            )
            .order_by('-total')[:5]
        )

        data = []

        for p in popular_destination:
            data.append({
                "name": p["travel_assignment__destination_city"],
                "total": p["total"]
            })

        return data

    def get_budget_realization(self, obj):
        total_pagu = 0
        pagu = PaguSPPD.objects.filter(is_delete=False)
        for p in pagu:
            total_pagu += p.pagu

        total_allowance = obj.total_allowance_all or 0

        percentage = (
            (total_allowance / total_pagu) * 100
            if total_pagu > 0 else 0
        )

        return {
            "pagu" : total_pagu,
            "budget_spent" : total_allowance,
            "budget_spent_persen": percentage,
            "remaining_budget" : total_pagu - total_allowance
        }

    def get_badge(self, obj):
        return {
            "total_document": obj.total_document,
            "need_approval": obj.need_approval,
            "approved": obj.approved,
            "province": Province.objects.filter(is_delete=False).count(),
            "realization": obj.total_allowance_all or 0
        }

class SPJDetail(serializers.ModelSerializer):
    class Meta:
        model = SPJ
        fields = "__all__"

class AddressbookListSerializer(serializers.Serializer):
    data_aam = serializers.SerializerMethodField()

    def get_data_aam(self, obj):
        request = self.context.get("request")
        data = get_data_profile_batch([obj.username], request)
        return data[0] if data else None
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from django.conf import settings
from sppd.models import Document, SBMMaster, DailyAllowanceRate
from django.urls import reverse

def estimate_cost(data):
    cost_category = data.get("cost_category")
    origin_city = data.get("origin_city")
    destination_city = data.get("destination_city")
    destination_province = data.get("destination_province")
    duration_days = data.get("duration_days", 0)
    persons = data.get("persons", 0)

    daily = daily_estimate_cost(
        destination_province,
        duration_days,
        persons
    ) or 0

    transport = 2500000

    lodging = lodging_estimate_cost(
        cost_category,
        duration_days,
        persons
    )

    lodging_cost = lodging.get("cost") or 0
    representation = lodging.get("representation") or 0

    sub_total = daily + transport + lodging_cost + representation

    return {
        "origin_city": origin_city,
        "duration_days": duration_days,
        "daily_allowance": daily,
        "lodging": lodging_cost,
        "transport": transport,
        "representation": representation,
        "sub_total": sub_total
    }

def daily_estimate_cost(destination_province, days, persons):
    if destination_province:
        daily_allowance = DailyAllowanceRate.objects.filter(
            province__id=destination_province
        ).first()

        if daily_allowance:
            # return daily_allowance.amount * int(days) * int(persons)
            return daily_allowance.amount

    return 0

def lodging_estimate_cost(cost_category, days, persons):
    if cost_category:
        data = SBMMaster.objects.filter(grade=cost_category).first()

        if data:
            # cost = data.lodging_limit * (int(days) - 1) * int(persons)
            cost = data.lodging_limit

            if data.grade == "A":
                representation = (
                    data.representation_allowance
                )
            else:
                representation = 0

            return {
                "cost": cost,
                "representation": representation
            }

    return {
        "cost": 0,
        "representation": 0
    }

def validate_current_approver(doc_id, request, action=None):
    document = Document.objects.get(id=doc_id)
    approvers = document.get_approvers_list()
    if document.creator != request.user and action != "cancel":
        user = request.user
        if user.active_role.active_role != document.get_current_approver.role:
            raise ValidationError({"error": "Your role is not allowed to do this action"})
        current = document.current or 0
        if current >= len(approvers):
            raise ValidationError({"error": "No approver left for this document."})

        if document.authors != request.user:
            raise PermissionDenied({"error": "You are not the current approver."})
    return approvers

def get_budget_comparison(data):
    doc = data.document
    budget = doc.total_allowance
    realization = data.total_allowance
    submission_type = doc.submission_type

    total_paid = None
    if submission_type == "dp":
        dp = doc.dp
        total_paid = (budget * dp) / 100
    elif submission_type == "lumpsum":
        total_paid = budget
    elif submission_type == "reimburse":
        total_paid = 0
    else:
        raise ValidationError(f"Submission SPJ with id : {data.id} is not valid")

    total = realization - total_paid

    type = "kurang_bayar" if total > 0 else "lebih_bayar"
    return {
        "total": total,
        "type": type
    }

def get_role(user):
    groups = user.groups.all()
    data = []
    for g in groups:
        if 'sppd_operator' in g.name:
            data.append('operator')
        elif 'sppd_ppk' in g.name:
            data.append('ppk')
        elif 'sppd_kpa' in g.name:
            data.append('kpa')
    data.append('employee')
    return data

def get_approver_data(doc, user):
    return {
        "document": doc,
        "user": user if user else None,
    }
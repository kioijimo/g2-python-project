import csv
from dataclasses import dataclass
from datetime import datetime

from dateutil import relativedelta
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve
from django.urls.exceptions import Http404
from django.utils import timezone
from django.views.decorators.http import require_POST

from app.services.audit import record_audit

from .. import forms
from ..decorators import admin_required
from ..models import (
    AuditLog,
    BorrowRequest,
    CatalogItem,
    Category,
    EquipmentUnit,
    LoanRecord,
    MaintenanceRecord,
    Profile,
    RequestItem,
    ReturnRecord,
    SystemSetting,
    UnitAllocation,
    User,
)
from ..services.approvals import (
    approve_borrow_request,
    reject_borrow_request,
    release_borrow_request,
)

PAGE_ITEMS = 5


def _table_paginate(request, queryset):
    page_obj = Paginator(queryset, PAGE_ITEMS).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page_obj, params.urlencode()


def _get_borrow_request(pk):
    return get_object_or_404(
        BorrowRequest.objects.select_related("user").prefetch_related(
            "review_records__user",
            "items__catalog_item__category",
            "items__allocations__equipment_unit",
            "returnrecord_set__equipment_unit",
        ),
        pk=pk,
    )


def _structure_allocations_from_post(request, items):
    allocations_by_item = {}

    for request_item in items:
        unit_ids = (
            request.POST.getlist(f"units_{request_item.pk}")
            or request.POST.getlist(f"unit_{request_item.pk}")
            or request.POST.getlist(f"allocation_{request_item.pk}")
        )
        allocations_by_item[request_item.pk] = unit_ids

    if len(items) == 1 and not allocations_by_item[items[0].pk]:
        allocations_by_item[items[0].pk] = request.POST.getlist(
            "units"
        ) or request.POST.getlist("unit_ids")

    return allocations_by_item


@admin_required
def returns_manage_view(request):
    # Active loans eligible for returns (ISSUED or PARTIALLY_RETURNED)
    active_requests = list(
        BorrowRequest.objects.filter(
            status__in=[
                BorrowRequest.BorrowRequestStatus.ISSUED,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
            ]
        )
        .select_related("user", "user__profile")
        .prefetch_related(
            "items__catalog_item__category",
            "items__allocations__equipment_unit",
            "returnrecord_set__equipment_unit",
        )
        .order_by("-created_at")
    )

    today = timezone.localdate()
    for req in active_requests:
        returns_by_unit_id = {
            ret.equipment_unit_id: ret for ret in req.returnrecord_set.all()
        }
        allocated_units = []
        returned_cnt = 0
        remaining_cnt = 0
        for item in req.items.all():
            for alloc in item.allocations.all():
                if alloc.status == UnitAllocation.UnitAllocationStatus.RELEASED:
                    unit = alloc.equipment_unit
                    return_rec = returns_by_unit_id.get(unit.id)
                    is_ret = return_rec is not None
                    if is_ret:
                        returned_cnt += 1
                    else:
                        remaining_cnt += 1
                    allocated_units.append(
                        {
                            "id": unit.id,
                            "asset_code": unit.asset_code,
                            "catalog_item": item.catalog_item.name,
                            "category": item.catalog_item.category.name,
                            "is_returned": is_ret,
                            "return_condition": (
                                return_rec.condition if return_rec else None
                            ),
                        }
                    )
        req.allocated_units = allocated_units
        req.total_units_count = len(allocated_units)
        req.returned_units_count = returned_cnt
        req.remaining_units_count = remaining_cnt
        req.overdue_days_count = req.overdue_days(today)
        req.is_overdue = req.overdue_days_count > 0

    selected_request_id = request.GET.get("request_id", "").strip()
    active_ids = {str(req.id) for req in active_requests}
    if selected_request_id not in active_ids:
        selected_request_id = ""

    # Recent return audit records
    recent_returns_qs = ReturnRecord.objects.select_related(
        "borrow_request", "equipment_unit"
    ).order_by("-created_at")
    recent_returns, querystring = _table_paginate(request, recent_returns_qs)

    context = {
        "active_requests": active_requests,
        "selected_request_id": selected_request_id,
        "recent_returns": recent_returns,
        "page_obj": recent_returns,
        "queryset": recent_returns,
        "querystring": querystring,
        "EquipmentCondition": EquipmentUnit.EquipmentCondition,
    }
    return render(request, "manage/returns.html", context)


@admin_required
@transaction.atomic
def process_unit_return(request):
    if request.method == "POST":
        borrow_request_id = request.POST.get("borrow_request_id")
        borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)

        default_condition = int(
            request.POST.get("condition", EquipmentUnit.EquipmentCondition.FINE)
        )
        return_mode = request.POST.get("return_mode", "").strip()

        # Fetch all RELEASED allocations for this borrow request
        released_allocations = list(
            UnitAllocation.objects.filter(
                request_item__borrow_request=borrow_request,
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
            ).select_related("equipment_unit")
        )
        allocated_by_code = {
            alloc.equipment_unit.asset_code.upper(): alloc.equipment_unit
            for alloc in released_allocations
        }
        already_returned_ids = set(
            ReturnRecord.objects.filter(borrow_request=borrow_request).values_list(
                "equipment_unit_id", flat=True
            )
        )

        # Determine target asset codes from return_mode, checkboxes, or text input
        raw_codes = []
        if return_mode == "all":
            raw_codes = [
                alloc.equipment_unit.asset_code
                for alloc in released_allocations
                if alloc.equipment_unit_id not in already_returned_ids
            ]
        elif return_mode.startswith("single:"):
            single_code = return_mode.split(":", 1)[1].strip()
            if single_code:
                raw_codes = [single_code]
        else:
            checked_codes = [
                c.strip() for c in request.POST.getlist("asset_codes") if c.strip()
            ]
            if checked_codes:
                raw_codes = checked_codes
            else:
                asset_code_input = request.POST.get("asset_code", "").strip()
                if asset_code_input.upper() == "ALL":
                    raw_codes = [
                        alloc.equipment_unit.asset_code
                        for alloc in released_allocations
                        if alloc.equipment_unit_id not in already_returned_ids
                    ]
                elif asset_code_input:
                    raw_codes = [
                        c.strip()
                        for c in asset_code_input.replace(";", ",").split(",")
                        if c.strip()
                    ]

        # Deduplicate while preserving order
        seen_upper = set()
        target_codes = []
        for code in raw_codes:
            upper = code.upper()
            if upper not in seen_upper:
                seen_upper.add(upper)
                target_codes.append(code)

        if not target_codes:
            messages.error(
                request,
                "Please select or enter at least one unit to return.",
            )
            return redirect(f"/manage/returns/?request_id={borrow_request.id}")

        # Validate all target codes belong to this borrow request
        units_to_process = []
        for code in target_codes:
            unit = allocated_by_code.get(code.upper())
            if unit is None:
                # Check if the asset code exists at all in EquipmentUnit
                if not EquipmentUnit.objects.filter(asset_code__iexact=code).exists():
                    messages.error(
                        request,
                        f"Asset unit '{code}' does not exist or was not issued under Request #{borrow_request.id}.",
                    )
                else:
                    messages.error(
                        request,
                        f"Asset unit '{code}' was not issued under Request #{borrow_request.id}.",
                    )
                return redirect(f"/manage/returns/?request_id={borrow_request.id}")

            if unit.id in already_returned_ids:
                if len(target_codes) == 1:
                    messages.warning(
                        request,
                        f"Unit '{unit.asset_code}' has already been returned for Request #{borrow_request.id}.",
                    )
                    return redirect(f"/manage/returns/?request_id={borrow_request.id}")
                continue

            units_to_process.append(unit)

        if not units_to_process:
            messages.warning(
                request,
                f"All selected units have already been returned for Request #{borrow_request.id}.",
            )
            return redirect(f"/manage/returns/?request_id={borrow_request.id}")

        fine_codes = []
        damaged_codes = []

        for unit in units_to_process:
            cond_raw = request.POST.get(
                f"condition_{unit.asset_code}",
                request.POST.get(f"condition_{unit.id}", default_condition),
            )
            condition_val = int(cond_raw)

            # Create Return Record
            ReturnRecord.objects.create(
                borrow_request=borrow_request,
                equipment_unit=unit,
                condition=condition_val,
            )

            # Route Unit Inventory Status based on condition
            unit.condition = condition_val
            if condition_val == EquipmentUnit.EquipmentCondition.FINE:
                unit.inventory_status = EquipmentUnit.EquipmentStatus.AVAILABLE
                unit.save()
                fine_codes.append(unit.asset_code)
            else:
                # DAMAGED -> Route directly to MAINTENANCE
                unit.inventory_status = EquipmentUnit.EquipmentStatus.MAINTENANCE
                unit.save()
                MaintenanceRecord.objects.create(
                    maintainer=request.user,
                    unit=unit,
                    issue=f"Returned DAMAGED from BorrowRequest #{borrow_request.id}.",
                    action="Pending inspection and repair.",
                    status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
                    resolved_at=timezone.now(),
                )
                damaged_codes.append(unit.asset_code)

            AuditLog.objects.create(
                user=request.user,
                action=f"Processed return of unit '{unit.asset_code}' for BorrowRequest #{borrow_request.id}.",
            )

        if len(fine_codes) == 1:
            messages.success(
                request,
                f"Unit {fine_codes[0]} returned in FINE condition and restored to AVAILABLE stock.",
            )
        elif len(fine_codes) > 1:
            messages.success(
                request,
                f"{len(fine_codes)} units ({', '.join(fine_codes)}) returned in FINE condition and restored to AVAILABLE stock.",
            )

        if len(damaged_codes) == 1:
            messages.warning(
                request,
                f"Unit {damaged_codes[0]} returned DAMAGED and placed into MAINTENANCE.",
            )
        elif len(damaged_codes) > 1:
            messages.warning(
                request,
                f"{len(damaged_codes)} units ({', '.join(damaged_codes)}) returned DAMAGED and placed into MAINTENANCE.",
            )

        # Evaluate overall BorrowRequest status (Partial vs Fully Returned)
        total_allocated = len(released_allocations)
        total_returned = ReturnRecord.objects.filter(
            borrow_request=borrow_request
        ).count()

        if total_returned >= total_allocated:
            borrow_request.status = BorrowRequest.BorrowRequestStatus.RETURNED
            borrow_request.save()
            return redirect("manage_returns")
        else:
            borrow_request.status = BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED
            borrow_request.save()
            return redirect(f"/manage/returns/?request_id={borrow_request.id}")

    return redirect("manage_returns")


@admin_required
def maintenance_manage_view(request):
    tickets = MaintenanceRecord.objects.select_related(
        "unit", "unit__catalog_item", "maintainer"
    ).order_by("-created_at")
    tickets, querystring = _table_paginate(request, tickets)

    # Inventory Reconciliation Totals
    total_units = EquipmentUnit.objects.count()
    available_cnt = EquipmentUnit.objects.filter(
        inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE
    ).count()
    reserved_cnt = EquipmentUnit.objects.filter(
        inventory_status=EquipmentUnit.EquipmentStatus.RESERVED
    ).count()
    issued_cnt = EquipmentUnit.objects.filter(
        inventory_status=EquipmentUnit.EquipmentStatus.ISSUED
    ).count()
    maintenance_cnt = EquipmentUnit.objects.filter(
        inventory_status=EquipmentUnit.EquipmentStatus.MAINTENANCE
    ).count()
    retired_cnt = EquipmentUnit.objects.filter(
        inventory_status=EquipmentUnit.EquipmentStatus.RETIRED
    ).count()

    # Units eligible to enter maintenance (cannot be ISSUED or RESERVED)
    eligible_units = EquipmentUnit.objects.filter(
        inventory_status__in=[
            EquipmentUnit.EquipmentStatus.AVAILABLE,
        ]
    )

    context = {
        "tickets": tickets,
        "page_obj": tickets,
        "queryset": tickets,
        "querystring": querystring,
        "eligible_units": eligible_units,
        "MaintenanceStatus": MaintenanceRecord.MaintenanceStatus,
        "audit": {
            "total": total_units,
            "available": available_cnt,
            "reserved": reserved_cnt,
            "issued": issued_cnt,
            "maintenance": maintenance_cnt,
            "retired": retired_cnt,
        },
    }
    return render(request, "manage/maintenance.html", context)


@admin_required
@transaction.atomic
def open_maintenance_ticket(request):
    if request.method == "POST":
        unit_id = request.POST.get("unit_id")
        issue = request.POST.get("issue", "").strip()

        unit = get_object_or_404(EquipmentUnit, id=unit_id)

        # Reject maintenance for currently ISSUED or RESERVED units
        if unit.inventory_status in [
            EquipmentUnit.EquipmentStatus.ISSUED,
            EquipmentUnit.EquipmentStatus.RESERVED,
        ]:
            messages.error(
                request,
                f"Cannot place unit '{unit.asset_code}' into maintenance because its status is currently {unit.get_inventory_status_display()}.",
            )
            return redirect("manage_maintenance")

        # Update unit status
        unit.inventory_status = EquipmentUnit.EquipmentStatus.MAINTENANCE
        unit.condition = EquipmentUnit.EquipmentCondition.DAMAGED
        unit.save()

        # Create record
        MaintenanceRecord.objects.create(
            maintainer=request.user,
            unit=unit,
            issue=issue,
            action="Work order initialized.",
            status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
            resolved_at=timezone.now(),
        )

        AuditLog.objects.create(
            user=request.user,
            action=f"Opened maintenance record for unit '{unit.asset_code}'.",
        )
        messages.success(
            request, f"Maintenance work order opened for unit '{unit.asset_code}'."
        )

    return redirect("manage_maintenance")


@admin_required
@transaction.atomic
def resolve_maintenance_ticket(request, ticket_id):
    if request.method == "POST":
        ticket = get_object_or_404(MaintenanceRecord, id=ticket_id)
        action_description = request.POST.get("action", "").strip()
        outcome = request.POST.get("outcome")  # 'REPAIR' or 'RETIRE'

        ticket.action = action_description
        ticket.status = MaintenanceRecord.MaintenanceStatus.FINISHED
        ticket.resolved_at = timezone.now()
        ticket.save()

        unit = ticket.unit
        if outcome == "REPAIR":
            unit.inventory_status = EquipmentUnit.EquipmentStatus.AVAILABLE
            unit.condition = EquipmentUnit.EquipmentCondition.FINE
            unit.save()
            messages.success(
                request,
                f"Unit '{unit.asset_code}' successfully repaired and restored to AVAILABLE stock.",
            )
            action_log = f"Resolved maintenance for '{unit.asset_code}' (Repaired)."
        else:
            unit.inventory_status = EquipmentUnit.EquipmentStatus.RETIRED
            unit.save()
            messages.warning(request, f"Unit '{unit.asset_code}' marked as RETIRED.")
            action_log = f"Resolved maintenance for '{unit.asset_code}' (Retired)."

        AuditLog.objects.create(user=request.user, action=action_log)

    return redirect("manage_maintenance")


def _export_loans_csv(queryset):
    response = HttpResponse(content_type="text/csv")
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = (
        f'attachment; filename="loan_report_{timestamp}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Loan ID",
            "Borrower Name",
            "Borrower Email",
            "Items Requested",
            "Allocated Asset Codes",
            "Status",
            "Requested At",
            "Released At",
            "Due Date",
        ]
    )
    for loan in queryset:
        borrower_name = (
            getattr(loan.user, "display_name", None)
            or loan.user.get_full_name()
            or loan.user.username
        )
        items_desc = "; ".join(
            f"{item.catalog_item.name} (x{item.quantity})" for item in loan.items.all()
        )
        asset_codes = []
        for item in loan.items.all():
            for alloc in item.allocations.all():
                asset_codes.append(alloc.equipment_unit.asset_code)
        asset_codes_str = ", ".join(asset_codes) if asset_codes else "None"
        released_record = loan.review_records.filter(released_at__isnull=False).first()
        released_str = (
            timezone.localtime(released_record.released_at).strftime("%Y-%m-%d %H:%M")
            if released_record and released_record.released_at
            else "N/A"
        )
        created_str = timezone.localtime(loan.created_at).strftime("%Y-%m-%d %H:%M")
        due_str = timezone.localtime(loan.due_at).strftime("%Y-%m-%d")

        writer.writerow(
            [
                f"#{loan.pk}",
                borrower_name,
                loan.user.email,
                items_desc,
                asset_codes_str,
                loan.get_status_display(),
                created_str,
                released_str,
                due_str,
            ]
        )
    return response


def _export_overdue_csv(queryset):
    response = HttpResponse(content_type="text/csv")
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = (
        f'attachment; filename="overdue_report_{timestamp}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Loan ID",
            "Borrower Name",
            "Borrower Email",
            "Contact Number",
            "Items Requested",
            "Allocated Asset Codes",
            "Due Date",
            "Days Overdue",
            "Status",
        ]
    )
    today = timezone.localdate()
    for loan in queryset:
        profile = getattr(loan.user, "profile", None)
        borrower_name = (
            getattr(loan.user, "display_name", None)
            or loan.user.get_full_name()
            or loan.user.username
        )
        contact = getattr(profile, "contact_number", "") or "N/A"
        items_desc = "; ".join(
            f"{item.catalog_item.name} (x{item.quantity})" for item in loan.items.all()
        )
        asset_codes = []
        for item in loan.items.all():
            for alloc in item.allocations.all():
                asset_codes.append(alloc.equipment_unit.asset_code)
        asset_codes_str = ", ".join(asset_codes) if asset_codes else "None"
        due_str = timezone.localtime(loan.due_at).strftime("%Y-%m-%d")
        days = loan.overdue_days(today)

        writer.writerow(
            [
                f"#{loan.pk}",
                borrower_name,
                loan.user.email,
                contact,
                items_desc,
                asset_codes_str,
                due_str,
                days,
                loan.get_status_display(),
            ]
        )
    return response


@admin_required
def manage(request):
    context = {}

    user_form = forms.UserForm(request.POST or None)
    profile_form = forms.ProfileForm(data=request.POST or None)

    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user = user_form.save()
        profile = profile_form.save(commit=False)
        profile.user = user
        profile.save()

        user_form = forms.UserForm()
        profile_form = forms.ProfileForm()
        messages.success(request, "Account created successfully.")

    context["forms"] = {"user": user_form, "profile": profile_form}

    # Hardcoded statistics for the 4 dashboard cards
    context["stats"] = {
        "available_units": EquipmentUnit.objects.filter(
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        ).count(),
        "pending_requests": BorrowRequest.objects.filter(
            status=BorrowRequest.BorrowRequestStatus.PENDING
        ).count(),
        "active_loans": BorrowRequest.objects.filter(
            Q(status=BorrowRequest.BorrowRequestStatus.ISSUED)
            | Q(status=BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED)
        ).count(),
        "overdue_loans": BorrowRequest.objects.filter(
            status__in=(
                BorrowRequest.BorrowRequestStatus.ISSUED,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
            ),
            due_at__lt=timezone.now(),
        ).count(),
    }

    context["monthly_trend"] = {
        "labels": [],
        "data": [],
    }

    prev = None
    for i, date in enumerate(
        [
            timezone.now() - relativedelta.relativedelta(months=x)
            for x in range(5, -1, -1)
        ]
    ):
        if i == 0:
            prev: datetime = date
            date = date.replace(day=1)

        context["monthly_trend"]["labels"].append(date.strftime("%b"))

        sum = 0

        print(f"Date is {date} while timezone is {timezone.now()}")

        for _ in BorrowRequest.objects.filter(
            created_at__range=(
                date,
                timezone.now() if i == 0 else prev,
            )
        ):
            sum = sum + 1

        context["monthly_trend"]["data"].insert(0, sum)

    categories = Category.objects.all()

    category_stats = []

    for c in categories:
        total = 0

        for i in CatalogItem.objects.filter(category=c.id):
            for o in RequestItem.objects.filter(catalog_item=i.id):
                total += o.quantity

        category_stats.append({"category": c.name, "usage": total})

    total_category_usage = 0
    for s in category_stats:
        total_category_usage += s["usage"]

    context["category_usage"] = {
        "labels": [s["category"] for s in category_stats],
        "data": [s["usage"] for s in category_stats],
        "counts": [s["usage"] for s in category_stats],
        "percentages": [
            round((s["usage"] / total_category_usage) * 100, 1)
            if total_category_usage > 0
            else 0
            for s in category_stats
        ],
    }

    context["settings"] = SystemSetting.objects.first()

    # Date-Filtered Loan and Overdue Reports logic
    loan_from = request.GET.get("loan_from", "").strip()
    loan_to = request.GET.get("loan_to", "").strip()
    loan_status = request.GET.get("loan_status", "all").strip()
    report_tab = request.GET.get("report_tab", "loans").strip()

    overdue_from = request.GET.get("overdue_from", "").strip()
    overdue_to = request.GET.get("overdue_to", "").strip()

    loans_report_qs = (
        BorrowRequest.objects.filter(
            status__in=[
                BorrowRequest.BorrowRequestStatus.ISSUED,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
                BorrowRequest.BorrowRequestStatus.RETURNED,
            ]
        )
        .select_related("user")
        .prefetch_related(
            "items__catalog_item",
            "items__allocations__equipment_unit",
            "review_records__user",
        )
        .order_by("-created_at")
    )
    if loan_from:
        loans_report_qs = loans_report_qs.filter(created_at__date__gte=loan_from)
    if loan_to:
        loans_report_qs = loans_report_qs.filter(created_at__date__lte=loan_to)
    if loan_status and loan_status != "all":
        try:
            loans_report_qs = loans_report_qs.filter(status=int(loan_status))
        except ValueError:
            pass

    now = timezone.now()
    overdue_report_qs = (
        BorrowRequest.objects.filter(
            status__in=[
                BorrowRequest.BorrowRequestStatus.ISSUED,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
            ],
            due_at__lt=now,
        )
        .select_related("user")
        .prefetch_related(
            "items__catalog_item",
            "items__allocations__equipment_unit",
        )
        .order_by("due_at")
    )
    if overdue_from:
        overdue_report_qs = overdue_report_qs.filter(due_at__date__gte=overdue_from)
    if overdue_to:
        overdue_report_qs = overdue_report_qs.filter(due_at__date__lte=overdue_to)

    export_action = request.GET.get("export")
    if export_action == "loans_csv":
        return _export_loans_csv(loans_report_qs)
    elif export_action == "overdue_csv":
        return _export_overdue_csv(overdue_report_qs)

    today = timezone.localdate()
    overdue_list = []
    for req in overdue_report_qs:
        overdue_list.append(
            {
                "request": req,
                "days_overdue": req.overdue_days(today),
            }
        )

    context["reports"] = {
        "active_tab": report_tab if report_tab in ("loans", "overdue") else "loans",
        "loans": loans_report_qs,
        "loans_count": loans_report_qs.count(),
        "overdue_list": overdue_list,
        "overdue_count": len(overdue_list),
        "filters": {
            "loan_from": loan_from,
            "loan_to": loan_to,
            "loan_status": loan_status,
            "overdue_from": overdue_from,
            "overdue_to": overdue_to,
        },
    }

    return render(request, "manage/home.html", context)


@admin_required
def loans_list(request):
    filter_type = request.GET.get("filter", "active")

    queryset = (
        BorrowRequest.objects.filter(
            status__in=[
                BorrowRequest.BorrowRequestStatus.ISSUED.value,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value,
                BorrowRequest.BorrowRequestStatus.RETURNED.value,
            ]
        )
        .select_related("user")
        .prefetch_related("items__catalog_item")
        .order_by("-created_at")
    )

    today = timezone.localdate()

    if filter_type == "overdue":
        loans = [req for req in queryset if req.overdue_days(today) > 0]
    elif filter_type == "returned":
        loans = queryset.filter(status=BorrowRequest.BorrowRequestStatus.RETURNED.value)
    else:
        loans = queryset.filter(
            status__in=[
                BorrowRequest.BorrowRequestStatus.ISSUED.value,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value,
            ]
        )

    loans, querystring = _table_paginate(request, loans)

    return render(
        request,
        "manage/loans.html",
        {
            "loans": loans,
            "page_obj": loans,
            "queryset": loans,
            "querystring": querystring,
            "filter_type": filter_type,
            "today": today,
        },
    )


@admin_required
def process_returns(request, request_id):
    borrow_request = get_object_or_404(
        BorrowRequest,
        id=request_id,
        status__in=[
            BorrowRequest.BorrowRequestStatus.ISSUED.value,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value,
        ],
    )

    allocations = UnitAllocation.objects.filter(
        request_item__borrow_request=borrow_request,
        status=UnitAllocation.UnitAllocationStatus.RELEASED.value,
    ).select_related("equipment_unit", "request_item__catalog_item")

    if request.method == "POST":
        allocated_ids_to_return = request.POST.getlist("allocations_to_return")

        if not allocated_ids_to_return:
            messages.error(request, "Select atleast one unit to return.")
            return redirect("process_returns", request_id=borrow_request.id)

        with transaction.atomic():
            for alloc in allocations:
                if str(alloc.id) in allocated_ids_to_return:
                    cond_val = int(
                        request.POST.get(
                            f"condition_{alloc.id}",
                            EquipmentUnit.EquipmentCondition.FINE.value,
                        )
                    )

                    ReturnRecord.objects.create(
                        borrow_request=borrow_request,
                        equipment_unit=alloc.equipment_unit,
                        condition=cond_val,
                    )

                    alloc.status = UnitAllocation.UnitAllocationStatus.CANCELLED.value
                    alloc.save()

                    unit = alloc.equipment_unit
                    unit.condition = cond_val

                    if cond_val == EquipmentUnit.EquipmentCondition.DAMAGED.value:
                        unit.inventory_status = (
                            EquipmentUnit.EquipmentStatus.MAINTENANCE.value
                        )
                        MaintenanceRecord.objects.create(
                            maintainer=request.user,
                            unit=unit,
                            issue=f"Damaged upon return from Request #{borrow_request.id}",
                            action="Awaiting inspection",
                            status=MaintenanceRecord.MaintenanceStatus.ACTIVE.value,
                            resolved_at=timezone.now(),
                        )
                    else:
                        unit.inventory_status = (
                            EquipmentUnit.EquipmentStatus.AVAILABLE.value
                        )

                    unit.save()
            remaining = UnitAllocation.objects.filter(
                request_item__borrow_request=borrow_request,
                status=UnitAllocation.UnitAllocationStatus.RELEASED.value,
            ).count()

            if remaining == 0:
                borrow_request.status = BorrowRequest.BorrowRequestStatus.RETURNED.value
            else:
                borrow_request.status = (
                    BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value
                )

            borrow_request.save()

            AuditLog.objects.create(
                user=request.user,
                action=f"Processed return for Request #{borrow_request.id} ({len(allocated_ids_to_return)} unit(s) returned)",
            )

            messages.success(request, "Successfully processed returns.")
            return redirect("loans_list")

    return render(
        request,
        "manage/process_return.html",
        {
            "borrow_request": borrow_request,
            "allocations": allocations,
            "conditions": EquipmentUnit.EquipmentCondition.choices,
        },
    )


@admin_required
def borrow_requests(request):
    filter_form = forms.BorrowRequestFilterForm(request.GET)
    queryset = (
        BorrowRequest.objects.select_related("user")
        .prefetch_related("review_records__user")
        .order_by("-created_at")
    )

    if filter_form.is_valid():
        query = filter_form.cleaned_data["q"].strip()
        status = filter_form.cleaned_data["status"]
        date_from = filter_form.cleaned_data["date_from"]
        date_to = filter_form.cleaned_data["date_to"]

        if query:
            filters = Q(user__email__icontains=query) | Q(purpose__icontains=query)
            if query.isdigit() and len(query) <= 18:
                filters |= Q(pk=int(query))
            queryset = queryset.filter(filters)
        if status is not None:
            queryset = queryset.filter(status=status)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

    queryset, querystring = _table_paginate(request, queryset)
    return render(
        request,
        "manage/borrow_requests.html",
        {
            "filter_form": filter_form,
            "queryset": queryset,
            "querystring": querystring,
        },
    )


@admin_required
def borrow_request_review(request, pk):
    borrow_request = _get_borrow_request(pk)
    returns_by_unit_id = {
        ret.equipment_unit_id: ret for ret in borrow_request.returnrecord_set.all()
    }
    show_return_status = borrow_request.status in (
        BorrowRequest.BorrowRequestStatus.ISSUED,
        BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
        BorrowRequest.BorrowRequestStatus.RETURNED,
    )
    item_rows = []

    for request_item in borrow_request.items.all():
        allocations = []
        for allocation in request_item.allocations.all():
            if allocation.status != UnitAllocation.UnitAllocationStatus.CANCELLED:
                return_rec = returns_by_unit_id.get(allocation.equipment_unit_id)
                allocation.is_returned = return_rec is not None
                allocation.return_condition = (
                    return_rec.condition if return_rec else None
                )
                allocation.show_return_status = show_return_status
                allocations.append(allocation)

        available_units = EquipmentUnit.objects.none()

        if borrow_request.status == BorrowRequest.BorrowRequestStatus.PENDING:
            available_units = EquipmentUnit.objects.filter(
                catalog_item=request_item.catalog_item,
                inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
                condition=EquipmentUnit.EquipmentCondition.FINE,
            ).order_by("asset_code")

        item_rows.append(
            {
                "request_item": request_item,
                "allocations": allocations,
                "available_units": available_units,
                "available_count": available_units.count(),
            }
        )

    loan = LoanRecord.objects.filter(borrow_request=borrow_request).first()
    borrower_profile = Profile.objects.filter(user=borrow_request.user).first()

    return render(
        request,
        "manage/borrow_request_review.html",
        {
            "borrow_request": borrow_request,
            "item_rows": item_rows,
            "loan": loan,
            "borrower_profile": borrower_profile,
            "EquipmentCondition": EquipmentUnit.EquipmentCondition,
        },
    )


@admin_required
@require_POST
def borrow_request_approve(request, pk):
    borrow_request = _get_borrow_request(pk)
    allocations_by_item = _structure_allocations_from_post(
        request, list(borrow_request.items.all())
    )

    try:
        approve_borrow_request(
            borrow_request,
            request.user,
            allocations_by_item,
        )
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Borrow request approved and units reserved.")

    return redirect("borrow_request_review", pk=pk)


@admin_required
@require_POST
def borrow_request_reject(request, pk):
    borrow_request = _get_borrow_request(pk)
    reason = request.POST.get("rejection_reason", "").strip()

    if not reason:
        messages.error(request, "Please provide a reason for rejecting the request.")
        return redirect("borrow_request_review", pk=pk)

    try:
        reject_borrow_request(
            borrow_request,
            request.user,
            reason=reason,
        )
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Borrow request rejected with reason provided.")

    return redirect("borrow_request_review", pk=pk)


@admin_required
@require_POST
def borrow_request_release(request, pk):
    borrow_request = _get_borrow_request(pk)

    try:
        release_borrow_request(borrow_request, request.user)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("borrow_request_review", pk=pk)

    messages.success(request, "Equipment released. The loan is now active.")
    return redirect("borrow_request_slip", pk=pk)


@admin_required
def borrow_request_slip(request, pk):
    borrow_request = _get_borrow_request(pk)
    loan = get_object_or_404(
        LoanRecord.objects.select_related("user"),
        borrow_request=borrow_request,
        released_at__isnull=False,
    )
    allocations = (
        UnitAllocation.objects.filter(
            request_item__borrow_request=borrow_request,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
        )
        .select_related("equipment_unit", "request_item__catalog_item")
        .order_by("request_item__catalog_item__name", "equipment_unit__asset_code")
    )
    borrower_profile = Profile.objects.filter(user=borrow_request.user).first()

    return render(
        request,
        "manage/borrow_request_slip.html",
        {
            "borrow_request": borrow_request,
            "loan": loan,
            "allocations": allocations,
            "borrower_profile": borrower_profile,
        },
    )


@admin_required
def audit(request):
    search_form = forms.AuditLogSearchForm(request.GET)
    logs = AuditLog.objects.all().order_by("-created_at")

    if search_form.is_valid():
        query = search_form.cleaned_data["q"].strip()
        logs = logs.filter(Q(action__icontains=query) | Q(user__email__icontains=query))

    logs, querystring = _table_paginate(request, logs)

    return render(
        request,
        "manage/audit.html",
        {
            "logs": logs,
            "page_obj": logs,
            "queryset": logs,
            "querystring": querystring,
            "search_form": search_form,
        },
    )


@admin_required
def settings(request):
    setting, created = SystemSetting.objects.get_or_create(id=1)

    if request.method == "POST":
        old_borrow_quantity, old_borrow_days = (
            setting.max_borrow_quantity,
            setting.max_borrow_days,
        )

        form = forms.SystemSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()

            message = f"{'No existing settings found. Using default ' if created else 'Updated system settings. '} Max Quantity: {setting.max_borrow_quantity}, Max Borrow Days: {setting.max_borrow_days}"

            AuditLog.objects.create(
                user=request.user,
                action=message,
            )

            if old_borrow_quantity != setting.max_borrow_quantity:
                messages.success(
                    request,
                    f"Updated MAX_BORROW_QUANTITY from {old_borrow_quantity} to {setting.max_borrow_quantity}.",
                )
            if old_borrow_days != setting.max_borrow_days:
                messages.success(
                    request,
                    f"Updated MAX_BORROW_DAYS from {old_borrow_days} to {setting.max_borrow_days}.",
                )

            return redirect("settings")
    else:
        form = forms.SystemSettingForm(instance=setting)

    return render(request, "manage/settings.html", {"form": form})


@admin_required
def catalogs(request, view="category", pk=0):
    @dataclass()
    class CatalogViewConfig:
        model: type
        form: type
        filter_form: type
        queryset: QuerySet
        querystring: str
        identifier: str
        label: str
        status_field: str
        status: int
        action: str

    def _apply_valid_filter(request, config):
        config.filter_form = config.filter_form(
            request.GET if request.method == "GET" else None
        )

        if request.method == "GET" and config.filter_form.is_valid():

            match view.lower():
                case "category":
                    query = config.filter_form.cleaned_data["q"].strip()
                    status = config.filter_form.cleaned_data["status"]

                    if query:
                        config.queryset = config.queryset.filter(
                            Q(name__icontains=query) | Q(description__icontains=query)
                        )
                    if status is not None:
                        config.queryset = config.queryset.filter(status=status)
                case "item":
                    query = config.filter_form.cleaned_data["q"].strip()
                    category = config.filter_form.cleaned_data["category"]
                    status = config.filter_form.cleaned_data["status"]

                    if query:
                        config.queryset = config.queryset.filter(
                            Q(name__icontains=query)
                            | Q(description__icontains=query)
                            | Q(category__name__icontains=query)
                        )
                    if category:
                        config.queryset = config.queryset.filter(category=category)
                    if status is not None:
                        config.queryset = config.queryset.filter(status=status)
                case "unit":
                    query = config.filter_form.cleaned_data["q"].strip()
                    category = config.filter_form.cleaned_data["category"]
                    catalog_item = config.filter_form.cleaned_data["catalog_item"]
                    inventory_status = config.filter_form.cleaned_data["inventory_status"]

                    if query:
                        config.queryset = config.queryset.filter(
                            Q(asset_code__icontains=query)
                            | Q(catalog_item__name__icontains=query)
                            | Q(catalog_item__category__name__icontains=query)
                        )
                    if category:
                        config.queryset = config.queryset.filter(
                            catalog_item__category=category
                        )
                    if catalog_item:
                        config.queryset = config.queryset.filter(catalog_item=catalog_item)
                    if inventory_status is not None:
                        config.queryset = config.queryset.filter(
                            inventory_status=inventory_status
                        )

        config.queryset, config.querystring = _table_paginate(request, config.queryset)

    def _audit(request, config, target):
        name = getattr(target, config.identifier, "") if target else ""
        record_audit(request.user, f"{config.action} '{name}' {config.label}")
        messages.success(
            request, f"Successfully {config.action.lower()} '{name}' {config.label}!"
        )

    views = {
        "category": CatalogViewConfig(
            Category,
            forms.CategoryForm,
            forms.CategoryFilterForm,
            Category.objects.annotate(item_count=Count("catalogitem")).order_by("name"),
            "",
            "name",
            "category",
            "status",
            Category.CategoryStatus.ARCHIVED,
            "Archived",
        ),
        "item": CatalogViewConfig(
            CatalogItem,
            forms.CatalogItemForm,
            forms.CatalogItemFilterForm,
            (
                CatalogItem.objects.select_related("category")
                .annotate(
                    total_units=Count("units", distinct=True),
                    available_units=Count(
                        "units",
                        filter=Q(
                            units__inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
                            units__condition=EquipmentUnit.EquipmentCondition.FINE,
                        ),
                        distinct=True,
                    ),
                )
                .order_by("category__name", "name")
            ),
            "",
            "name",
            "catalog item",
            "status",
            CatalogItem.CatalogItemStatus.ARCHIVED,
            "Archived",
        ),
        "unit": CatalogViewConfig(
            EquipmentUnit,
            forms.EquipmentUnitForm,
            forms.EquipmentUnitFilterForm,
            EquipmentUnit.objects.select_related("catalog_item__category").order_by(
                "asset_code"
            ),
            "",
            "asset_code",
            "equipment unit",
            "inventory_status",
            EquipmentUnit.EquipmentStatus.RETIRED,
            "Retired",
        ),
    }

    url_name = resolve(request.path).url_name

    config = views.get(view.lower())

    if config == None:
        raise Http404(f"No catalog of {view.title()} view!")

    form = target = None

    _apply_valid_filter(request, config)

    if url_name == "catalogs_archive":
        target = get_object_or_404(config.model, pk=pk)
        if request.method == "POST":
            setattr(target, config.status_field, config.status)
            target.save(update_fields=[config.status_field])

            _audit(request, config, target)
            return redirect("catalogs_view", view=view)

        context = {
            "view": view.lower(),
            "queryset": config.queryset,
            "querystring": config.querystring,
            "form": form,
            "filter_form": config.filter_form,
            "target": target,
        }
        return render(request, "manage/catalogs.html", context)

    if url_name == "catalogs_edit":
        target = get_object_or_404(config.model, pk=pk)
        config.action = "Edited"
    else:
        config.action = "Created"

    form = config.form(request.POST or None, instance=target)

    if form.is_valid():
        target = form.save()
        _audit(request, config, target)
        return redirect("catalogs_view", view=view)
    elif (
        request.method == "POST"
        and url_name != "catalogs_edit"
        and url_name != "catalogs_archive"
    ):
        target = form

    context = {
        "view": view.lower(),
        "queryset": config.queryset,
        "querystring": config.querystring,
        "form": form,
        "filter_form": config.filter_form,
        "target": target,
    }

    return render(request, "manage/catalogs.html", context)


@admin_required
def sample(request):
    return render(request, "manage/sample.html")


@admin_required
def account_list(request):
    search_form = forms.AccountSearchForm(request.GET or None)
    search_query = (request.GET.get("q") or request.GET.get("search") or "").strip()

    users = User.objects.all().select_related("profile").order_by("-role", "-profile__created_at", "-id")
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query)
            | Q(profile__first_name__icontains=search_query)
            | Q(profile__last_name__icontains=search_query)
            | Q(profile__contact_number__icontains=search_query)
        )

    total_count = users.count()
    users, querystring = _table_paginate(request, users)

    context = {
        "users": users,
        "page_obj": users,
        "queryset": users,
        "querystring": querystring,
        "search_form": search_form,
        "search_query": search_query,
        "total_count": total_count,
    }
    return render(request, "manage/account_list.html", context)


@admin_required
def activate_user(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    target_user.is_active = True
    target_user.save()

    record_audit(
        request.user,
        f"Activated user account '{target_user.email}' (ID #{target_user.id}).",
    )
    messages.success(request, f"Account '{target_user.email}' has been activated.")
    return redirect("account_list")


@admin_required
def deactivate_user(request, pk):
    target_user = get_object_or_404(User, pk=pk)

    if target_user.id == request.user.id:
        messages.error(request, "You cannot deactivate your own administrator account.")
        return redirect("account_list")

    target_user.is_active = False
    target_user.save()

    record_audit(
        request.user,
        f"Deactivated user account '{target_user.email}' (ID #{target_user.id}).",
    )
    messages.success(request, f"Account '{target_user.email}' has been deactivated.")
    return redirect("account_list")


@admin_required
def user_borrowing_history(request, pk):
    target_user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    borrow_requests = (
        BorrowRequest.objects.filter(user=target_user)
        .prefetch_related(
            "items__catalog_item",
            "items__allocations__equipment_unit",
            "review_records__user",
        )
        .order_by("-created_at")
    )

    active_count = borrow_requests.filter(
        status__in=[
            BorrowRequest.BorrowRequestStatus.ISSUED,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
        ]
    ).count()
    returned_count = borrow_requests.filter(
        status=BorrowRequest.BorrowRequestStatus.RETURNED
    ).count()
    overdue_count = borrow_requests.filter(
        status__in=[
            BorrowRequest.BorrowRequestStatus.ISSUED,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
        ],
        due_at__lt=timezone.now(),
    ).count()

    total_history_count = borrow_requests.count()
    borrow_requests, querystring = _table_paginate(request, borrow_requests)

    context = {
        "target_user": target_user,
        "borrow_requests": borrow_requests,
        "page_obj": borrow_requests,
        "queryset": borrow_requests,
        "querystring": querystring,
        "stats": {
            "total": total_history_count,
            "active": active_count,
            "returned": returned_count,
            "overdue": overdue_count,
        },
    }
    return render(request, "manage/user_borrowing_history.html", context)

from datetime import datetime

from dateutil import relativedelta
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.forms.models import ModelForm
from django.shortcuts import get_object_or_404, redirect, render
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
    RequestItem,
    ReturnRecord,
    SystemSetting,
    UnitAllocation,
)
from ..services.approvals import (
    approve_borrow_request,
    reject_borrow_request,
    release_borrow_request,
)

PAGE_ITEMS = 20


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
    active_requests = (
        BorrowRequest.objects.filter(
            status__in=[
                BorrowRequest.BorrowRequestStatus.ISSUED,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
            ]
        )
        .select_related("user")
        .order_by("-created_at")
    )

    # Recent return audit records
    recent_returns = ReturnRecord.objects.select_related(
        "borrow_request", "equipment_unit"
    ).order_by("-created_at")[:20]

    context = {
        "active_requests": active_requests,
        "recent_returns": recent_returns,
        "EquipmentCondition": EquipmentUnit.EquipmentCondition,
    }
    return render(request, "manage/returns.html", context)


@admin_required
@transaction.atomic
def process_unit_return(request):
    if request.method == "POST":
        borrow_request_id = request.POST.get("borrow_request_id")
        asset_code = request.POST.get("asset_code", "").strip()
        condition_val = int(
            request.POST.get("condition", EquipmentUnit.EquipmentCondition.FINE)
        )

        borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)
        unit = get_object_or_404(EquipmentUnit, asset_code=asset_code)

        # Verify unit was allocated to this request
        allocation_exists = UnitAllocation.objects.filter(
            request_item__borrow_request=borrow_request,
            equipment_unit=unit,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
        ).exists()

        if not allocation_exists:
            messages.error(
                request,
                f"Asset unit '{asset_code}' was not issued under Request #{borrow_request.id}.",
            )
            return redirect("manage_returns")

        # Check for duplicate return
        if ReturnRecord.objects.filter(
            borrow_request=borrow_request, equipment_unit=unit
        ).exists():
            messages.warning(
                request,
                f"Unit '{asset_code}' has already been returned for Request #{borrow_request.id}.",
            )
            return redirect("manage_returns")

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
            messages.success(
                request,
                f"Unit {unit.asset_code} returned in FINE condition and restored to AVAILABLE stock.",
            )
        else:
            # DAMAGED -> Route directly to MAINTENANCE
            unit.inventory_status = EquipmentUnit.EquipmentStatus.MAINTENANCE
            unit.save()

            # Automatically open a MaintenanceRecord
            MaintenanceRecord.objects.create(
                maintainer=request.user,
                unit=unit,
                issue=f"Returned DAMAGED from BorrowRequest #{borrow_request.id}.",
                action="Pending inspection and repair.",
                status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
                resolved_at=timezone.now(),  # Placeholder until finished
            )
            messages.warning(
                request,
                f"Unit {unit.asset_code} returned DAMAGED and placed into MAINTENANCE.",
            )

        # Evaluate overall BorrowRequest status (Partial vs Fully Returned)
        total_allocated = UnitAllocation.objects.filter(
            request_item__borrow_request=borrow_request,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
        ).count()

        total_returned = ReturnRecord.objects.filter(
            borrow_request=borrow_request
        ).count()

        if total_returned >= total_allocated:
            borrow_request.status = BorrowRequest.BorrowRequestStatus.RETURNED
        else:
            borrow_request.status = BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED
        borrow_request.save()

        # Audit Logging
        AuditLog.objects.create(
            user=request.user,
            action=f"Processed return of unit '{unit.asset_code}' for BorrowRequest #{borrow_request.id}.",
        )

    return redirect("manage_returns")


@admin_required
def maintenance_manage_view(request):
    tickets = MaintenanceRecord.objects.select_related("unit", "maintainer").order_by(
        "-created_at"
    )

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
            Q(inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE)
            | Q(condition=EquipmentUnit.EquipmentCondition.FINE)
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

    context["category_usage"] = {
        "labels": [s["category"] for s in category_stats],
        "data": [s["usage"] for s in category_stats],
    }

    context["settings"] = SystemSetting.objects.first()

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

    return render(
        request,
        "manage/returns_list.html",
        {
            "loans": loans,
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

    page_obj, querystring = _table_paginate(request, queryset)
    return render(
        request,
        "manage/borrow_requests.html",
        {
            "filter_form": filter_form,
            "page_obj": page_obj,
            "querystring": querystring,
        },
    )


@admin_required
def borrow_request_review(request, pk):
    borrow_request = _get_borrow_request(pk)
    item_rows = []

    for request_item in borrow_request.items.all():
        allocations = [
            allocation
            for allocation in request_item.allocations.all()
            if allocation.status != UnitAllocation.UnitAllocationStatus.CANCELLED
        ]
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

    try:
        reject_borrow_request(
            borrow_request,
            request.user,
        )
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Borrow request rejected.")

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
        print(query)

        logs = logs.filter(Q(action__icontains=query) | Q(user__email__icontains=query))

    return render(
        request,
        "manage/audit.html",
        {"logs": logs, "search_form": search_form},
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
def catalogs(request, view="category"):
    filter_form = None
    queryset = None
    data = request.POST or None
    form = None

    match view.lower():
        case "category":
            form = forms.CategoryForm(data)
        case "item":
            form = forms.CatalogItemForm(data)
        case "unit":
            form = forms.EquipmentUnitForm(data)

    match view.lower():
        case "category":
            filter_form = forms.CategoryFilterForm(request.GET)
            queryset = Category.objects.annotate(
                item_count=Count("catalogitem")
            ).order_by("name")

            if request.method == "GET" and filter_form.is_valid():
                query = filter_form.cleaned_data["q"].strip()
                status = filter_form.cleaned_data["status"]

                if query:
                    queryset = queryset.filter(
                        Q(name__icontains=query) | Q(description__icontains=query)
                    )
                if status is not None:
                    queryset = queryset.filter(status=status)
        case "item":
            filter_form = forms.CatalogItemFilterForm(request.GET)
            queryset = (
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
            )

            if request.method == "GET" and filter_form.is_valid():
                query = filter_form.cleaned_data["q"].strip()
                category = filter_form.cleaned_data["category"]
                status = filter_form.cleaned_data["status"]

                if query:
                    queryset = queryset.filter(
                        Q(name__icontains=query)
                        | Q(description__icontains=query)
                        | Q(category__name__icontains=query)
                    )
                if category:
                    queryset = queryset.filter(category=category)
                if status is not None:
                    queryset = queryset.filter(status=status)
        case "unit":
            filter_form = forms.EquipmentUnitFilterForm(request.GET)
            queryset = EquipmentUnit.objects.select_related(
                "catalog_item__category"
            ).order_by("asset_code")

            if request.method == "GET" and filter_form.is_valid():
                query = filter_form.cleaned_data["q"].strip()
                category = filter_form.cleaned_data["category"]
                catalog_item = filter_form.cleaned_data["catalog_item"]
                inventory_status = filter_form.cleaned_data["inventory_status"]

                if query:
                    queryset = queryset.filter(
                        Q(asset_code__icontains=query)
                        | Q(catalog_item__name__icontains=query)
                        | Q(catalog_item__category__name__icontains=query)
                    )
                if category:
                    queryset = queryset.filter(catalog_item__category=category)
                if catalog_item:
                    queryset = queryset.filter(catalog_item=catalog_item)
                if inventory_status is not None:
                    queryset = queryset.filter(inventory_status=inventory_status)

    assert isinstance(form, ModelForm)

    if request.method == "POST" and form.is_valid():
        form.save()

        created = (
            view
            if view == "category"
            else "catalog item"
            if view == "item"
            else "equipment unit"
        )

        record_audit(request.user, f"Created a new {created}")

        messages.success(request, f"Successfully created a new {created}!")
        redirect("catalogs")

    query

    context = {
        "view": view,
        "query": queryset,
        "form": form,
        "filter_form": filter_form,
    }

    return render(request, "manage/catalogs.html", context)


@admin_required
def sample(request):
    return render(request, "manage/sample.html")

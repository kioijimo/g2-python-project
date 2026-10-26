from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .. import forms, models
from ..decorators import admin_required
from app.models import (
    BorrowRequest,
    EquipmentUnit,
    RequestItem,
    UnitAllocation,
    ReturnRecord,
    MaintenanceRecord,
    AuditLog,
)

@login_required
@admin_required
def returns_manage_view(request):
    # Active loans eligible for returns (ISSUED or PARTIALLY_RETURNED)
    active_requests = BorrowRequest.objects.filter(
        status__in=[
            BorrowRequest.BorrowRequestStatus.ISSUED,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
        ]
    ).select_related("user").order_by("-created_at")

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


@login_required
@admin_required
@transaction.atomic
def process_unit_return(request):
    if request.method == "POST":
        borrow_request_id = request.POST.get("borrow_request_id")
        asset_code = request.POST.get("asset_code", "").strip()
        condition_val = int(request.POST.get("condition", EquipmentUnit.EquipmentCondition.FINE))

        borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)
        unit = get_object_or_404(EquipmentUnit, asset_code=asset_code)

        # Verify unit was allocated to this request
        allocation_exists = UnitAllocation.objects.filter(
            request_item__borrow_request=borrow_request,
            equipment_unit=unit,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
        ).exists()

        if not allocation_exists:
            messages.error(request, f"Asset unit '{asset_code}' was not issued under Request #{borrow_request.id}.")
            return redirect("manage_returns")

        # Check for duplicate return
        if ReturnRecord.objects.filter(borrow_request=borrow_request, equipment_unit=unit).exists():
            messages.warning(request, f"Unit '{asset_code}' has already been returned for Request #{borrow_request.id}.")
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
            messages.success(request, f"Unit {unit.asset_code} returned in FINE condition and restored to AVAILABLE stock.")
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
            messages.warning(request, f"Unit {unit.asset_code} returned DAMAGED and placed into MAINTENANCE.")

        # Evaluate overall BorrowRequest status (Partial vs Fully Returned)
        total_allocated = UnitAllocation.objects.filter(
            request_item__borrow_request=borrow_request,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
        ).count()

        total_returned = ReturnRecord.objects.filter(borrow_request=borrow_request).count()

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

@login_required
@admin_required
def maintenance_manage_view(request):
    tickets = MaintenanceRecord.objects.select_related("unit", "maintainer").order_by("-created_at")

    # Inventory Reconciliation Totals
    total_units = EquipmentUnit.objects.count()
    available_cnt = EquipmentUnit.objects.filter(inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE).count()
    reserved_cnt = EquipmentUnit.objects.filter(inventory_status=EquipmentUnit.EquipmentStatus.RESERVED).count()
    issued_cnt = EquipmentUnit.objects.filter(inventory_status=EquipmentUnit.EquipmentStatus.ISSUED).count()
    maintenance_cnt = EquipmentUnit.objects.filter(inventory_status=EquipmentUnit.EquipmentStatus.MAINTENANCE).count()
    retired_cnt = EquipmentUnit.objects.filter(inventory_status=EquipmentUnit.EquipmentStatus.RETIRED).count()

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


@login_required
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
        messages.success(request, f"Maintenance work order opened for unit '{unit.asset_code}'.")

    return redirect("manage_maintenance")


@login_required
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
            messages.success(request, f"Unit '{unit.asset_code}' successfully repaired and restored to AVAILABLE stock.")
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
        "available_units": 142,
        "pending_requests": 8,
        "active_loans": 34,
        "overdue_loans": 3,
    }

    # Hardcoded static data for charts
    context["monthly_trend"] = {
        "labels": ["May", "Jun", "Jul", "Aug", "Sep", "Oct"],
        "data": [18, 26, 22, 35, 42, 38],
    }

    context["category_usage"] = {
        "labels": ["Electronics & Lab", "Audio / Visual", "IT & Computing", "Measuring Tools"],
        "data": [40, 25, 20, 15],
    }

    return render(request, "manage/home.html", context)


@admin_required
def category(request):
    context = {}

    catalog_item_form = forms.CategoryItemForm(
        data=request.POST or None,
        status=models.CatalogItem.CatalogItemStatus.ACTIVE,
    )

    if request.method == "POST" and catalog_item_form.is_valid():
        catalog_item_form.save()

        catalog_item_form = forms.CategoryItemForm(
            status=models.CatalogItem.CatalogItemStatus.ACTIVE
        )

        messages.success(request, "Added category item successfully.")

    context["forms"] = {"catalog_item": catalog_item_form}

    return render(request, "manage/catalog.html", context)


@admin_required
def sample(request):
    return render(request, "manage/sample.html")

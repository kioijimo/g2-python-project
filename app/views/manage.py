from profiling.sampling import string_table

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q
from rich import status

from .. import forms, models
from ..decorators import admin_required
from .. models import (
    BorrowRequest,
    EquipmentUnit,
    UnitAllocation,
    ReturnRecord,
    MaintenanceRecord,
    AuditLog,
)

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
def loans_list(request):
    filter_type = request.GET.get("filter", 'active')

    queryset = BorrowRequest.objects.filter(
        status__in = [
            BorrowRequest.BorrowRequestStatus.ISSUED.value,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value,
            BorrowRequest.BorrowRequestStatus.RETURNED.value,
        ]
    ).select_related('user').prefetch_related('items__catalog_item')

    today = timezone.localdate()

    if filter_type == 'overdue':
        loans = [req for req in queryset if req.overdue_days(today) > 0]
    elif filter_type == 'returned':
        loans = queryset.filter(status = BorrowRequest.BorrowRequestStatus.RETURNED.value)
    else:
        loans = queryset.filter(
            status__in = [
                BorrowRequest.BorrowRequestStatus.ISSUED.value,
                BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value,
            ]
        )

    return render(request, 'manage/returns_list.html', {
        'loans': loans,
        'filter_type': filter_type,
        'today': today,
    })

@admin_required
def process_returns(request, request_id):
    borrow_request = get_object_or_404(
        BorrowRequest,
        id=request_id,
        status__in=[
            BorrowRequest.BorrowRequestStatus.ISSUED.value,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value,
        ]
    )

    allocations = UnitAllocation.objects.filter(
        request_item__borrow_request=borrow_request,
        status = UnitAllocation.UnitAllocationStatus.RELEASED.value
    ).select_related('equipment_unit', 'request_item__catalog_item')

    if request.method == "POST":
        allocated_ids_to_return = request.POST.getlist('allocations_to_return')

        if not allocated_ids_to_return:
            messages.error(request, "Select atleast one unit to return.")
            return redirect('process_returns', request_id = borrow_request.id)

        with transaction.atomic():
            for alloc in allocations:
                if str(alloc.id) in allocated_ids_to_return:
                    cond_val = int(request.POST.get(f'condition_{alloc.id}', EquipmentUnit.EquipmentCondition.FINE.value))

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
                        unit.inventory_status = EquipmentUnit.EquipmentStatus.MAINTENANCE.value
                        MaintenanceRecord.objects.create(
                            maintainer=request.user,
                            unit=unit,
                            issue=f'Damaged upon return from Request #{borrow_request.id}',
                            action='Awaiting inspection',
                            status=MaintenanceRecord.MaintenanceStatus.ACTIVE.value,
                        )
                    else:
                        unit.inventory_status = EquipmentUnit.EquipmentStatus.AVAILABLE.value

                    unit.save()
            remaining = UnitAllocation.objects.filter(
                request_item__borrow_request=borrow_request,
                status=UnitAllocation.UnitAllocationStatus.RELEASED.value
            ).count()

            if remaining == 0:
                borrow_request.status = BorrowRequest.BorrowRequestStatus.RETURNED.value
            else:
                borrow_request.status = BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED.value

            borrow_request.save()

            AuditLog.objects.create(
                user=request.user,
                action=f'Processed return for Request #{borrow_request.id} ({len(allocated_ids_to_return)} unit(s) returned)'
            )

            messages.success(request, "Successfully processed returns.")
            return redirect('loans_list')

    return render(request, 'manage/process_return.html', {
        'borrow_request': borrow_request,
        'allocations': allocations,
        'conditions': EquipmentUnit.EquipmentCondition.choices,
    })



@admin_required
def sample(request):
    return render(request, "manage/sample.html")

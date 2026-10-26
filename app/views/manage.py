from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .. import forms, models
from ..decorators import admin_required
from ..models import (
    AuditLog,
    BorrowRequest,
    EquipmentUnit,
    MaintenanceRecord,
    ReturnRecord,
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
        models.BorrowRequest.objects.select_related("user").prefetch_related(
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
        "labels": [
            "Electronics & Lab",
            "Audio / Visual",
            "IT & Computing",
            "Measuring Tools",
        ],
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
    queryset = models.BorrowRequest.objects.select_related(
        "user"
    ).prefetch_related("review_records__user").order_by("-created_at")

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
            if allocation.status != models.UnitAllocation.UnitAllocationStatus.CANCELLED
        ]
        available_units = models.EquipmentUnit.objects.none()

        if borrow_request.status == models.BorrowRequest.BorrowRequestStatus.PENDING:
            available_units = models.EquipmentUnit.objects.filter(
                catalog_item=request_item.catalog_item,
                inventory_status=models.EquipmentUnit.EquipmentStatus.AVAILABLE,
                condition=models.EquipmentUnit.EquipmentCondition.FINE,
            ).order_by("asset_code")

        item_rows.append(
            {
                "request_item": request_item,
                "allocations": allocations,
                "available_units": available_units,
                "available_count": available_units.count(),
            }
        )

    loan = models.LoanRecord.objects.filter(borrow_request=borrow_request).first()
    borrower_profile = models.Profile.objects.filter(user=borrow_request.user).first()

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
        models.LoanRecord.objects.select_related("user"),
        borrow_request=borrow_request,
        released_at__isnull=False,
    )
    allocations = (
        models.UnitAllocation.objects.filter(
            request_item__borrow_request=borrow_request,
            status=models.UnitAllocation.UnitAllocationStatus.RELEASED,
        )
        .select_related("equipment_unit", "request_item__catalog_item")
        .order_by("request_item__catalog_item__name", "equipment_unit__asset_code")
    )
    borrower_profile = models.Profile.objects.filter(user=borrow_request.user).first()

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
def sample(request):
    return render(request, "manage/sample.html")

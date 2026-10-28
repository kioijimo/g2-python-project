from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    BorrowRequest,
    CatalogItem,
    EquipmentUnit,
    RequestItem,
    SystemSetting,
    UnitAllocation,
)
from .catalog import requestable_units_count


def due_date_bounds(settings=None):
    settings = settings or SystemSetting.load()
    today = timezone.localdate()
    return (
        today + timedelta(days=1),
        today + timedelta(days=settings.max_borrow_days),
    )


def due_at_for_date(desired_date):
    return timezone.make_aware(
        datetime.combine(desired_date, time.max),
        timezone.get_current_timezone(),
    )


def create_borrow_request(user, purpose, due_at, items):
    if not items:
        raise ValidationError("Add at least one catalog item.")
    if len(items) > 3:
        raise ValidationError("A request can contain at most three catalog items.")

    with transaction.atomic():
        list(
            CatalogItem.objects.select_for_update()
            .filter(pk__in={item.pk for item, _ in items})
            .order_by("pk")
        )

        settings = SystemSetting.load()
        min_date, max_date = due_date_bounds(settings)
        due_date = timezone.localtime(due_at).date()

        if not min_date <= due_date <= max_date:
            raise ValidationError(
                f"Choose a return date between {min_date.isoformat()} and "
                f"{max_date.isoformat()}."
            )

        selected_ids = set()

        for catalog_item, quantity in items:
            if quantity < 1:
                raise ValidationError("Quantity must be at least one.")
            if quantity > settings.max_borrow_quantity:
                raise ValidationError(
                    f"Maximum {settings.max_borrow_quantity} unit(s) per item."
                )
            if catalog_item.pk in selected_ids:
                raise ValidationError(
                    "Each catalog item can only be requested once."
                )

            available = requestable_units_count(catalog_item)
            if quantity > available:
                raise ValidationError(
                    f"Only {available} unit(s) are currently available for "
                    f"{catalog_item.name}."
                )
            selected_ids.add(catalog_item.pk)

        borrow_request = BorrowRequest.objects.create(
            user=user,
            purpose=purpose,
            due_at=due_at,
            status=BorrowRequest.BorrowRequestStatus.PENDING,
        )
        RequestItem.objects.bulk_create(
            [
                RequestItem(
                    borrow_request=borrow_request,
                    catalog_item=catalog_item,
                    quantity=quantity,
                )
                for catalog_item, quantity in items
            ]
        )

    return borrow_request


def cancel_borrow_request(borrow_request):
    with transaction.atomic():
        request = BorrowRequest.objects.select_for_update().get(pk=borrow_request.pk)

        if not request.is_cancellable:
            raise ValidationError("This request can no longer be cancelled.")

        if request.status == BorrowRequest.BorrowRequestStatus.APPROVED:
            allocations = UnitAllocation.objects.select_for_update().filter(
                request_item__borrow_request=request,
                status=UnitAllocation.UnitAllocationStatus.PENDING,
            )
            unit_ids = list(
                allocations.values_list("equipment_unit_id", flat=True)
            )

            if unit_ids:
                EquipmentUnit.objects.filter(
                    pk__in=unit_ids,
                    inventory_status=EquipmentUnit.EquipmentStatus.RESERVED,
                ).update(inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE)
                allocations.update(
                    status=UnitAllocation.UnitAllocationStatus.CANCELLED
                )

        request.status = BorrowRequest.BorrowRequestStatus.CANCELLED
        request.save(update_fields=["status"])

    return request

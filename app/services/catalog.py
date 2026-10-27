from django.db.models import (
    Count,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Greatest

from ..models import (
    BorrowRequest,
    CatalogItem,
    Category,
    EquipmentUnit,
    RequestItem,
)

SERVICEABLE_INVENTORY_STATUSES = (
    EquipmentUnit.EquipmentStatus.AVAILABLE,
    EquipmentUnit.EquipmentStatus.RESERVED,
    EquipmentUnit.EquipmentStatus.ISSUED,
)


def active_catalog_items(search=""):
    items = CatalogItem.objects.filter(
        status=CatalogItem.CatalogItemStatus.ACTIVE,
        category__status=Category.CategoryStatus.ACTIVE,
    )

    search = search.strip()
    if search:
        items = items.filter(
            Q(name__icontains=search) | Q(category__name__icontains=search)
        )

    pending_requested_subquery = (
        RequestItem.objects.filter(
            catalog_item=OuterRef("pk"),
            borrow_request__status=BorrowRequest.BorrowRequestStatus.PENDING,
        )
        .values("catalog_item")
        .annotate(total=Sum("quantity"))
        .values("total")
    )

    return (
        items.select_related("category")
        .annotate(
            serviceable_count=Count(
                "units",
                filter=Q(
                    units__condition=EquipmentUnit.EquipmentCondition.FINE,
                    units__inventory_status__in=SERVICEABLE_INVENTORY_STATUSES,
                ),
                distinct=True,
            ),
            available_count=Count(
                "units",
                filter=Q(
                    units__condition=EquipmentUnit.EquipmentCondition.FINE,
                    units__inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
                ),
                distinct=True,
            ),
            pending_requested=Coalesce(
                Subquery(
                    pending_requested_subquery,
                    output_field=IntegerField(),
                ),
                Value(0),
            ),
        )
        .annotate(
            requestable_count=Greatest(
                F("available_count") - F("pending_requested"),
                Value(0),
            )
        )
        .order_by("category__name", "name")
    )


def available_units_count(catalog_item):
    return catalog_item.units.filter(
        condition=EquipmentUnit.EquipmentCondition.FINE,
        inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
    ).count()


def pending_requested_quantity(catalog_item):
    return (
        RequestItem.objects.filter(
            catalog_item=catalog_item,
            borrow_request__status=BorrowRequest.BorrowRequestStatus.PENDING,
        ).aggregate(total=Sum("quantity"))["total"]
        or 0
    )


def requestable_units_count(catalog_item):
    return max(
        available_units_count(catalog_item)
        - pending_requested_quantity(catalog_item),
        0,
    )

from django.db.models import Count, Q

from ..models import CatalogItem, Category, EquipmentUnit

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
        )
        .order_by("category__name", "name")
    )


def available_units_count(catalog_item):
    return catalog_item.units.filter(
        condition=EquipmentUnit.EquipmentCondition.FINE,
        inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
    ).count()

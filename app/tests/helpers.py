from datetime import timedelta

from django.utils import timezone

from app.models import (
    BorrowRequest,
    CatalogItem,
    Category,
    EquipmentUnit,
    Profile,
    RequestItem,
    SystemSetting,
    User,
)

PASSWORD = "Str0ng-Passw0rd!2026"
CONTACT_NUMBER = "09123456789"


def create_user(email="basic@example.com", with_profile=True):
    user = User.objects.create_user(email, PASSWORD)
    if with_profile:
        Profile.objects.create(
            user=user,
            first_name="Basic",
            last_name="User",
            contact_number=CONTACT_NUMBER,
        )
    return user


def create_admin(email="admin@example.com"):
    return User.objects.create_superuser(email, PASSWORD)


def create_category(name="Computing", status=Category.CategoryStatus.ACTIVE):
    return Category.objects.create(
        name=name,
        description=f"{name} equipment",
        status=status,
    )


def create_catalog_item(
    name="Laptop",
    category=None,
    status=CatalogItem.CatalogItemStatus.ACTIVE,
):
    category = category or create_category()
    return CatalogItem.objects.create(
        category=category,
        name=name,
        description=f"{name} description",
        status=status,
    )


def create_units(
    catalog_item,
    count=1,
    inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
    condition=EquipmentUnit.EquipmentCondition.FINE,
):
    units = []
    for index in range(count):
        units.append(
            EquipmentUnit.objects.create(
                asset_code=f"{catalog_item.pk}-{index}",
                catalog_item=catalog_item,
                inventory_status=inventory_status,
                condition=condition,
            )
        )
    return units


def create_settings(max_borrow_days=7, max_borrow_quantity=3):
    return SystemSetting.objects.create(
        max_borrow_days=max_borrow_days,
        max_borrow_quantity=max_borrow_quantity,
    )


def create_borrow_request(
    user,
    purpose="Class project",
    status=BorrowRequest.BorrowRequestStatus.PENDING,
    due_at=None,
):
    if due_at is None:
        due_at = timezone.now() + timedelta(days=1)
    return BorrowRequest.objects.create(
        user=user,
        purpose=purpose,
        status=status,
        due_at=due_at,
    )


def create_request_item(borrow_request, catalog_item, quantity=1):
    return RequestItem.objects.create(
        borrow_request=borrow_request,
        catalog_item=catalog_item,
        quantity=quantity,
    )

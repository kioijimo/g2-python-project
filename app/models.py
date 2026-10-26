from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import (
    EmailValidator,
    MaxLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils import timezone

from .managers import UserManager

"""
TODO:
    - Solidify system workflow
CHANGES:
    - Finished a defacto model of the system database
"""

NAME_LENGTH = 64  # Maximum length for names
DESCRIPTION_LENGTH = (
    254  # Single maximum length for descriptions for any kind of entity
)
CONTACT_NUM_LENGTH = 11

# Default system settings values
MAX_BORROW_QUANTITY = 3
MAX_BORROW_DAYS = 7


class User(AbstractBaseUser):
    """
    A user of the system. Inherits Django Auth's AbstractUser model.

    Attributes
    ----------
    `email`: str
        The user's email. Must not exceed `EMAIL_LENGTH` number of characters. Required to be unique.
    `role: int
        The user's role in the system whether they are a staff (ADMIN) or not. To see roles, check `User.UserRoles` class.
    `status`: int
        The user's activity status in the system. To see the valid statuses, check `User.UserStatus` class.
    """

    class UserRoles(models.IntegerChoices):
        """This indicates whether the user is ADMIN or not"""

        USER = 0
        ADMIN = 1

    class UserStatus(models.IntegerChoices):
        """This indicates whether the user can apply for BORROW_REQUESTS or not."""

        ACTIVE = 1
        INACTIVE = 0

    # Unused AbstractBaseUser fields
    is_superuser = None
    username = None
    first_name = None
    last_name = None

    email = models.EmailField(unique=True, validators=[EmailValidator])
    role = models.IntegerField(default=UserRoles.USER.value, choices=UserRoles)
    status = models.IntegerField(default=UserStatus.ACTIVE.value, choices=UserStatus)

    # Replaces username as the unique key for user and uses email instead
    REQUIRED_FIELDS = []
    USERNAME_FIELD = "email"

    objects = UserManager()

    @property
    def is_active(self):
        """Expose Django auth's active check backed by `status`."""
        return self.status == self.UserStatus.ACTIVE

    @is_active.setter
    def is_active(self, value):
        self.status = self.UserStatus.ACTIVE if value else self.UserStatus.INACTIVE

    @property
    def is_staff(self):
        """Allow future admin tooling to check for staff status."""
        return self.role == self.UserRoles.ADMIN

    def __str__(self):
        return self.email


AUTH_USER = getattr(settings, "AUTH_USER_MODEL", User)


class Profile(models.Model):
    """
    The personal information of users.

    Attributes
    ----------
    `first_name`: str
        The user's first name. Must not exceed `NAME_LENGTH` number of characters.
    `last_name`: str
        The user's last name. Must not exceed `NAME_LENGTH` number of characters.
    `contact_number`: str
        The user's personal contact number. Must not exceed `CONTACT_NUM_LENGTH` number of characters.
    `created_at`: datetime
        The date and time when the user's account is created.
    """

    user = models.OneToOneField(
        AUTH_USER, on_delete=models.PROTECT
    )  # Protect protects the foreign key object from being deleted as long as they are being referenced by this entity. This serves as extra hardener for the 'no delete' policy.
    first_name = models.CharField(
        max_length=NAME_LENGTH, validators=[MaxLengthValidator(NAME_LENGTH)]
    )
    last_name = models.CharField(
        max_length=NAME_LENGTH, validators=[MaxLengthValidator(NAME_LENGTH)]
    )
    contact_number = models.CharField(
        max_length=CONTACT_NUM_LENGTH,
        validators=[RegexValidator("^(09)\\d{9}$", "Enter a valid phone number.")],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.first_name) + str(self.last_name)


class Category(models.Model):
    """
    Organizational label for inventory items.

    Attributes
    ----------
    `name`: str
        The category's label name.
    `description`: str
        The description of the category.
    `status`: int
        The status of the category. To see the statuses, check `Category.CategoryStatus` class.
    `created_at`: datetime
        The date and time when the category is first created.
    """

    class CategoryStatus(models.IntegerChoices):
        """
        The statuses of categories

        `ACTIVE`
            The category is available.
        `ARCHIVED`
            The category has been retired and all of the items belonging in it are all retired as well.
        """

        ACTIVE = 1
        ARCHIVED = 0

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(choices=CategoryStatus)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return str(self.name)


class CatalogItem(models.Model):
    """
    An item classifier. An item brand.

    Attributes
    ----------
    `category`: Category
        The category the item belongs to.
    `name`: str
        The item brand name. Must not exceed `NAME_LENGTH` number of characters.
    `description`: str
        The description of the item brand. Must not exceed `DESCRIPTION_LENGTH` number of characters.
    `status`: int
        The status of the item brand. To see the statuses, check `CatalogItem.CatalogItemStatus` class.
    """

    class CatalogItemStatus(models.IntegerChoices):
        """
        The statuses of items.

        `ACTIVE`
            The item brand is available
        `ARCHIVED`
            The item brand has been retired and is not available for users to borrow.
        """

        ACTIVE = 1
        ARCHIVED = 0

    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    name = models.CharField(max_length=NAME_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(
        default=CatalogItemStatus.ACTIVE.value, choices=CatalogItemStatus
    )

    def __str__(self):
        return str(self.name)


class EquipmentUnit(models.Model):
    """
    The item under a catalog item.

    Attributes
    ----------
    `asset_code`: str
        A unique identifier (different from database ID). Must not exceed `NAME_LENGTH` number of characters.
    `catalog_item`: CatalogItem
        The catalog item the equipment unit belongs to.
    `inventory_status`: int
        The inventory status of the equipment unit. To see statuses, check `EquipmentUnit.EquipmentStatus` class.
    `condition`: int
        The condition of the equipment unit. To see conditions, check `EquipmentUnit.EquipmentCondition` class.
    `created_at`: datetime
        The datetime when the unit was acquired.
    """

    class EquipmentStatus(models.IntegerChoices):
        AVAILABLE = 1
        RESERVED = 2
        ISSUED = 3
        MAINTENANCE = 4
        RETIRED = 0

    class EquipmentCondition(models.IntegerChoices):
        FINE = 1
        DAMAGED = 0

    asset_code = models.CharField(max_length=NAME_LENGTH)
    catalog_item = models.ForeignKey(
        CatalogItem, on_delete=models.PROTECT, related_name="units"
    )
    inventory_status = models.IntegerField(choices=EquipmentStatus)
    condition = models.IntegerField(choices=EquipmentCondition)
    acquired_at = models.DateTimeField(auto_now_add=True)


class BorrowRequest(models.Model):
    """
    The request form of users trying to borrow equipment units.

    Attributes
    ----------
    `user`: User
        The user that created the borrow request.
    `purpose`: str
        The purpose of the user for creating a borrow request. Must not exceed `DESCRIPTION_LENGTH` number of characters.
    `status`: int
        The workflow status of the request. To see the statuses, check `BorrowRequest.BorrowRequestStatus` class.
    `created_at`: datetime
        The date and time when the request was created.
    `due_at`: datetime
        The date and time the user must return the borrowed item(s).
    """

    class BorrowRequestStatus(models.IntegerChoices):
        """The status of a borrow request.

        `PENDING`
            The request has been created by the user.
        `APPROVED`
            The request has been approved by an admin.
        `ISSUED`
            idk
        `PARTIALLY_RETURNED`
            Some of the borrowed items have been returned by the user.
        `RETURNED`
            All of the borrowed items have been returned by the user.
        `REJECTED`
            The request from the user has been rejected by an admin.
        `CANCELLED`
            The request has been cancelled by the user or an admin. This is used for emergency cases such as request mistake or change of mind situations.
        """

        PENDING = 1
        APPROVED = 2
        ISSUED = 3
        PARTIALLY_RETURNED = 4
        RETURNED = 5
        REJECTED = 6
        CANCELLED = 0

    user = models.ForeignKey(
        AUTH_USER, on_delete=models.PROTECT, related_name="borrow_requests"
    )
    purpose = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(
        choices=BorrowRequestStatus,
        default=BorrowRequestStatus.PENDING.value,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()

    @property
    def is_cancellable(self):
        return self.status in (
            self.BorrowRequestStatus.PENDING,
            self.BorrowRequestStatus.APPROVED,
        )

    def overdue_days(self, as_of=None):
        if self.status not in (
            self.BorrowRequestStatus.ISSUED,
            self.BorrowRequestStatus.PARTIALLY_RETURNED,
        ):
            return 0

        as_of = as_of or timezone.localdate()
        due_date = timezone.localtime(self.due_at).date()
        return max(0, (as_of - due_date).days)


class RequestItem(models.Model):
    """
    The reference item a borrow request lists down.

    Attributes
    ----------
    `borrow_request`: BorrowRequest
        The borrow request this reference item belongs to.
    `catalog_item`: CatalogItem
        The catalog item to be borrowed.
    `quantity`: int
        The number of units to be borrowed.
    """

    borrow_request = models.ForeignKey(
        BorrowRequest, on_delete=models.PROTECT, related_name="items"
    )
    catalog_item = models.ForeignKey(
        CatalogItem, on_delete=models.PROTECT, related_name="request_items"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("borrow_request", "catalog_item"),
                name="unique_catalog_item_per_request",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="request_item_quantity_gte_1",
            ),
        ]


class UnitAllocation(models.Model):
    """
    The allocation process details.

    Attributes
    ----------
    `request_item`: RequestItem
        The reference item to lend to the user borrowing it.
    `equipment_unit`: EquipmentUnit
        The actual item to lend to the user borrowing it.
    `status`: int
        The status of the allocation process. To see statuses, check `UnitAllocation.UnitAllocationStatus` class.
    `allocated_at`: datetime
        The date and time when the user receives their borrowed unit.
    """

    class UnitAllocationStatus(models.IntegerChoices):
        PENDING = 1
        RELEASED = 2
        CANCELLED = 0

    request_item = models.ForeignKey(
        RequestItem, on_delete=models.PROTECT, related_name="allocations"
    )
    equipment_unit = models.ForeignKey(EquipmentUnit, on_delete=models.PROTECT)
    status = models.IntegerField(choices=UnitAllocationStatus)
    allocated_at = models.DateTimeField()


class LoanRecord(models.Model):
    """
    A record when a borrow request gets approved.

    Attributes
    ----------
    `borrow_request`: BorrowRequest
        The request the loan record is attached to. Strictly must be one-to-one.
    `user`: User
        The admin user that provisioned the request.
    `created_at`: datetime
        The date and time the record has been created.
    """

    borrow_request = models.ForeignKey(BorrowRequest, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class ReturnRecord(models.Model):
    """
    A record when a borrow request has finished and items borrowed are returned.

    Attributes
    ----------
    `borrow_request`: BorrowRequest
        The request the loan record is attached to. Strictly must be one-to-one.
    `equipment_unit`: EquipmentUnit
        An individual unit returned.
    `condition`: int
        The returned unit's condition.
    `created_at`: datetime
        The date and time the record has been created.
    """

    borrow_request = models.ForeignKey(BorrowRequest, on_delete=models.PROTECT)
    equipment_unit = models.ForeignKey(EquipmentUnit, on_delete=models.PROTECT)
    condition = models.IntegerField(choices=EquipmentUnit.EquipmentCondition)
    created_at = models.DateTimeField(auto_now_add=True)


class MaintenanceRecord(models.Model):
    """
    Holds maintenance detail of an equipment unit.

    Attributes
    ----------
    `maintainer`: User
        The user peforming the maintenance. Must strictly be a user of an ADMIN role.
    `unit`: EquipmentUnit
        The unit the maintainer is performing maintenance on.
    `issue`: str
        A description of the issue of the unit which explains the maintenance.
    `action`: str
        A description of the action taken to fix the issue.
    `status`: int
        The current status of the ongoing maintenance. To see the valid values, check MaintenanceRecord.MaintenanceStatus class
    `created_at`: datetime
        The date and time when the maintenance is first opened.
    `resolved_at`: datetime
        The date and time when the maintenance has reached the FINISHED status.
    """

    class MaintenanceStatus(models.IntegerChoices):
        """Status indicating the current status of a maintenance process on an equipment unit"""

        ACTIVE = 1
        PAUSED = 2
        FINISHED = 3
        CANCELLED = 0

    maintainer = models.ForeignKey(AUTH_USER, on_delete=models.PROTECT)
    unit = models.ForeignKey(EquipmentUnit, on_delete=models.PROTECT)
    issue = models.CharField(max_length=DESCRIPTION_LENGTH)
    action = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(choices=MaintenanceStatus)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField()


class AuditLog(models.Model):
    """
    Logs the system activity of admin users.

    Attributes
    ----------
    `user`: User
        The user that performed a system activity. Must be strictly a user of the ADMIN role.
    `action`: str
        A description of the activity they performed in the system.
    `created_at`: datetime
        The date and time the user performed the described activity.
    """

    user = models.ForeignKey(AUTH_USER, on_delete=models.PROTECT)
    action = models.CharField(max_length=DESCRIPTION_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)


class SystemSetting(models.Model):
    """
    Entity that holds the system configurations.

    Attributes
    ----------
    `max_borrow_quantity`: int
        The maximum allowed quantity for each equipment unit users can borrow per request.
    `max_borrow_days`: int
        The maximum allowed days the users can keep their borrowed equipment(s) without their BORROW_REQUEST being marked as OVERDUE.
    """

    max_borrow_quantity = models.IntegerField(default=MAX_BORROW_QUANTITY)
    max_borrow_days = models.IntegerField(default=MAX_BORROW_DAYS)

    @classmethod
    def load(cls):
        return cls.objects.order_by("pk").first() or cls()

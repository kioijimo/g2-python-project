from enum import Enum

from django.db import models

"""
TODO:
    - Solidify system workflow
CHANGES:
    - Finished a defacto model of the system database
"""

NAME_LENGTH = 64  # Maximum length for names
EMAIL_LENGTH = 254  # According to IETF RFC 2821
DESCRIPTION_LENGTH = (
    EMAIL_LENGTH  # Single maximum length for descriptions for any kind of entity
)
CONTACT_NUM_LENGTH = 11


class User(models.Model):
    """
    A user of the system.

    Attributes
    ----------
    `password`: str
        The user's password used to authenticate into the system. Must strictly follow django-auth's protocol.
    `role`: int
        The user's role in the system. To see the valid roles, check `User.UserRoles` class.
    `status`: int
        The user's activity status in the system. To see the valid statuses, check `User.UserStatus` class.
    """

    class UserRoles(models.IntegerChoices):
        """
        The roles of users in the system.

        `USER`
            Allows users to perform borrow requests, change their profile information, and browse available equipment units.
        `ADMIN`
            Allows users to manage categories, catalog items and equipment units, process borrow requests and loans, and edit the system configurations.
        """

        USER = 0
        ADMIN = 1

    class UserStatus(models.IntegerChoices):
        """This indicates whether the user can apply for BORROW_REQUESTS or not."""

        ACTIVE = 0
        INACTIVE = 1

    password = models.CharField(max_length=NAME_LENGTH)
    role = models.IntegerField(choices=UserRoles)
    status = models.IntegerField(choices=UserStatus)


class Profile(models.Model):
    """
    The personal information of users.

    Attributes
    ----------
    `first_name`: str
        The user's first name. Must not exceed `NAME_LENGTH` number of characters.
    `last_name`: str
        The user's last name. Must not exceed `NAME_LENGTH` number of characters.
    `email`: str
        The user's email. Must not exceed `EMAIL_LENGTH` number of characters.
    `contact_number`: str
        The user's personal contact number. Must not exceed `CONTACT_NUM_LENGTH` number of characters.
    `created_at`: datetime
        The date and time when the user's account is created.
    """

    user = models.ForeignKey(
        User, on_delete=models.PROTECT
    )  # Protect protects the foreign key object from being deleted as long as they are being referenced by this entity. This serves as extra hardener for the 'no delete' policy.
    first_name = models.CharField(max_length=NAME_LENGTH)
    last_name = models.CharField(max_length=NAME_LENGTH)
    email = models.CharField(max_length=EMAIL_LENGTH)
    contact_number = models.CharField(max_length=CONTACT_NUM_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)


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

        ACTIVE = 0
        ARCHIVED = 1

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(choices=CategoryStatus)
    created_at = models.DateTimeField(auto_now_add=True)


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

        ACTIVE = 0
        ARCHIVED = 1

    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    name = models.CharField(max_length=NAME_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(choices=CatalogItemStatus)


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
        AVAILABLE = 0
        RESERVED = 1
        ISSUED = 2
        MAINTENANCE = 3
        RETIRED = 4

    class EquipmentCondition(models.IntegerChoices):
        FINE = 0
        DAMAGED = 1

    asset_code = models.CharField(max_length=NAME_LENGTH)
    catalog_item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT)
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
    `reason`: str
        The purpose of the user for creating a borrow request. Must not exceed `DESCRIPTION_LEGNTH` number of characters.
    `status`: int
        The workflow status of the request. To see the statuses, check `BorrowRequest.BorrowRequestStatus` class.
    `created_at`: datetime
        The date and time when the request was created.
    `due_at`: datetime
        The date and time the user must return the borrowed item(s). Defaults to `DefaultSetting.Defaults.MAXIMUM_BORROW_DAYS`.
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

        PENDING = 0
        APPROVED = 1
        ISSUED = 2
        PARTIALLY_RETURNED = 3
        RETURNED = 4
        REJECTED = 5
        CANCELLED = 6

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    reason = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(choices=BorrowRequestStatus)
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()


class RequestItem(models.Model):
    """
    The reference item a borrow request lists down.

    Attributes
    ----------
    `borrow_request`: BorrowRequest
        The borrow request this reference item belongs to.
    `equipment_unit`: EquipmentUnit
        The unit to be borrowed.
    `quantity`: int
        The number of units to be borrowed. Defaults to `SystemSetting.Defaults.MAX_BORROW_QUANTITY` units.
    """

    borrow_request = models.ForeignKey(BorrowRequest, on_delete=models.PROTECT)
    equipment_unit = models.ForeignKey(EquipmentUnit, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()


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
        PENDING = 0
        RELEASED = 1
        CANCELLED = 2

    request_item = models.ForeignKey(RequestItem, on_delete=models.PROTECT)
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

        ACTIVE = 0
        PAUSED = 1
        CANCELLED = 2
        FINISHED = 3

    maintainer = models.ForeignKey(User, on_delete=models.PROTECT)
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

    user = models.ForeignKey(User, on_delete=models.PROTECT)
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

    class Defaults(Enum):
        """Default configuration values for the system settings"""

        MAX_BORROW_QUANTITY = 3
        LOAN_DURATION = 7

    max_borrow_quantity = models.IntegerField(
        default=Defaults.MAX_BORROW_QUANTITY.value
    )
    max_borrow_days = models.IntegerField(default=Defaults.LOAN_DURATION.value)

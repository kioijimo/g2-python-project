from enum import Enum

from django.db import models

"""
TODO:
    - Solidify system workflow
    - Finish modelling every required entity appropriately
        MISSING:
            - CatalogItem (WIP) - Missing fields
            - EquipmentUnit
            - BorrowRequest
            - RequestItem
            - UnitAllocation
            - LoanRecord
            - ReturnRecord

CHANGES:
    - Created models.Choices for models that require them (basically moving the separate enums into the models they belong to)
    - Moved default settings constants in the class under SystemSetting.Defaults class
    - Followed docstring documentation for python code
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
        The date and time when the user's account is created. Defaults to the date and time when the user's instance is first created.
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
        The date and time when the category is first created. Defaults to the date and time when the category's instance is first created.
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


# Represents an item
class CatalogItem(models.Model):
    """
    The item users can borrow.

    Attributes
    ----------
    `category`: Category
        The category the item belongs to.
    `name`: str
        The item name. Must not exceed `NAME_LENGTH` number of characters.
    `description`: str
        The desscription of the item. Must not exceed `DESCRIPTION_LENGTH` number of characters.
    `status`: int
        The status of the item. To see the statuses, check `CatalogItem.CatalogItemStatus` class.
    """

    class CatalogItemStatus(Enum):
        """
        The statuses of items.

        `ACTIVE`
            The item is available
        `ARCHIVED`
            The item has been retired and is not available for users to borrow.
        """

        ACTIVE = 0
        ARCHIVED = 1

    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    name = models.CharField(max_length=NAME_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH)
    status = models.IntegerField(choices=CatalogItemStatus)


class EquipmentUnit(models.Model):
    class EquipmentStatus(models.IntegerChoices):
        AVAILABLE = 0
        RESERVED = 1
        ISSUED = 2
        MAINTENANCE = 3
        RETIRED = 4


class BorrowRequest(models.Model):
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


class RequestItem(models.Model):
    pass


class UnitAllocation(models.Model):
    pass


class LoanRecord(models.Model):
    pass


class ReturnRecord(models.Model):
    pass


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
        The date and time when the maintenance is first opened. Defaults to the date and time where the instance is first created.
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


# System settings
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

    class Defaults:
        """Default configuration values for the system settings"""

        MAX_BORROW_QUANTITY = 3
        LOAN_DURATION = 7

    max_borrow_quantity = models.IntegerField()
    max_borrow_days = models.IntegerField()

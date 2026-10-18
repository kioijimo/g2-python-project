from enum import Enum

from django.db import models

"""
TODO:
    Solidify system workflow
    Finish modelling every required entity appropriately
        MISSING:
            CatalogItem (WIP) - Missing fields
            EquipmentUnit
            BorrowRequest
            RequestItem
            UnitAllocation
            LoanRecord
            ReturnRecord
            MaintenanceRecord
            AuditLog
"""

# Field max lengths
NAME_LENGTH = 64  # Maximum length for names
EMAIL_LENGTH = 254  # According to IETF RFC 2821
DESCRIPTION_LENGTH = (
    EMAIL_LENGTH  # Single maximum length for descriptions for any kind of entity
)
CONTACT_NUM_LENGTH = 11

# SYSTEM_SETTINGS defaults
MAX_BORROW_QUANTITY = 3  # Default maximum quantity of items users can borrow
LOAN_DURATION = 7  # Default days of users in which they can keep their borrowed item(s) with them before marking it as overdue AUTOMATICALLY


class UserRole(Enum):
    USER = 0
    ADMIN = 1


USER_ROLES = (
    (UserRole.USER.name.title(), UserRole.USER.value),
    (UserRole.ADMIN.name.title(), UserRole.ADMIN.value),
)


# UserStatus determines the account's status for users and admin, alike. Users can be set to inactive by admins
class UserStatus(Enum):
    ACTIVE = 0
    INACTIVE = 1


class EquipmentStatus(Enum):
    AVAILABLE = 0
    RESERVED = 1
    ISSUED = 2
    MAINTENANCE = 3
    RETIRED = 4


# ItemStatus determines the catalog item's inventory status depending on its quantity, quality, and borrow request(?)
class CatalogItemStatus(Enum):
    ACTIVE = 0
    ARCHIVE = 1


# RequestStatus is the flow of the borrow request process.
class RequestStatus(Enum):
    PENDING = 0
    APPROVED = 1
    ISSUED = 2
    PARTIALLY_RETURNED = 3
    RETURNED = 4
    REJECTED = 5
    CANCELLED = 6


# User represents a user of the system.
class User(models.Model):
    password = models.CharField(max_length=NAME_LENGTH)
    role = models.IntegerField(choices=USER_ROLES)


# Profile contains the User details such as name and email
class Profile(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.PROTECT
    )  # Protect protects the foreign key object from being deleted as long as they are being referenced by this entity. This serves as extra hardener for the 'no delete' policy.
    first_name = models.CharField(max_length=NAME_LENGTH)
    last_name = models.CharField(max_length=NAME_LENGTH)
    email = models.CharField(max_length=EMAIL_LENGTH)
    contact_number = models.CharField(max_length=CONTACT_NUM_LENGTH)


# Category represents a label for organizing related [CatalogItem]s
class Category(models.Model):
    name = models.CharField(max_length=NAME_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH)


# Represents an item
class CatalogItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    name = models.CharField(max_length=NAME_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH)


class EquipmentUnit(models.Model):
    pass


class BorrowRequest(models.Model):
    pass


class RequestItem(models.Model):
    pass


class UnitAllocation(models.Model):
    pass


class LoanRecord(models.Model):
    pass


class ReturnRecord(models.Model):
    pass


class MaintenanceRecord(models.Model):
    pass


# System settings
class SystemSetting(models.Model):
    max_borrow_quantity = models.IntegerField()
    max_borrow_days = models.IntegerField()

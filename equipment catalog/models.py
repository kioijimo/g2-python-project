from django.db import models


class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    is_archived = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.name


class CatalogItem(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField()

    is_archived = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.name


class EquipmentUnit(models.Model):

    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('RESERVED', 'Reserved'),
        ('ISSUED', 'Issued'),
        ('MAINTENANCE', 'Maintenance'),
        ('RETIRED', 'Retired')
    )

    CONDITION_CHOICES = (
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('DAMAGED', 'Damaged')
    )

    catalog_item = models.ForeignKey(
        CatalogItem,
        on_delete=models.PROTECT
    )

    asset_code = models.CharField(
        max_length=50,
        unique=True
    )

    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES
    )

    acquisition_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='AVAILABLE'
    )

    def __str__(self):
        return self.asset_code
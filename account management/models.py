from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('USER', 'Basic User'),
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='USER'
    )

    contact_no = models.CharField(
        max_length=20,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.username
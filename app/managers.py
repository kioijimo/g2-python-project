from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for the email-based custom user model."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a basic user, ignoring any attempted role/status escalation."""
        extra_fields.pop("role", None)
        extra_fields.pop("status", None)
        extra_fields.pop("is_active", None)
        extra_fields["role"] = self.model.UserRoles.USER
        extra_fields["status"] = self.model.UserStatus.ACTIVE
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create an administrator account."""
        extra_fields.pop("role", None)
        extra_fields.pop("status", None)
        extra_fields.pop("is_active", None)
        extra_fields["role"] = self.model.UserRoles.ADMIN
        extra_fields["status"] = self.model.UserStatus.ACTIVE
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username):
        """Look up users case-insensitively by their email address."""
        return self.get(email__iexact=username)

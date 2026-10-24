import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import User


class Command(BaseCommand):
    help = (
        "Create an administrator account or promote an existing basic user "
        "to administrator."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Email address of the administrator account.",
        )
        parser.add_argument(
            "--promote",
            action="store_true",
            help="Promote an existing basic user instead of creating a new account.",
        )

    def handle(self, *args, **options):
        email = User.objects.normalize_email(options["email"].strip())
        if not email:
            raise CommandError("An email address is required.")

        existing = User.objects.filter(email__iexact=email).first()

        if existing:
            if existing.role == User.UserRoles.ADMIN:
                self.stdout.write(
                    self.style.SUCCESS(f"{email} is already an administrator.")
                )
                return

            if not options["promote"]:
                raise CommandError(
                    f"{email} already exists as a basic user. "
                    "Re-run with --promote to promote this account."
                )

            existing.role = User.UserRoles.ADMIN
            existing.save(update_fields=["role"])
            self.stdout.write(
                self.style.SUCCESS(f"Promoted {email} to administrator.")
            )
            return

        password = self._prompt_password(email)

        with transaction.atomic():
            User.objects.create_superuser(email=email, password=password)

        self.stdout.write(
            self.style.SUCCESS(f"Created administrator account {email}.")
        )

    def _prompt_password(self, email):
        while True:
            try:
                password = getpass.getpass("Password: ")
                confirmation = getpass.getpass("Password (again): ")
            except (EOFError, KeyboardInterrupt):
                raise CommandError("Password input aborted.")

            if password != confirmation:
                self.stderr.write(
                    self.style.ERROR("Passwords do not match. Try again.")
                )
                continue

            try:
                validate_password(password, User(email=email))
            except ValidationError as error:
                for message in error.messages:
                    self.stderr.write(self.style.ERROR(message))
                continue

            return password

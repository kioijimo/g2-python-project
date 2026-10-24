from io import StringIO
from unittest.mock import patch

from django.contrib.auth import SESSION_KEY, authenticate
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile, User

PASSWORD = "Str0ng-Passw0rd!2026"
CONTACT_NUMBER = "09123456789"


def create_basic_user(email="basic@example.com"):
    return User.objects.create_user(email, PASSWORD)


def create_admin_user(email="admin@example.com"):
    return User.objects.create_superuser(email, PASSWORD)


def registration_data(**overrides):
    data = {
        "email": "new@example.com",
        "first_name": "New",
        "last_name": "User",
        "contact_number": CONTACT_NUMBER,
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


class UserManagerTests(TestCase):
    def test_create_user_forces_basic_role_and_active_status(self):
        user = User.objects.create_user(
            "User@Example.COM",
            PASSWORD,
            role=User.UserRoles.ADMIN,
            status=User.UserStatus.INACTIVE,
            is_active=False,
        )

        self.assertEqual(user.email, "User@example.com")
        self.assertEqual(user.role, User.UserRoles.USER)
        self.assertEqual(user.status, User.UserStatus.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_create_superuser_creates_active_admin(self):
        user = User.objects.create_superuser("admin@example.com", PASSWORD)

        self.assertEqual(user.role, User.UserRoles.ADMIN)
        self.assertEqual(user.status, User.UserStatus.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)

    def test_authenticate_uses_email_case_insensitively(self):
        create_basic_user("Basic@Example.com")

        user = authenticate(
            username="basic@example.com",
            password=PASSWORD,
        )

        self.assertIsNotNone(user)
        self.assertEqual(user.email, "Basic@example.com")


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = create_basic_user()
        self.admin = create_admin_user()

    def test_basic_user_login_redirects_to_portal(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": PASSWORD},
        )

        self.assertRedirects(response, reverse("portal:home"))

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_admin_login_redirects_to_manage(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.admin.email, "password": PASSWORD},
        )

        self.assertRedirects(response, reverse("manage"))

    def test_inactive_user_cannot_login(self):
        self.user.status = User.UserStatus.INACTIVE
        self.user.save(update_fields=["status"])

        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": PASSWORD},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_authenticated_login_redirects_by_role(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("login"))

        self.assertRedirects(response, reverse("portal:home"))

    def test_inactive_session_is_cleared_on_login_page(self):
        self.user.status = User.UserStatus.INACTIVE
        self.user.save(update_fields=["status"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_next_and_query_parameters_do_not_change_destination(self):
        response = self.client.post(
            f"{reverse('login')}?role=ADMIN",
            {
                "username": self.user.email,
                "password": PASSWORD,
                "next": reverse("manage"),
            },
        )

        self.assertRedirects(response, reverse("portal:home"))

    def test_get_logout_is_not_allowed(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 405)

    def test_post_logout_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)


class RegistrationTests(TestCase):
    def test_registration_creates_basic_user_and_profile(self):
        response = self.client.post(
            reverse("portal:register"),
            registration_data(),
        )

        self.assertRedirects(response, reverse("portal:home"))

        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, User.UserRoles.USER)
        self.assertEqual(user.status, User.UserStatus.ACTIVE)
        self.assertTrue(user.check_password(PASSWORD))

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.first_name, "New")
        self.assertEqual(profile.last_name, "User")
        self.assertEqual(profile.contact_number, CONTACT_NUMBER)

        self.assertIn(SESSION_KEY, self.client.session)

    def test_registration_ignores_privilege_fields(self):
        data = registration_data(
            role=User.UserRoles.ADMIN,
            status=User.UserStatus.INACTIVE,
            is_active=False,
            is_staff=True,
            is_superuser=True,
        )

        self.client.post(reverse("portal:register"), data)

        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, User.UserRoles.USER)
        self.assertEqual(user.status, User.UserStatus.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_registration_ignores_query_string_role(self):
        self.client.post(
            f"{reverse('portal:register')}?role=ADMIN",
            registration_data(),
        )

        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, User.UserRoles.USER)

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        create_basic_user("taken@example.com")

        response = self.client.post(
            reverse("portal:register"),
            registration_data(email="TAKEN@EXAMPLE.COM"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="taken@example.com").count(), 1)

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("portal:register"),
            registration_data(password2="Different-Passw0rd!2026"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            reverse("portal:register"),
            registration_data(password1="short", password2="short"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())


class AccessControlTests(TestCase):
    def setUp(self):
        self.user = create_basic_user()
        self.admin = create_admin_user()
        self.inactive_user = create_basic_user("inactive@example.com")
        self.inactive_user.status = User.UserStatus.INACTIVE
        self.inactive_user.save(update_fields=["status"])

    def test_portal_requires_login(self):
        response = self.client.get(reverse("portal:home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_manage_requires_login(self):
        response = self.client.get(reverse("manage"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_basic_user_cannot_access_manage(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("manage"))

        self.assertRedirects(response, reverse("portal:home"))

    def test_basic_user_cannot_access_category_management(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("category"))

        self.assertRedirects(response, reverse("portal:home"))

    def test_admin_is_redirected_from_portal(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("portal:home"))

        self.assertRedirects(response, reverse("manage"))

    def test_admin_can_access_manage(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("manage"))

        self.assertEqual(response.status_code, 200)

    def test_inactive_user_is_logged_out(self):
        self.client.force_login(self.inactive_user)

        response = self.client.get(reverse("portal:home"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_inactive_user_cannot_access_manage(self):
        self.client.force_login(self.inactive_user)

        response = self.client.get(reverse("manage"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)


class CsrfTests(TestCase):
    def setUp(self):
        self.user = create_basic_user()
        self.client = Client(enforce_csrf_checks=True)

    def test_login_post_requires_csrf(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": PASSWORD},
        )

        self.assertEqual(response.status_code, 403)

    def test_registration_post_requires_csrf(self):
        response = self.client.post(
            reverse("portal:register"),
            registration_data(),
        )

        self.assertEqual(response.status_code, 403)

    def test_logout_post_requires_csrf(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 403)


class ManageAccountCreationTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.client.force_login(self.admin)

    def test_admin_can_create_basic_account_with_hashed_password(self):
        response = self.client.post(
            reverse("manage"),
            {
                "email": "created@example.com",
                "password": PASSWORD,
                "first_name": "Created",
                "last_name": "User",
                "contact_number": CONTACT_NUMBER,
            },
        )

        self.assertEqual(response.status_code, 200)

        user = User.objects.get(email="created@example.com")
        self.assertEqual(user.role, User.UserRoles.USER)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertTrue(Profile.objects.filter(user=user).exists())


class CreateAdminCommandTests(TestCase):
    def test_command_creates_hashed_admin_account(self):
        with patch(
            "app.management.commands.createadmin.getpass.getpass",
            side_effect=[PASSWORD, PASSWORD],
        ):
            call_command(
                "createadmin",
                email="newadmin@example.com",
                stdout=StringIO(),
            )

        user = User.objects.get(email="newadmin@example.com")
        self.assertEqual(user.role, User.UserRoles.ADMIN)
        self.assertEqual(user.status, User.UserStatus.ACTIVE)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_command_is_idempotent_for_existing_admin(self):
        create_admin_user("existing@example.com")

        output = StringIO()
        call_command("createadmin", email="existing@example.com", stdout=output)

        self.assertIn("already an administrator", output.getvalue())
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

    def test_command_requires_promote_flag_for_existing_basic_user(self):
        user = create_basic_user("promote@example.com")

        with self.assertRaises(CommandError):
            call_command(
                "createadmin",
                email="promote@example.com",
                stdout=StringIO(),
            )

        user.refresh_from_db()
        self.assertEqual(user.role, User.UserRoles.USER)

    def test_command_promotes_existing_basic_user(self):
        user = create_basic_user("promote@example.com")

        call_command(
            "createadmin",
            email="promote@example.com",
            promote=True,
            stdout=StringIO(),
        )

        user.refresh_from_db()
        self.assertEqual(user.role, User.UserRoles.ADMIN)
        self.assertTrue(user.check_password(PASSWORD))

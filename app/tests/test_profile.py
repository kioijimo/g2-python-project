from django.test import TestCase
from django.urls import reverse

from app.models import Profile, User
from app.tests.helpers import CONTACT_NUMBER, create_admin, create_user


class ProfileTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_profile_page_shows_email_and_editable_fields(self):
        response = self.client.get(reverse("portal:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.email)
        self.assertContains(response, 'name="first_name"')
        self.assertContains(response, 'name="last_name"')
        self.assertContains(response, 'name="contact_number"')
        self.assertNotContains(response, 'name="email"')

    def test_profile_update_changes_only_allowed_fields(self):
        response = self.client.post(
            reverse("portal:profile"),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "contact_number": "09987654321",
                "email": "hijacked@example.com",
                "role": User.UserRoles.ADMIN,
                "status": User.UserStatus.INACTIVE,
            },
        )

        self.assertRedirects(response, reverse("portal:profile"))

        self.user.refresh_from_db()
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.first_name, "Updated")
        self.assertEqual(profile.last_name, "Name")
        self.assertEqual(profile.contact_number, "09987654321")
        self.assertEqual(self.user.email, "basic@example.com")
        self.assertEqual(self.user.role, User.UserRoles.USER)
        self.assertEqual(self.user.status, User.UserStatus.ACTIVE)

    def test_profile_update_rejects_invalid_contact_number(self):
        response = self.client.post(
            reverse("portal:profile"),
            {
                "first_name": "Basic",
                "last_name": "User",
                "contact_number": "12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid phone number.")

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.contact_number, CONTACT_NUMBER)

    def test_profile_is_created_for_user_without_one(self):
        user = create_user("noprofile@example.com", with_profile=False)
        self.client.force_login(user)

        response = self.client.post(
            reverse("portal:profile"),
            {
                "first_name": "New",
                "last_name": "Profile",
                "contact_number": "09111111111",
            },
        )

        self.assertRedirects(response, reverse("portal:profile"))
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_admin_cannot_access_profile(self):
        admin = create_admin()
        self.client.force_login(admin)

        response = self.client.get(reverse("portal:profile"))

        self.assertRedirects(response, reverse("manage"))

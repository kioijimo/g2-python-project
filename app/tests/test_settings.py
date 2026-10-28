from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import AuditLog, BorrowRequest, SystemSetting, User
from app.tests.helpers import create_admin, create_catalog_item, create_units, create_user


class SettingsTests(TestCase):
    def setUp(self):
        self.admin = create_admin("admin_settings@example.com")
        self.user = create_user("student_settings@example.com")
        self.setting, _ = SystemSetting.objects.get_or_create(
            id=1,
            defaults={"max_borrow_days": 7, "max_borrow_quantity": 3},
        )
        self.setting.max_borrow_days = 7
        self.setting.max_borrow_quantity = 3
        self.setting.save()

    def test_settings_page_renders_both_fields(self):
        """Settings page must display both 'Max borrow days' and 'Max quantity' fields."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)

        # Confirm both field inputs are present
        self.assertContains(response, 'name="max_borrow_days"')
        self.assertContains(response, 'name="max_borrow_quantity"')

        # Confirm labels/help text
        self.assertContains(response, "Max borrow days")
        self.assertContains(response, "Max quantity")

    def test_admin_can_update_both_settings(self):
        """Admin can save new values for both max borrow days and max borrow quantity."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("settings"),
            {
                "max_borrow_days": 10,
                "max_borrow_quantity": 5,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.setting.refresh_from_db()
        self.assertEqual(self.setting.max_borrow_days, 10)
        self.assertEqual(self.setting.max_borrow_quantity, 5)

        # Verify flash messages
        self.assertContains(response, "Updated MAX_BORROW_QUANTITY from 3 to 5")
        self.assertContains(response, "Updated MAX_BORROW_DAYS from 7 to 10")

        # Verify AuditLog
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                action__icontains="Max Quantity: 5, Max Borrow Days: 10",
            ).exists()
        )

    def test_validation_rejects_negative_or_zero_values(self):
        """Values below 1 must be rejected by form validation."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("settings"),
            {
                "max_borrow_days": 0,
                "max_borrow_quantity": -2,
            },
        )
        self.assertEqual(response.status_code, 200)

        self.setting.refresh_from_db()
        self.assertEqual(self.setting.max_borrow_days, 7)
        self.assertEqual(self.setting.max_borrow_quantity, 3)

    def test_non_admin_cannot_access_settings(self):
        """Only admins can view or modify system settings."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("portal:home"), response.url)

        self.client.logout()
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_settings_applied_to_new_requests(self):
        """Both max borrow days and max borrow quantity must be enforced on new requests."""
        # Configure settings: max 2 units, max 4 days
        self.setting.max_borrow_quantity = 2
        self.setting.max_borrow_days = 4
        self.setting.save()

        item = create_catalog_item(name="Projector")
        create_units(item, count=10)

        self.client.force_login(self.user)

        # 1. Reject quantity above configured max (requesting 3 when max is 2)
        due_date = (timezone.localdate() + timedelta(days=2)).isoformat()
        response = self.client.post(
            reverse("portal:request_create"),
            {
                "purpose": "Group presentation",
                "desired_return_date": due_date,
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "3",
                "items-0-catalog_item": str(item.pk),
                "items-0-quantity": "3",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.filter(user=self.user).exists())
        self.assertContains(response, "Maximum 2 unit(s) per item.")

        # 2. Reject return date beyond configured max days (requesting 5 days when max is 4)
        due_date_beyond = (timezone.localdate() + timedelta(days=5)).isoformat()
        response = self.client.post(
            reverse("portal:request_create"),
            {
                "purpose": "Group presentation",
                "desired_return_date": due_date_beyond,
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "3",
                "items-0-catalog_item": str(item.pk),
                "items-0-quantity": "2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.filter(user=self.user).exists())

        # 3. Accept valid request within both limits (2 units, 4 days)
        valid_due_date = (timezone.localdate() + timedelta(days=4)).isoformat()
        response = self.client.post(
            reverse("portal:request_create"),
            {
                "purpose": "Group presentation",
                "desired_return_date": valid_due_date,
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "3",
                "items-0-catalog_item": str(item.pk),
                "items-0-quantity": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BorrowRequest.objects.filter(user=self.user).exists())

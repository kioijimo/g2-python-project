from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import AuditLog, BorrowRequest, Profile, User
from app.tests.helpers import (
    create_admin,
    create_borrow_request,
    create_catalog_item,
    create_request_item,
    create_user,
)


class ManageAccountTests(TestCase):
    def setUp(self):
        self.admin = create_admin("admin_test@example.com")
        self.user1 = create_user("alice@example.com")
        self.user2 = create_user("bob@example.com")

        # Give user1 and user2 distinct profile names
        self.user1.profile.first_name = "Alice"
        self.user1.profile.last_name = "Smith"
        self.user1.profile.contact_number = "09111111111"
        self.user1.profile.save()

        self.user2.profile.first_name = "Bob"
        self.user2.profile.last_name = "Jones"
        self.user2.profile.contact_number = "09222222222"
        self.user2.profile.save()

    def test_anonymous_user_redirected_to_login(self):
        url = reverse("account_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_basic_user_cannot_access_account_list(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse("account_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("portal:home"), response.url)

    def test_admin_can_view_account_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "manage/account_list.html")

        # Check content includes users
        self.assertContains(response, "alice@example.com")
        self.assertContains(response, "Alice Smith")
        self.assertContains(response, "bob@example.com")
        self.assertContains(response, "Bob Jones")
        self.assertContains(response, "admin_test@example.com")
        self.assertContains(response, "Total accounts:")

    def test_search_users_by_email(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"), {"q": "alice"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice@example.com")
        self.assertNotContains(response, "bob@example.com")

    def test_search_users_by_name(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"), {"q": "Jones"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bob@example.com")
        self.assertNotContains(response, "alice@example.com")

    def test_search_users_by_contact_number(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"), {"q": "09111111111"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice@example.com")
        self.assertNotContains(response, "bob@example.com")

    def test_search_users_no_matches(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"), {"q": "nonexistent_query"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No accounts found matching "nonexistent_query"')

    def test_deactivate_and_activate_user(self):
        self.client.force_login(self.admin)

        # Deactivate user1
        deactivate_url = reverse("deactivate_user", args=[self.user1.pk])
        response = self.client.post(deactivate_url)
        self.assertRedirects(response, reverse("account_list"))

        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_active)
        self.assertEqual(self.user1.status, User.UserStatus.INACTIVE)

        # Check AuditLog
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin, action__icontains="Deactivated user account"
            ).exists()
        )

        # Activate user1
        activate_url = reverse("activate_user", args=[self.user1.pk])
        response = self.client.post(activate_url)
        self.assertRedirects(response, reverse("account_list"))

        self.user1.refresh_from_db()
        self.assertTrue(self.user1.is_active)
        self.assertEqual(self.user1.status, User.UserStatus.ACTIVE)

        # Check AuditLog
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin, action__icontains="Activated user account"
            ).exists()
        )

    def test_get_activate_and_deactivate_also_works(self):
        self.client.force_login(self.admin)

        # Deactivate via GET
        response = self.client.get(reverse("deactivate_user", args=[self.user2.pk]))
        self.assertRedirects(response, reverse("account_list"))
        self.user2.refresh_from_db()
        self.assertFalse(self.user2.is_active)

        # Activate via GET
        response = self.client.get(reverse("activate_user", args=[self.user2.pk]))
        self.assertRedirects(response, reverse("account_list"))
        self.user2.refresh_from_db()
        self.assertTrue(self.user2.is_active)

    def test_admin_cannot_deactivate_themselves(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("deactivate_user", args=[self.admin.pk]))
        self.assertRedirects(response, reverse("account_list"))

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_view_borrowing_history(self):
        self.client.force_login(self.admin)

        # Create borrow requests for alice
        item = create_catalog_item(name="DSLR Camera")
        req1 = create_borrow_request(
            user=self.user1,
            purpose="Photography Project",
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=timezone.now() + timedelta(days=2),
        )
        create_request_item(req1, item, quantity=1)

        req2 = create_borrow_request(
            user=self.user1,
            purpose="Overdue Project",
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=timezone.now() - timedelta(days=2),
        )
        create_request_item(req2, item, quantity=1)

        req3 = create_borrow_request(
            user=self.user1,
            purpose="Returned Assignment",
            status=BorrowRequest.BorrowRequestStatus.RETURNED,
            due_at=timezone.now() - timedelta(days=5),
        )
        create_request_item(req3, item, quantity=2)

        history_url = reverse("user_borrowing_history", args=[self.user1.pk])
        response = self.client.get(history_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "manage/user_borrowing_history.html")

        # Verify user information is displayed
        self.assertContains(response, "Alice Smith")
        self.assertContains(response, "alice@example.com")
        self.assertContains(response, "09111111111")

        # Verify requests are displayed
        self.assertContains(response, "Photography Project")
        self.assertContains(response, "Overdue Project")
        self.assertContains(response, "Returned Assignment")
        self.assertContains(response, "DSLR Camera")

        # Check stats in context
        stats = response.context["stats"]
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["active"], 2)
        self.assertEqual(stats["returned"], 1)
        self.assertEqual(stats["overdue"], 1)

    def test_view_borrowing_history_empty(self):
        self.client.force_login(self.admin)
        history_url = reverse("user_borrowing_history", args=[self.user2.pk])
        response = self.client.get(history_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No borrow requests found for this user.")
        stats = response.context["stats"]
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["active"], 0)
        self.assertEqual(stats["returned"], 0)
        self.assertEqual(stats["overdue"], 0)

    def test_admin_navbar_contains_accounts_link(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("account_list"))
        self.assertContains(response, "Accounts")
        self.assertContains(response, 'aria-current="page"')

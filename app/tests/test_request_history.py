from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import (
    BorrowRequest,
    EquipmentUnit,
    UnitAllocation,
)
from app.tests.helpers import (
    create_admin,
    create_borrow_request as create_request,
    create_catalog_item,
    create_category,
    create_request_item,
    create_units,
    create_user,
)


class RequestHistoryTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user("other@example.com")
        self.client.force_login(self.user)
        self.category = create_category("Computing")
        self.item = create_catalog_item("Laptop", category=self.category)

    def make_request(self, user=None, status=None, due_at=None, purpose="Class project"):
        kwargs = {"user": user or self.user, "purpose": purpose}
        if status is not None:
            kwargs["status"] = status
        if due_at is not None:
            kwargs["due_at"] = due_at
        return create_request(**kwargs)

    def end_of_day(self, date):
        return timezone.make_aware(
            datetime.combine(date, time.max),
            timezone.get_current_timezone(),
        )

    def test_list_shows_only_current_users_requests(self):
        own_request = self.make_request(purpose="Own presentation request")
        create_request_item(own_request, self.item)
        self.make_request(self.other_user, purpose="Other private request")

        response = self.client.get(reverse("portal:request_list"))

        self.assertContains(response, "Own presentation request")
        self.assertNotContains(response, "Other private request")
        self.assertContains(response, f"#{own_request.pk}")
        self.assertContains(response, "Pending")

    def test_list_shows_empty_state(self):
        response = self.client.get(reverse("portal:request_list"))

        self.assertContains(response, "No requests yet")

    def test_detail_shows_request_items_and_status(self):
        borrow_request = self.make_request()
        create_request_item(borrow_request, self.item, quantity=2)

        response = self.client.get(
            reverse("portal:request_detail", args=[borrow_request.pk])
        )

        self.assertContains(response, f"Request #{borrow_request.pk}")
        self.assertContains(response, "Class project")
        self.assertContains(response, self.item.name)
        self.assertContains(response, self.category.name)
        self.assertContains(response, "Pending")
        self.assertContains(response, "Cancel request")
        self.assertContains(response, "Not assigned yet")

    def test_detail_shows_assigned_units(self):
        borrow_request = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.APPROVED
        )
        request_item = create_request_item(borrow_request, self.item, quantity=2)
        units = create_units(
            self.item,
            count=2,
            inventory_status=EquipmentUnit.EquipmentStatus.RESERVED,
        )
        for unit in units:
            UnitAllocation.objects.create(
                request_item=request_item,
                equipment_unit=unit,
                status=UnitAllocation.UnitAllocationStatus.PENDING,
                allocated_at=timezone.now(),
            )

        response = self.client.get(
            reverse("portal:request_detail", args=[borrow_request.pk])
        )

        for unit in units:
            self.assertContains(response, unit.asset_code)
        self.assertContains(response, "Approved")

    def test_detail_shows_partially_returned_status(self):
        borrow_request = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED
        )

        response = self.client.get(
            reverse("portal:request_detail", args=[borrow_request.pk])
        )

        self.assertContains(response, "Partially Returned")
        self.assertContains(response, "Return the remaining units")
        self.assertContains(response, "border-teal-200 bg-teal-50 text-teal-700")
        self.assertContains(response, "whitespace-nowrap")
        self.assertNotContains(response, "border-amber-200 bg-amber-50 text-amber-700")

    def test_detail_cannot_view_another_users_request(self):
        other_request = self.make_request(self.other_user)

        response = self.client.get(
            reverse("portal:request_detail", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_detail_shows_overdue_days_for_issued_request(self):
        due_at = self.end_of_day(timezone.localdate() - timedelta(days=3))
        borrow_request = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=due_at,
        )

        response = self.client.get(
            reverse("portal:request_detail", args=[borrow_request.pk])
        )

        self.assertContains(response, "overdue by 3 days")

    def test_overdue_days_are_zero_on_or_before_due_date(self):
        today = timezone.localdate()
        issued_today = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=self.end_of_day(today),
        )
        issued_future = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=self.end_of_day(today + timedelta(days=2)),
        )

        self.assertEqual(issued_today.overdue_days(), 0)
        self.assertEqual(issued_future.overdue_days(), 0)

    def test_overdue_days_count_calendar_days_for_partially_returned(self):
        due_at = self.end_of_day(timezone.localdate() - timedelta(days=2))
        borrow_request = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
            due_at=due_at,
        )

        self.assertEqual(borrow_request.overdue_days(), 2)

    def test_overdue_days_are_zero_for_unissued_requests(self):
        due_at = self.end_of_day(timezone.localdate() - timedelta(days=4))
        borrow_request = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.PENDING,
            due_at=due_at,
        )

        response = self.client.get(
            reverse("portal:request_detail", args=[borrow_request.pk])
        )

        self.assertEqual(borrow_request.overdue_days(), 0)
        self.assertNotContains(response, "overdue by")

    def test_cancels_pending_request(self):
        borrow_request = self.make_request()

        response = self.client.post(
            reverse("portal:request_cancel", args=[borrow_request.pk]),
            follow=True,
        )

        self.assertContains(response, "Borrow request cancelled successfully.")
        borrow_request.refresh_from_db()
        self.assertEqual(
            borrow_request.status,
            BorrowRequest.BorrowRequestStatus.CANCELLED,
        )

    def test_cancelling_approved_request_releases_reserved_units(self):
        borrow_request = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.APPROVED
        )
        request_item = create_request_item(borrow_request, self.item, quantity=2)
        units = create_units(
            self.item,
            count=2,
            inventory_status=EquipmentUnit.EquipmentStatus.RESERVED,
        )
        allocations = [
            UnitAllocation.objects.create(
                request_item=request_item,
                equipment_unit=unit,
                status=UnitAllocation.UnitAllocationStatus.PENDING,
                allocated_at=timezone.now(),
            )
            for unit in units
        ]

        self.client.post(
            reverse("portal:request_cancel", args=[borrow_request.pk])
        )

        borrow_request.refresh_from_db()
        self.assertEqual(
            borrow_request.status,
            BorrowRequest.BorrowRequestStatus.CANCELLED,
        )
        for unit in units:
            unit.refresh_from_db()
            self.assertEqual(
                unit.inventory_status,
                EquipmentUnit.EquipmentStatus.AVAILABLE,
            )
        for allocation in allocations:
            allocation.refresh_from_db()
            self.assertEqual(
                allocation.status,
                UnitAllocation.UnitAllocationStatus.CANCELLED,
            )

    def test_cannot_cancel_issued_request(self):
        borrow_request = self.make_request(
            status=BorrowRequest.BorrowRequestStatus.ISSUED
        )

        response = self.client.post(
            reverse("portal:request_cancel", args=[borrow_request.pk]),
            follow=True,
        )

        self.assertContains(response, "can no longer be cancelled")
        borrow_request.refresh_from_db()
        self.assertEqual(
            borrow_request.status,
            BorrowRequest.BorrowRequestStatus.ISSUED,
        )

    def test_cannot_cancel_another_users_request(self):
        other_request = self.make_request(self.other_user)

        response = self.client.post(
            reverse("portal:request_cancel", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)
        other_request.refresh_from_db()
        self.assertEqual(
            other_request.status,
            BorrowRequest.BorrowRequestStatus.PENDING,
        )

    def test_cancel_requires_post(self):
        borrow_request = self.make_request()

        response = self.client.get(
            reverse("portal:request_cancel", args=[borrow_request.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_admin_cannot_access_request_history(self):
        admin = create_admin()
        self.client.force_login(admin)

        response = self.client.get(reverse("portal:request_list"))

        self.assertRedirects(response, reverse("manage"))

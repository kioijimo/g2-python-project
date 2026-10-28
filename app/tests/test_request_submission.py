from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import (
    BorrowRequest,
    CatalogItem,
    RequestItem,
    UnitAllocation,
)
from app.forms import BorrowRequestItemForm
from app.tests.helpers import (
    create_borrow_request,
    create_catalog_item,
    create_category,
    create_request_item,
    create_settings,
    create_units,
    create_user,
)


class RequestSubmissionTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)
        self.category = create_category("Computing")
        self.settings = create_settings(max_borrow_days=7)

    def make_item(self, name, units=1):
        item = create_catalog_item(name, category=self.category)
        if units:
            create_units(item, count=units)
        return item

    def due_date(self, days=1):
        return (timezone.localdate() + timedelta(days=days)).isoformat()

    def request_data(self, items, total_forms=3):
        data = {
            "purpose": "Class project",
            "desired_return_date": self.due_date(),
            "items-TOTAL_FORMS": str(total_forms),
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "3",
        }

        for index in range(total_forms):
            item = items[index] if index < len(items) else None
            data[f"items-{index}-id"] = ""
            data[f"items-{index}-catalog_item"] = (
                str(item[0].pk) if item else ""
            )
            data[f"items-{index}-quantity"] = str(item[1]) if item else ""

        return data

    def test_creates_single_item_request(self):
        item = self.make_item("Laptop")

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 1)]),
        )

        borrow_request = BorrowRequest.objects.get(user=self.user)
        self.assertRedirects(
            response,
            reverse("portal:request_detail", args=[borrow_request.pk]),
        )
        self.assertEqual(
            borrow_request.status,
            BorrowRequest.BorrowRequestStatus.PENDING,
        )
        self.assertEqual(borrow_request.purpose, "Class project")

        request_item = borrow_request.items.get()
        self.assertEqual(request_item.catalog_item, item)
        self.assertEqual(request_item.quantity, 1)
        self.assertFalse(UnitAllocation.objects.exists())

    def test_stores_due_at_at_end_of_day(self):
        item = self.make_item("Laptop")

        self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 1)]),
        )

        borrow_request = BorrowRequest.objects.get(user=self.user)
        local_due = timezone.localtime(borrow_request.due_at)

        self.assertEqual(local_due.date(), timezone.localdate() + timedelta(days=1))
        self.assertEqual(local_due.time().replace(microsecond=0), time(23, 59, 59))

    def test_creates_three_item_request(self):
        items = [
            self.make_item("Laptop"),
            self.make_item("Projector"),
            self.make_item("Speaker"),
        ]

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 1) for item in items]),
        )

        self.assertEqual(response.status_code, 302)
        borrow_request = BorrowRequest.objects.get(user=self.user)
        self.assertEqual(borrow_request.items.count(), 3)

    def test_rejects_duplicate_catalog_items(self):
        item = self.make_item("Laptop")

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 1), (item, 1)]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())
        self.assertContains(response, "duplicate")

    def test_invalid_row_prevents_partial_request(self):
        available = self.make_item("Laptop")
        unavailable = self.make_item("Projector", units=0)

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(available, 1), (unavailable, 1)]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())
        self.assertFalse(RequestItem.objects.exists())

    def test_requires_at_least_one_item(self):
        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())
        self.assertContains(response, "Add at least one catalog item")

    def test_rejects_more_than_three_rows(self):
        items = [
            self.make_item("Laptop"),
            self.make_item("Projector"),
            self.make_item("Speaker"),
            self.make_item("Tablet"),
        ]

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 1) for item in items], total_forms=4),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())

    def test_rejects_quantity_above_configured_maximum(self):
        item = self.make_item("Laptop", units=5)

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 4)]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())
        self.assertContains(response, f"Maximum {self.settings.max_borrow_quantity} unit")

    def test_respects_configured_max_borrow_quantity(self):
        self.settings.max_borrow_quantity = 5
        self.settings.save(update_fields=["max_borrow_quantity"])
        item = self.make_item("Laptop", units=5)

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 5)]),
        )

        self.assertEqual(response.status_code, 302)
        borrow_request = BorrowRequest.objects.get(user=self.user)
        self.assertEqual(borrow_request.items.get().quantity, 5)

    def test_quantity_widget_has_configured_maximum(self):
        form = BorrowRequestItemForm()

        self.assertEqual(
            form.fields["quantity"].widget.attrs.get("max"),
            self.settings.max_borrow_quantity,
        )

    def test_rejects_quantity_above_available_units(self):
        item = self.make_item("Laptop", units=1)

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 2)]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())
        self.assertContains(response, "Only 1 unit")

    def test_pending_requests_reduce_requestable_quantity(self):
        item = self.make_item("Laptop", units=3)
        other_user = create_user("other@example.com")
        pending = create_borrow_request(user=other_user)
        create_request_item(pending, item, quantity=2)

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 2)]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.filter(user=self.user).exists())
        self.assertContains(response, "Only 1 unit")

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 1)]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(BorrowRequest.objects.filter(user=self.user).exists())

    def test_cancelled_pending_request_restores_requestable_quantity(self):
        item = self.make_item("Laptop", units=3)
        other_user = create_user("other@example.com")
        pending = create_borrow_request(user=other_user)
        create_request_item(pending, item, quantity=2)

        pending.status = BorrowRequest.BorrowRequestStatus.CANCELLED
        pending.save(update_fields=["status"])

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 3)]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(BorrowRequest.objects.filter(user=self.user).exists())

    def test_rejects_due_date_today(self):
        item = self.make_item("Laptop")

        data = self.request_data([(item, 1)])
        data["desired_return_date"] = self.due_date(0)

        response = self.client.post(reverse("portal:request_create"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())

    def test_accepts_due_date_on_maximum_day(self):
        item = self.make_item("Laptop")

        data = self.request_data([(item, 1)])
        data["desired_return_date"] = self.due_date(7)

        response = self.client.post(reverse("portal:request_create"), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(BorrowRequest.objects.exists())

    def test_rejects_due_date_beyond_maximum(self):
        item = self.make_item("Laptop")

        data = self.request_data([(item, 1)])
        data["desired_return_date"] = self.due_date(8)

        response = self.client.post(reverse("portal:request_create"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())

    def test_respects_configured_max_borrow_days(self):
        self.settings.max_borrow_days = 5
        self.settings.save(update_fields=["max_borrow_days"])
        item = self.make_item("Laptop")

        data = self.request_data([(item, 1)])
        data["desired_return_date"] = self.due_date(6)

        response = self.client.post(reverse("portal:request_create"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())

    def test_rejects_archived_item(self):
        item = self.make_item("Laptop")
        item.status = CatalogItem.CatalogItemStatus.ARCHIVED
        item.save(update_fields=["status"])

        response = self.client.post(
            reverse("portal:request_create"),
            self.request_data([(item, 1)]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BorrowRequest.objects.exists())

    def test_prefills_item_from_query_string(self):
        item = self.make_item("Laptop")

        response = self.client.get(
            f"{reverse('portal:request_create')}?item={item.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{item.pk}" selected')

    def test_form_renders_three_rows_and_management_form(self):
        response = self.client.get(reverse("portal:request_create"))

        self.assertContains(response, "items-TOTAL_FORMS")
        self.assertEqual(
            response.content.decode().count("data-show-row="),
            3,
        )

    def test_form_options_expose_requestable_availability(self):
        item = self.make_item("Laptop", units=2)

        response = self.client.get(reverse("portal:request_create"))

        self.assertContains(response, 'data-available="2"')
        self.assertContains(response, item.name)

    @patch(
        "app.services.borrowing.RequestItem.objects.bulk_create",
        side_effect=RuntimeError("simulated failure"),
    )
    def test_failed_item_save_rolls_back_request(self, mocked_bulk_create):
        item = self.make_item("Laptop")

        with self.assertRaises(RuntimeError):
            self.client.post(
                reverse("portal:request_create"),
                self.request_data([(item, 1)]),
            )

        self.assertFalse(BorrowRequest.objects.exists())
        self.assertFalse(RequestItem.objects.exists())

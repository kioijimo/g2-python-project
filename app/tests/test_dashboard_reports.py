import csv
import io
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import (
    BorrowRequest,
    CatalogItem,
    Category,
    EquipmentUnit,
    LoanRecord,
    RequestItem,
    UnitAllocation,
)
from app.tests.helpers import create_admin, create_user


class DashboardReportTests(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.client.force_login(self.admin)
        self.user = create_user(email="student1@example.com")

        # Create category, catalog item, and equipment unit
        self.category = Category.objects.create(name="Laptops", status=Category.CategoryStatus.ACTIVE)
        self.catalog_item = CatalogItem.objects.create(
            category=self.category,
            name="ThinkPad T14",
            description="Engineering laptop",
            status=CatalogItem.CatalogItemStatus.ACTIVE,
        )
        self.unit1 = EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-0099",
            inventory_status=EquipmentUnit.EquipmentStatus.ISSUED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )

        # Active Loan (Issued)
        self.active_request = BorrowRequest.objects.create(
            user=self.user,
            purpose="Lab project",
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=timezone.now() + timedelta(days=5),
        )
        req_item = RequestItem.objects.create(
            borrow_request=self.active_request,
            catalog_item=self.catalog_item,
            quantity=1,
        )
        UnitAllocation.objects.create(
            request_item=req_item,
            equipment_unit=self.unit1,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
            allocated_at=timezone.now(),
        )
        LoanRecord.objects.create(
            borrow_request=self.active_request,
            user=self.admin,
            released_at=timezone.now(),
        )

        # Overdue Loan
        self.unit2 = EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-0100",
            inventory_status=EquipmentUnit.EquipmentStatus.ISSUED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        self.overdue_request = BorrowRequest.objects.create(
            user=self.user,
            purpose="Overdue testing",
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=timezone.now() - timedelta(days=3),
        )
        req_item_overdue = RequestItem.objects.create(
            borrow_request=self.overdue_request,
            catalog_item=self.catalog_item,
            quantity=1,
        )
        UnitAllocation.objects.create(
            request_item=req_item_overdue,
            equipment_unit=self.unit2,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
            allocated_at=timezone.now() - timedelta(days=10),
        )
        LoanRecord.objects.create(
            borrow_request=self.overdue_request,
            user=self.admin,
            released_at=timezone.now() - timedelta(days=10),
        )

    def test_dashboard_renders_reports_section(self):
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reports & Analytics")
        self.assertContains(response, "Loan Report")
        self.assertContains(response, "Overdue Report")
        self.assertIn("reports", response.context)
        self.assertEqual(response.context["reports"]["loans_count"], 2)
        self.assertEqual(response.context["reports"]["overdue_count"], 1)

    def test_dashboard_loans_filter_by_date(self):
        today = timezone.localdate().strftime("%Y-%m-%d")
        tomorrow = (timezone.localdate() + timedelta(days=1)).strftime("%Y-%m-%d")

        response = self.client.get(
            reverse("manage"),
            {"report_tab": "loans", "loan_from": today, "loan_to": tomorrow},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AST-0099")

    def test_dashboard_overdue_tab_view(self):
        response = self.client.get(reverse("manage"), {"report_tab": "overdue"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["reports"]["active_tab"], "overdue")
        self.assertContains(response, "AST-0100")
        self.assertContains(response, "days late")

    def test_export_loans_csv(self):
        response = self.client.get(reverse("manage"), {"export": "loans_csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        self.assertGreaterEqual(len(rows), 2)
        headers = rows[0]
        self.assertIn("Loan ID", headers)
        self.assertIn("Borrower Email", headers)
        self.assertIn("Allocated Asset Codes", headers)

        # Confirm student1 data is exported
        csv_text = response.content.decode()
        self.assertIn("student1@example.com", csv_text)
        self.assertIn("AST-0099", csv_text)

    def test_export_overdue_csv(self):
        response = self.client.get(reverse("manage"), {"export": "overdue_csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        self.assertGreaterEqual(len(rows), 2)
        headers = rows[0]
        self.assertIn("Loan ID", headers)
        self.assertIn("Days Overdue", headers)
        self.assertIn("Borrower Email", headers)

        csv_text = response.content.decode()
        self.assertIn("student1@example.com", csv_text)
        self.assertIn("AST-0100", csv_text)

    def test_all_manage_routes_return_200(self):
        routes = [
            reverse("manage"),
            reverse("catalogs"),
            reverse("borrow_requests"),
            reverse("loans_list"),
            reverse("manage_returns"),
            reverse("manage_maintenance"),
            reverse("audit"),
            reverse("settings"),
        ]
        for url in routes:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200)

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

    def test_dashboard_available_units_stat_excludes_issued_reserved_maintenance_units(self):
        """Dashboard 'available_units' stat must only count units that are AVAILABLE and in FINE condition."""
        # setUp created 2 units (unit1 and unit2), both ISSUED with condition=FINE.
        # Neither should be counted as available.
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["available_units"], 0)

        # 1. Create a unit that is AVAILABLE and FINE -> available_units should be 1
        unit_avail_fine = EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-AVAIL-1",
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 1)

        # 2. Create a unit that is AVAILABLE but DAMAGED -> should NOT increment
        EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-AVAIL-DAMAGED",
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
            condition=EquipmentUnit.EquipmentCondition.DAMAGED,
        )
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 1)

        # 3. Create a unit that is RESERVED with condition=FINE -> should NOT increment
        EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-RESERVED-FINE",
            inventory_status=EquipmentUnit.EquipmentStatus.RESERVED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 1)

        # 4. Create a unit that is in MAINTENANCE with condition=FINE -> should NOT increment
        EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-MAINT-FINE",
            inventory_status=EquipmentUnit.EquipmentStatus.MAINTENANCE,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 1)

        # 5. Create a unit that is RETIRED with condition=FINE -> should NOT increment
        EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-RETIRED-FINE",
            inventory_status=EquipmentUnit.EquipmentStatus.RETIRED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 1)

    def test_dashboard_available_units_updates_after_transactions(self):
        """Dashboard 'available_units' dynamically reflects status transitions."""
        unit = EquipmentUnit.objects.create(
            catalog_item=self.catalog_item,
            asset_code="AST-TX-1",
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 1)

        # Issue the unit -> available_units drops to 0
        unit.inventory_status = EquipmentUnit.EquipmentStatus.ISSUED
        unit.save()
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 0)

        # Return the unit in FINE condition -> available_units returns to 1
        unit.inventory_status = EquipmentUnit.EquipmentStatus.AVAILABLE
        unit.condition = EquipmentUnit.EquipmentCondition.FINE
        unit.save()
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 1)

        # Move to MAINTENANCE -> available_units drops back to 0
        unit.inventory_status = EquipmentUnit.EquipmentStatus.MAINTENANCE
        unit.condition = EquipmentUnit.EquipmentCondition.DAMAGED
        unit.save()
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.context["stats"]["available_units"], 0)

    def test_returns_manage_layout_and_active_request_details_table(self):
        """Returns management page renders Process Unit Return beside an initially empty Borrow Request Details table and Recent Unit Return Logs below."""
        response = self.client.get(reverse("manage_returns"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        # Verify sections appear in the expected order:
        # 1. Process Unit Return
        # 2. Borrow Request Details (initially empty table beside it)
        # 3. Recent Unit Return Logs (below)
        pos_process = html.index("Process Unit Return")
        pos_details = html.index("Borrow Request Details")
        pos_recent_logs = html.index("Recent Unit Return Logs")
        self.assertLess(pos_process, pos_details)
        self.assertLess(pos_details, pos_recent_logs)

        # Verify initially empty state row is present
        self.assertContains(
            response,
            "Select an active borrow request to view its allocated units, asset codes, and details.",
        )

        # Verify active borrow requests have their details and allocated units rendered for selection
        self.assertContains(
            response, f'data-request-rows="{self.active_request.id}"'
        )
        self.assertContains(response, f"#REQ-{self.active_request.id}")
        self.assertContains(response, "ThinkPad T14")
        self.assertContains(response, "Laptops")
        self.assertContains(response, "AST-0099")
        self.assertContains(response, "AST-0100")
        self.assertContains(response, "student1@example.com")
        self.assertContains(response, "Lab project")
        self.assertContains(response, "Overdue testing")

    def test_dashboard_category_usage_includes_counts_and_percentages_and_tooltip(self):
        """Equipment Category Usage chart data and tooltip include both unit counts and percentages."""
        audio_cat = Category.objects.create(name="Audio", status=Category.CategoryStatus.ACTIVE)
        mic_item = CatalogItem.objects.create(
            category=audio_cat,
            name="Studio Mic",
            description="Condenser microphone",
            status=CatalogItem.CatalogItemStatus.ACTIVE,
        )
        RequestItem.objects.create(
            borrow_request=self.active_request,
            catalog_item=mic_item,
            quantity=2,
        )

        response = self.client.get(reverse("manage"))
        self.assertEqual(response.status_code, 200)
        category_usage = response.context["category_usage"]
        self.assertEqual(category_usage["labels"], ["Laptops", "Audio"])
        self.assertEqual(category_usage["counts"], [2, 2])
        self.assertEqual(category_usage["percentages"], [50.0, 50.0])
        self.assertContains(
            response,
            "return ` ${context.label}: ${count} ${unitLabel} (${pct}%)`;",
        )

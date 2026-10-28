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
    MaintenanceRecord,
    RequestItem,
    ReturnRecord,
    UnitAllocation,
)
from app.tests.helpers import create_admin, create_user


class ReturnsManagementTests(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.client.force_login(self.admin)
        self.beatrice = create_user(email="beatrice.mendoza@example.com")

        self.cat_it = Category.objects.create(
            name="IT & Computing",
            status=Category.CategoryStatus.ACTIVE,
        )
        self.cat_av = Category.objects.create(
            name="Audio-Visual Equipment",
            status=Category.CategoryStatus.ACTIVE,
        )
        self.cat_lab = Category.objects.create(
            name="Laboratory & Electronics",
            status=Category.CategoryStatus.ACTIVE,
        )

        self.item_laptop = CatalogItem.objects.create(
            category=self.cat_it,
            name='Dell Latitude Laptop 14"',
            description="Portable workstation",
            status=CatalogItem.CatalogItemStatus.ACTIVE,
        )
        self.item_cam = CatalogItem.objects.create(
            category=self.cat_av,
            name="Sony 4K Handheld Camcorder",
            description="4K video camera",
            status=CatalogItem.CatalogItemStatus.ACTIVE,
        )
        self.item_dmm = CatalogItem.objects.create(
            category=self.cat_lab,
            name="Fluke Digital Multimeter",
            description="True-RMS multimeter",
            status=CatalogItem.CatalogItemStatus.ACTIVE,
        )

        self.lap_003 = EquipmentUnit.objects.create(
            asset_code="LAP-003",
            catalog_item=self.item_laptop,
            inventory_status=EquipmentUnit.EquipmentStatus.ISSUED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        self.cam_001 = EquipmentUnit.objects.create(
            asset_code="CAM-001",
            catalog_item=self.item_cam,
            inventory_status=EquipmentUnit.EquipmentStatus.ISSUED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        self.dmm_002 = EquipmentUnit.objects.create(
            asset_code="DMM-002",
            catalog_item=self.item_dmm,
            inventory_status=EquipmentUnit.EquipmentStatus.ISSUED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        self.dmm_003 = EquipmentUnit.objects.create(
            asset_code="DMM-003",
            catalog_item=self.item_dmm,
            inventory_status=EquipmentUnit.EquipmentStatus.ISSUED,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )

        now = timezone.now()
        self.borrow_request = BorrowRequest.objects.create(
            user=self.beatrice,
            purpose="Capstone project remote data acquisition demonstration",
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
            due_at=now - timedelta(days=3),
        )

        ri_lap = RequestItem.objects.create(
            borrow_request=self.borrow_request,
            catalog_item=self.item_laptop,
            quantity=1,
        )
        ri_cam = RequestItem.objects.create(
            borrow_request=self.borrow_request,
            catalog_item=self.item_cam,
            quantity=1,
        )
        ri_dmm = RequestItem.objects.create(
            borrow_request=self.borrow_request,
            catalog_item=self.item_dmm,
            quantity=2,
        )

        for ri, unit in [
            (ri_lap, self.lap_003),
            (ri_cam, self.cam_001),
            (ri_dmm, self.dmm_002),
            (ri_dmm, self.dmm_003),
        ]:
            UnitAllocation.objects.create(
                request_item=ri,
                equipment_unit=unit,
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=10),
            )

        LoanRecord.objects.create(
            borrow_request=self.borrow_request,
            user=self.admin,
            released_at=now - timedelta(days=10),
        )

    def test_returns_page_displays_multiple_units_and_overdue_days(self):
        response = self.client.get(
            reverse("manage_returns"),
            {"request_id": self.borrow_request.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LAP-003")
        self.assertContains(response, "CAM-001")
        self.assertContains(response, "DMM-002")
        self.assertContains(response, "DMM-003")
        self.assertContains(response, "Overdue (3 days)")
        self.assertEqual(self.borrow_request.overdue_days(), 3)
        self.assertContains(
            response,
            f'data-selectable-row="{self.borrow_request.id}"',
        )
        self.assertContains(response, "bg-brand-primary-subtle")
        self.assertContains(response, "toggleRowSelection(this)")
        self.assertNotContains(response, '<th class="px-4 py-3.5 w-10 text-center">Select</th>')
        self.assertNotContains(response, "data-select-all=")
        self.assertNotContains(response, "Return Selected Units")
        self.assertNotContains(response, "Return All Remaining")
        self.assertNotContains(response, "condition_LAP-003")

    def test_single_unit_partial_return_and_overdue_days_preserved(self):
        response = self.client.post(
            reverse("process_unit_return"),
            {
                "borrow_request_id": self.borrow_request.id,
                "asset_code": "LAP-003",
                "condition": EquipmentUnit.EquipmentCondition.FINE,
            },
        )
        self.assertEqual(response.status_code, 302)

        self.borrow_request.refresh_from_db()
        self.lap_003.refresh_from_db()

        self.assertEqual(
            self.borrow_request.status,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
        )
        self.assertEqual(
            self.lap_003.inventory_status,
            EquipmentUnit.EquipmentStatus.AVAILABLE,
        )
        self.assertEqual(
            self.lap_003.condition,
            EquipmentUnit.EquipmentCondition.FINE,
        )
        self.assertEqual(self.borrow_request.overdue_days(), 3)

    def test_multiple_item_return_with_damaged_routing_to_maintenance(self):
        response = self.client.post(
            reverse("process_unit_return"),
            {
                "borrow_request_id": self.borrow_request.id,
                "return_mode": "selected",
                "asset_codes": ["CAM-001", "DMM-002"],
                "condition_CAM-001": EquipmentUnit.EquipmentCondition.FINE,
                "condition_DMM-002": EquipmentUnit.EquipmentCondition.DAMAGED,
            },
        )
        self.assertEqual(response.status_code, 302)

        self.borrow_request.refresh_from_db()
        self.cam_001.refresh_from_db()
        self.dmm_002.refresh_from_db()

        # Request is PARTIALLY_RETURNED (2 of 4 returned)
        self.assertEqual(
            self.borrow_request.status,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
        )
        # CAM-001 returned FINE -> AVAILABLE
        self.assertEqual(
            self.cam_001.inventory_status,
            EquipmentUnit.EquipmentStatus.AVAILABLE,
        )
        self.assertEqual(
            self.cam_001.condition,
            EquipmentUnit.EquipmentCondition.FINE,
        )
        # DMM-002 returned DAMAGED -> MAINTENANCE + active MaintenanceRecord
        self.assertEqual(
            self.dmm_002.inventory_status,
            EquipmentUnit.EquipmentStatus.MAINTENANCE,
        )
        self.assertEqual(
            self.dmm_002.condition,
            EquipmentUnit.EquipmentCondition.DAMAGED,
        )
        self.assertTrue(
            MaintenanceRecord.objects.filter(
                unit=self.dmm_002,
                status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
            ).exists()
        )

    def test_return_all_remaining_completes_request_and_clears_overdue_days(self):
        # First return 1 unit so 3 remain
        self.client.post(
            reverse("process_unit_return"),
            {
                "borrow_request_id": self.borrow_request.id,
                "return_mode": "single:LAP-003",
                "condition_LAP-003": EquipmentUnit.EquipmentCondition.FINE,
            },
        )
        self.borrow_request.refresh_from_db()
        self.assertEqual(
            self.borrow_request.status,
            BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
        )
        self.assertEqual(self.borrow_request.overdue_days(), 3)

        # Now return all remaining units at once (with DMM-003 damaged)
        response = self.client.post(
            reverse("process_unit_return"),
            {
                "borrow_request_id": self.borrow_request.id,
                "return_mode": "all",
                "condition_CAM-001": EquipmentUnit.EquipmentCondition.FINE,
                "condition_DMM-002": EquipmentUnit.EquipmentCondition.FINE,
                "condition_DMM-003": EquipmentUnit.EquipmentCondition.DAMAGED,
            },
        )
        self.assertEqual(response.status_code, 302)

        self.borrow_request.refresh_from_db()
        self.cam_001.refresh_from_db()
        self.dmm_002.refresh_from_db()
        self.dmm_003.refresh_from_db()

        self.assertEqual(
            self.borrow_request.status,
            BorrowRequest.BorrowRequestStatus.RETURNED,
        )
        self.assertEqual(self.borrow_request.overdue_days(), 0)
        self.assertEqual(
            ReturnRecord.objects.filter(borrow_request=self.borrow_request).count(),
            4,
        )
        self.assertEqual(
            self.cam_001.inventory_status,
            EquipmentUnit.EquipmentStatus.AVAILABLE,
        )
        self.assertEqual(
            self.dmm_002.inventory_status,
            EquipmentUnit.EquipmentStatus.AVAILABLE,
        )
        self.assertEqual(
            self.dmm_003.inventory_status,
            EquipmentUnit.EquipmentStatus.MAINTENANCE,
        )
        self.assertTrue(
            MaintenanceRecord.objects.filter(
                unit=self.dmm_003,
                status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
            ).exists()
        )

    def test_partially_returned_request_review_shows_returned_and_not_returned_unit_indicators(self):
        # Return LAP-003 (FINE) and DMM-002 (DAMAGED), leaving CAM-001 and DMM-003 unreturned
        self.client.post(
            reverse("process_unit_return"),
            {
                "borrow_request_id": self.borrow_request.id,
                "return_mode": "selected",
                "asset_codes": ["LAP-003", "DMM-002"],
                "condition_LAP-003": EquipmentUnit.EquipmentCondition.FINE,
                "condition_DMM-002": EquipmentUnit.EquipmentCondition.DAMAGED,
            },
        )

        review_response = self.client.get(
            reverse("borrow_request_review", args=[self.borrow_request.id])
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertContains(review_response, "Partially Returned")
        self.assertContains(review_response, "Returned")
        self.assertContains(review_response, "Returned (Damaged)")
        self.assertContains(review_response, "Not Returned")
        self.assertContains(review_response, "border-emerald-200 bg-emerald-50")
        self.assertContains(review_response, "border-rose-200 bg-rose-50")
        self.assertContains(review_response, "border-amber-200 bg-amber-50")

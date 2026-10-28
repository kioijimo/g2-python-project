import sqlite3
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from app.models import (
    BorrowRequest,
    CatalogItem,
    Category,
    EquipmentUnit,
    LoanRecord,
    MaintenanceRecord,
    Profile,
    ReturnRecord,
    UnitAllocation,
    User,
)


class SeedDemoDataCommandTest(TestCase):
    def test_seed_demo_data_command(self):
        call_command("seed_demo_data", flush=True)

        # 1. Categories: >= 3
        self.assertGreaterEqual(Category.objects.count(), 3)

        # 2. Catalog Items: >= 6
        self.assertGreaterEqual(CatalogItem.objects.count(), 6)

        # 3. Physical Units: >= 18
        self.assertGreaterEqual(EquipmentUnit.objects.count(), 18)

        # 4. Users: 1 Admin, 8 Basic Users
        self.assertEqual(User.objects.filter(role=User.UserRoles.ADMIN).count(), 1)
        self.assertEqual(User.objects.filter(role=User.UserRoles.USER).count(), 8)

        # 5. Names: All 6 group member names must exist in profiles
        expected_names = [
            ("Vonlery", "Villanueva"),
            ("Marc Justin", "Pavia"),
            ("Lester", "Perez"),
            ("John Ace", "Padilla"),
            ("Janver", "Flores"),
            ("Denzelkeane", "Aquino"),
        ]
        for first_name, last_name in expected_names:
            self.assertTrue(
                Profile.objects.filter(first_name=first_name, last_name=last_name).exists(),
                f"Missing profile for {first_name} {last_name}",
            )

        # 6. Requests: >= 20
        self.assertGreaterEqual(BorrowRequest.objects.count(), 20)

        # 7. Issued Loans: >= 8
        self.assertGreaterEqual(
            LoanRecord.objects.filter(released_at__isnull=False).count(), 8
        )

        # 8. Maintenance Records: >= 4
        self.assertGreaterEqual(MaintenanceRecord.objects.count(), 4)

        # 9. Scenarios:
        # Rejected
        self.assertTrue(
            BorrowRequest.objects.filter(
                status=BorrowRequest.BorrowRequestStatus.REJECTED
            ).exists()
        )
        # Cancelled
        self.assertTrue(
            BorrowRequest.objects.filter(
                status=BorrowRequest.BorrowRequestStatus.CANCELLED
            ).exists()
        )
        # Partially returned
        self.assertTrue(
            BorrowRequest.objects.filter(
                status=BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED
            ).exists()
        )
        # Damaged return
        self.assertTrue(
            ReturnRecord.objects.filter(
                condition=EquipmentUnit.EquipmentCondition.DAMAGED
            ).exists()
        )
        # Overdue loans
        now = timezone.now()
        self.assertTrue(
            BorrowRequest.objects.filter(
                status__in=[
                    BorrowRequest.BorrowRequestStatus.ISSUED,
                    BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
                ],
                due_at__lt=now,
            ).exists()
        )

        # 10. Beatrice Mendoza has multiple items and units for return
        beatrice_req = BorrowRequest.objects.get(
            user__email="beatrice.mendoza@example.com",
            status=BorrowRequest.BorrowRequestStatus.ISSUED,
        )
        self.assertEqual(beatrice_req.items.count(), 3)
        allocated_codes = set(
            UnitAllocation.objects.filter(
                request_item__borrow_request=beatrice_req,
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
            ).values_list("equipment_unit__asset_code", flat=True)
        )
        self.assertEqual(
            allocated_codes,
            {"LAP-003", "CAM-001", "DMM-002", "DMM-003"},
        )

    def test_seed_demo_data_sql_file_valid_and_has_beatrice_multi_items(self):
        sql_path = Path("seed_demo_data.sql")
        self.assertTrue(sql_path.exists())
        sql_script = sql_path.read_text(encoding="utf-8")

        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(sql_script)
            cursor = conn.cursor()
            # BorrowRequest #16 belongs to Beatrice (user_id=9)
            cursor.execute(
                "SELECT COUNT(*) FROM app_requestitem WHERE borrow_request_id = 16"
            )
            self.assertEqual(cursor.fetchone()[0], 3)

            cursor.execute(
                """
                SELECT eu.asset_code
                FROM app_unitallocation ua
                JOIN app_requestitem ri ON ua.request_item_id = ri.id
                JOIN app_equipmentunit eu ON ua.equipment_unit_id = eu.id
                WHERE ri.borrow_request_id = 16 AND ua.status = 2
                """
            )
            codes = {row[0] for row in cursor.fetchall()}
            self.assertEqual(codes, {"LAP-003", "CAM-001", "DMM-002", "DMM-003"})
        finally:
            conn.close()

from datetime import timedelta
import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app.models import (
    AuditLog,
    BorrowRequest,
    CatalogItem,
    Category,
    EquipmentUnit,
    LoanRecord,
    MaintenanceRecord,
    Profile,
    RequestItem,
    ReturnRecord,
    SystemSetting,
    UnitAllocation,
    User,
)


class Command(BaseCommand):
    help = "Seed database with Minimum Demonstration Data meeting all system criteria."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing demonstration data before seeding.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            with transaction.atomic():
                AuditLog.objects.all().delete()
                MaintenanceRecord.objects.all().delete()
                ReturnRecord.objects.all().delete()
                UnitAllocation.objects.all().delete()
                LoanRecord.objects.all().delete()
                RequestItem.objects.all().delete()
                BorrowRequest.objects.all().delete()
                EquipmentUnit.objects.all().delete()
                CatalogItem.objects.all().delete()
                Category.objects.all().delete()
                Profile.objects.all().delete()
                User.objects.all().delete()
                SystemSetting.objects.all().delete()

                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name LIKE 'app_%'")
            self.stdout.write(self.style.SUCCESS("Existing data flushed."))

        self.stdout.write("Seeding Minimum Demonstration Data...")
        now = timezone.now()
        raw_password = "DemoPass123!"
        hashed_password = make_password(raw_password)

        with transaction.atomic():
            # 1. System Setting
            setting, _ = SystemSetting.objects.get_or_create(
                pk=1,
                defaults={"max_borrow_quantity": 3, "max_borrow_days": 7},
            )
            setting.max_borrow_quantity = 3
            setting.max_borrow_days = 7
            setting.save()

            # 2. Users (1 Admin, 8 Basic Users)
            # Admin
            admin_user = User.objects.create(
                email="admin@example.com",
                password=hashed_password,
                role=User.UserRoles.ADMIN,
                status=User.UserStatus.ACTIVE,
                last_login=now,
            )
            Profile.objects.create(
                user=admin_user,
                first_name="Admin",
                last_name="Officer",
                contact_number="09170000001",
            )

            # 8 Basic Users (Including all 6 requested group names)
            basic_users_meta = [
                ("vonlery.villanueva@example.com", "Vonlery", "Villanueva", "09171110001"),
                ("marc.pavia@example.com", "Marc Justin", "Pavia", "09171110002"),
                ("lester.perez@example.com", "Lester", "Perez", "09171110003"),
                ("john.padilla@example.com", "John Ace", "Padilla", "09171110004"),
                ("janver.flores@example.com", "Janver", "Flores", "09171110005"),
                ("denzelkeane.aquino@example.com", "Denzelkeane", "Aquino", "09171110006"),
                ("rafael.cruz@example.com", "Rafael", "Cruz", "09171110007"),
                ("beatrice.mendoza@example.com", "Beatrice", "Mendoza", "09171110008"),
            ]

            users = {}
            for email, fname, lname, contact in basic_users_meta:
                u = User.objects.create(
                    email=email,
                    password=hashed_password,
                    role=User.UserRoles.USER,
                    status=User.UserStatus.ACTIVE,
                    last_login=now - timedelta(hours=2),
                )
                Profile.objects.create(
                    user=u,
                    first_name=fname,
                    last_name=lname,
                    contact_number=contact,
                )
                users[email] = u

            # 3. Categories (4 Categories, all ACTIVE)
            cat_it = Category.objects.create(
                name="IT & Computing",
                description="Laptops, portable workstations, and computer peripherals.",
                status=Category.CategoryStatus.ACTIVE,
            )
            cat_av = Category.objects.create(
                name="Audio-Visual Equipment",
                description="Projectors, presenter remotes, cameras, and display devices.",
                status=Category.CategoryStatus.ACTIVE,
            )
            cat_lab = Category.objects.create(
                name="Laboratory & Electronics",
                description="Digital multimeters, soldering stations, and electronic test gear.",
                status=Category.CategoryStatus.ACTIVE,
            )
            cat_office = Category.objects.create(
                name="Office & Facility Supplies",
                description="Document scanners, labeling equipment, and administrative tools.",
                status=Category.CategoryStatus.ACTIVE,
            )

            # 4. Catalog Items (8 Catalog Items)
            item_laptop = CatalogItem.objects.create(
                category=cat_it,
                name='Dell Latitude Laptop 14"',
                description="Core i7, 16GB RAM portable workstation for development and analysis.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )
            item_hub = CatalogItem.objects.create(
                category=cat_it,
                name="USB-C Multiport Hub",
                description="7-in-1 USB-C adapter with HDMI, USB 3.0, and Gigabit Ethernet.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )
            item_proj = CatalogItem.objects.create(
                category=cat_av,
                name="Epson PowerLite Projector",
                description="3600-lumen Full HD 3LCD projector with HDMI and wireless support.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )
            item_clicker = CatalogItem.objects.create(
                category=cat_av,
                name="Logitech Wireless Presenter Clicker",
                description="Ergonomic presentation remote with bright red laser pointer.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )
            item_cam = CatalogItem.objects.create(
                category=cat_av,
                name="Sony 4K Handheld Camcorder",
                description="Compact 4K video camera with optical image stabilization.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )
            item_dmm = CatalogItem.objects.create(
                category=cat_lab,
                name="Fluke Digital Multimeter",
                description="True-RMS multimeter for accurate voltage, resistance, and current readings.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )
            item_solder = CatalogItem.objects.create(
                category=cat_lab,
                name="Hakko Soldering Station",
                description="Adjustable temperature ESD-safe soldering station with stand.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )
            item_label = CatalogItem.objects.create(
                category=cat_office,
                name="Brother Heavy-Duty Label Maker",
                description="Industrial handheld labeling machine with laminated tape cassette.",
                status=CatalogItem.CatalogItemStatus.ACTIVE,
            )

            # 5. Physical Equipment Units (24 Physical Units)
            units = {}

            def add_unit(code, item, inv_status, cond):
                u = EquipmentUnit.objects.create(
                    asset_code=code,
                    catalog_item=item,
                    inventory_status=inv_status,
                    condition=cond,
                )
                units[code] = u
                return u

            # Laptops (4)
            add_unit("LAP-001", item_laptop, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("LAP-002", item_laptop, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("LAP-003", item_laptop, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("LAP-004", item_laptop, EquipmentUnit.EquipmentStatus.RESERVED, EquipmentUnit.EquipmentCondition.FINE)

            # USB Hubs (3)
            add_unit("HUB-001", item_hub, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("HUB-002", item_hub, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("HUB-003", item_hub, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)

            # Projectors (3)
            add_unit("PRJ-001", item_proj, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("PRJ-002", item_proj, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("PRJ-003", item_proj, EquipmentUnit.EquipmentStatus.MAINTENANCE, EquipmentUnit.EquipmentCondition.DAMAGED)

            # Clickers (3)
            add_unit("CLK-001", item_clicker, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("CLK-002", item_clicker, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("CLK-003", item_clicker, EquipmentUnit.EquipmentStatus.RESERVED, EquipmentUnit.EquipmentCondition.FINE)

            # Camcorders (3)
            add_unit("CAM-001", item_cam, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("CAM-002", item_cam, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("CAM-003", item_cam, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)

            # Multimeters (3)
            add_unit("DMM-001", item_dmm, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("DMM-002", item_dmm, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("DMM-003", item_dmm, EquipmentUnit.EquipmentStatus.ISSUED, EquipmentUnit.EquipmentCondition.FINE)

            # Soldering Stations (3)
            add_unit("SLD-001", item_solder, EquipmentUnit.EquipmentStatus.MAINTENANCE, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("SLD-002", item_solder, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("SLD-003", item_solder, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)

            # Label Makers (2)
            add_unit("LBL-001", item_label, EquipmentUnit.EquipmentStatus.RESERVED, EquipmentUnit.EquipmentCondition.FINE)
            add_unit("LBL-002", item_label, EquipmentUnit.EquipmentStatus.AVAILABLE, EquipmentUnit.EquipmentCondition.FINE)

            # 6. Borrow Requests, RequestItems, UnitAllocations, LoanRecords, ReturnRecords
            # Total 20 requests:
            # - 4 PENDING (Req 1..4)
            # - 3 APPROVED (Req 5..7)
            # - 3 REJECTED (Req 8..10)
            # - 2 CANCELLED (Req 11..12)
            # - 8 ISSUED LOANS (Req 13..20):
            #     - 3 Active on-time (Req 13..15)
            #     - 2 Overdue loans (Req 16..17)
            #     - 1 Partial return (Req 18)
            #     - 1 Fully returned fine (Req 19)
            #     - 1 Returned with damaged unit (Req 20)

            # Req 1: PENDING
            r1 = BorrowRequest.objects.create(
                user=users["vonlery.villanueva@example.com"],
                purpose="Class presentation on system architecture and design patterns",
                status=BorrowRequest.BorrowRequestStatus.PENDING,
                due_at=now + timedelta(days=5),
            )
            BorrowRequest.objects.filter(pk=r1.pk).update(created_at=now - timedelta(hours=3))
            RequestItem.objects.create(borrow_request=r1, catalog_item=item_clicker, quantity=1)

            # Req 2: PENDING
            r2 = BorrowRequest.objects.create(
                user=users["marc.pavia@example.com"],
                purpose="Laboratory experiment on analog amplifier circuit testing",
                status=BorrowRequest.BorrowRequestStatus.PENDING,
                due_at=now + timedelta(days=4),
            )
            BorrowRequest.objects.filter(pk=r2.pk).update(created_at=now - timedelta(hours=2))
            RequestItem.objects.create(borrow_request=r2, catalog_item=item_dmm, quantity=1)

            # Req 3: PENDING
            r3 = BorrowRequest.objects.create(
                user=users["lester.perez@example.com"],
                purpose="Prototyping microcontroller board and header pin soldering",
                status=BorrowRequest.BorrowRequestStatus.PENDING,
                due_at=now + timedelta(days=6),
            )
            BorrowRequest.objects.filter(pk=r3.pk).update(created_at=now - timedelta(hours=1))
            RequestItem.objects.create(borrow_request=r3, catalog_item=item_solder, quantity=1)

            # Req 4: PENDING
            r4 = BorrowRequest.objects.create(
                user=users["john.padilla@example.com"],
                purpose="Equipment labeling and wire tagging for capstone project hardware box",
                status=BorrowRequest.BorrowRequestStatus.PENDING,
                due_at=now + timedelta(days=3),
            )
            BorrowRequest.objects.filter(pk=r4.pk).update(created_at=now - timedelta(minutes=45))
            RequestItem.objects.create(borrow_request=r4, catalog_item=item_label, quantity=1)

            # Req 5: APPROVED (Awaiting release)
            r5 = BorrowRequest.objects.create(
                user=users["janver.flores@example.com"],
                purpose="Inter-collegiate programming contest training and simulation",
                status=BorrowRequest.BorrowRequestStatus.APPROVED,
                due_at=now + timedelta(days=5),
            )
            BorrowRequest.objects.filter(pk=r5.pk).update(created_at=now - timedelta(days=1))
            ri5 = RequestItem.objects.create(borrow_request=r5, catalog_item=item_laptop, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri5,
                equipment_unit=units["LAP-004"],
                status=UnitAllocation.UnitAllocationStatus.PENDING,
                allocated_at=now - timedelta(hours=12),
            )
            lr5 = LoanRecord.objects.create(borrow_request=r5, user=admin_user, released_at=None)
            LoanRecord.objects.filter(pk=lr5.pk).update(created_at=now - timedelta(hours=12))

            # Req 6: APPROVED (Awaiting release)
            r6 = BorrowRequest.objects.create(
                user=users["denzelkeane.aquino@example.com"],
                purpose="Thesis title defense slide presentation",
                status=BorrowRequest.BorrowRequestStatus.APPROVED,
                due_at=now + timedelta(days=4),
            )
            BorrowRequest.objects.filter(pk=r6.pk).update(created_at=now - timedelta(days=1))
            ri6 = RequestItem.objects.create(borrow_request=r6, catalog_item=item_clicker, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri6,
                equipment_unit=units["CLK-003"],
                status=UnitAllocation.UnitAllocationStatus.PENDING,
                allocated_at=now - timedelta(hours=10),
            )
            lr6 = LoanRecord.objects.create(borrow_request=r6, user=admin_user, released_at=None)
            LoanRecord.objects.filter(pk=lr6.pk).update(created_at=now - timedelta(hours=10))

            # Req 7: APPROVED (Awaiting release)
            r7 = BorrowRequest.objects.create(
                user=users["rafael.cruz@example.com"],
                purpose="Inventory labeling for organizational archives",
                status=BorrowRequest.BorrowRequestStatus.APPROVED,
                due_at=now + timedelta(days=3),
            )
            BorrowRequest.objects.filter(pk=r7.pk).update(created_at=now - timedelta(hours=18))
            ri7 = RequestItem.objects.create(borrow_request=r7, catalog_item=item_label, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri7,
                equipment_unit=units["LBL-001"],
                status=UnitAllocation.UnitAllocationStatus.PENDING,
                allocated_at=now - timedelta(hours=8),
            )
            lr7 = LoanRecord.objects.create(borrow_request=r7, user=admin_user, released_at=None)
            LoanRecord.objects.filter(pk=lr7.pk).update(created_at=now - timedelta(hours=8))

            # Req 8: REJECTED
            r8 = BorrowRequest.objects.create(
                user=users["beatrice.mendoza@example.com"],
                purpose="Movie night with friends at private dormitory",
                status=BorrowRequest.BorrowRequestStatus.REJECTED,
                due_at=now + timedelta(days=3),
                rejection_reason="Off-campus personal entertainment use is strictly prohibited by university borrowing regulations.",
            )
            BorrowRequest.objects.filter(pk=r8.pk).update(created_at=now - timedelta(days=2))
            RequestItem.objects.create(borrow_request=r8, catalog_item=item_proj, quantity=1)
            lr8 = LoanRecord.objects.create(borrow_request=r8, user=admin_user, released_at=None)
            LoanRecord.objects.filter(pk=lr8.pk).update(created_at=now - timedelta(days=1, hours=20))

            # Req 9: REJECTED
            r9 = BorrowRequest.objects.create(
                user=users["vonlery.villanueva@example.com"],
                purpose="Personal vlog filming off-campus over long weekend",
                status=BorrowRequest.BorrowRequestStatus.REJECTED,
                due_at=now + timedelta(days=4),
                rejection_reason="Equipment cannot be borrowed for non-academic personal vlog production off-campus.",
            )
            BorrowRequest.objects.filter(pk=r9.pk).update(created_at=now - timedelta(days=3))
            RequestItem.objects.create(borrow_request=r9, catalog_item=item_cam, quantity=1)
            lr9 = LoanRecord.objects.create(borrow_request=r9, user=admin_user, released_at=None)
            LoanRecord.objects.filter(pk=lr9.pk).update(created_at=now - timedelta(days=2, hours=18))

            # Req 10: REJECTED
            r10 = BorrowRequest.objects.create(
                user=users["marc.pavia@example.com"],
                purpose="Unmonitored high voltage line test outside engineering building",
                status=BorrowRequest.BorrowRequestStatus.REJECTED,
                due_at=now + timedelta(days=2),
                rejection_reason="Hazardous electrical testing requires certified laboratory faculty supervision and an approved safety risk assessment.",
            )
            BorrowRequest.objects.filter(pk=r10.pk).update(created_at=now - timedelta(days=2))
            RequestItem.objects.create(borrow_request=r10, catalog_item=item_dmm, quantity=1)
            lr10 = LoanRecord.objects.create(borrow_request=r10, user=admin_user, released_at=None)
            LoanRecord.objects.filter(pk=lr10.pk).update(created_at=now - timedelta(days=1, hours=15))

            # Req 11: CANCELLED
            r11 = BorrowRequest.objects.create(
                user=users["lester.perez@example.com"],
                purpose="Organization meeting originally scheduled for Friday afternoon",
                status=BorrowRequest.BorrowRequestStatus.CANCELLED,
                due_at=now + timedelta(days=3),
            )
            BorrowRequest.objects.filter(pk=r11.pk).update(created_at=now - timedelta(days=4))
            RequestItem.objects.create(borrow_request=r11, catalog_item=item_proj, quantity=1)

            # Req 12: CANCELLED
            r12 = BorrowRequest.objects.create(
                user=users["john.padilla@example.com"],
                purpose="Borrowed an alternative laptop from lab teammate instead",
                status=BorrowRequest.BorrowRequestStatus.CANCELLED,
                due_at=now + timedelta(days=2),
            )
            BorrowRequest.objects.filter(pk=r12.pk).update(created_at=now - timedelta(days=3))
            RequestItem.objects.create(borrow_request=r12, catalog_item=item_laptop, quantity=1)

            # Req 13: ISSUED LOAN #1 (Active, On-Time)
            r13 = BorrowRequest.objects.create(
                user=users["janver.flores@example.com"],
                purpose="Software engineering web development sprint workshop",
                status=BorrowRequest.BorrowRequestStatus.ISSUED,
                due_at=now + timedelta(days=5),
            )
            BorrowRequest.objects.filter(pk=r13.pk).update(created_at=now - timedelta(days=2))
            ri13 = RequestItem.objects.create(borrow_request=r13, catalog_item=item_laptop, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri13,
                equipment_unit=units["LAP-002"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=2),
            )
            lr13 = LoanRecord.objects.create(
                borrow_request=r13,
                user=admin_user,
                released_at=now - timedelta(days=2),
            )
            LoanRecord.objects.filter(pk=lr13.pk).update(created_at=now - timedelta(days=2))

            # Req 14: ISSUED LOAN #2 (Active, On-Time)
            r14 = BorrowRequest.objects.create(
                user=users["denzelkeane.aquino@example.com"],
                purpose="Department seminar research symposium presentation",
                status=BorrowRequest.BorrowRequestStatus.ISSUED,
                due_at=now + timedelta(days=6),
            )
            BorrowRequest.objects.filter(pk=r14.pk).update(created_at=now - timedelta(days=1))
            ri14 = RequestItem.objects.create(borrow_request=r14, catalog_item=item_clicker, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri14,
                equipment_unit=units["CLK-002"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=1),
            )
            lr14 = LoanRecord.objects.create(
                borrow_request=r14,
                user=admin_user,
                released_at=now - timedelta(days=1),
            )
            LoanRecord.objects.filter(pk=lr14.pk).update(created_at=now - timedelta(days=1))

            # Req 15: ISSUED LOAN #3 (Active, On-Time)
            r15 = BorrowRequest.objects.create(
                user=users["rafael.cruz@example.com"],
                purpose="Guest speaker technical lecture in AV amphitheater",
                status=BorrowRequest.BorrowRequestStatus.ISSUED,
                due_at=now + timedelta(days=4),
            )
            BorrowRequest.objects.filter(pk=r15.pk).update(created_at=now - timedelta(days=1))
            ri15 = RequestItem.objects.create(borrow_request=r15, catalog_item=item_proj, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri15,
                equipment_unit=units["PRJ-002"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=1),
            )
            lr15 = LoanRecord.objects.create(
                borrow_request=r15,
                user=admin_user,
                released_at=now - timedelta(days=1),
            )
            LoanRecord.objects.filter(pk=lr15.pk).update(created_at=now - timedelta(days=1))

            # Req 16: ISSUED LOAN #4 (OVERDUE by 3 days, Multiple Items & Units for Beatrice)
            r16 = BorrowRequest.objects.create(
                user=users["beatrice.mendoza@example.com"],
                purpose="Capstone project remote data acquisition demonstration",
                status=BorrowRequest.BorrowRequestStatus.ISSUED,
                due_at=now - timedelta(days=3),
            )
            BorrowRequest.objects.filter(pk=r16.pk).update(created_at=now - timedelta(days=10))
            ri16 = RequestItem.objects.create(borrow_request=r16, catalog_item=item_laptop, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri16,
                equipment_unit=units["LAP-003"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=10),
            )
            ri16_cam = RequestItem.objects.create(borrow_request=r16, catalog_item=item_cam, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri16_cam,
                equipment_unit=units["CAM-001"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=10),
            )
            ri16_dmm = RequestItem.objects.create(borrow_request=r16, catalog_item=item_dmm, quantity=2)
            UnitAllocation.objects.create(
                request_item=ri16_dmm,
                equipment_unit=units["DMM-002"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=10),
            )
            UnitAllocation.objects.create(
                request_item=ri16_dmm,
                equipment_unit=units["DMM-003"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=10),
            )
            lr16 = LoanRecord.objects.create(
                borrow_request=r16,
                user=admin_user,
                released_at=now - timedelta(days=10),
            )
            LoanRecord.objects.filter(pk=lr16.pk).update(created_at=now - timedelta(days=10))

            # Req 17: ISSUED LOAN #5 (OVERDUE by 5 days)
            r17 = BorrowRequest.objects.create(
                user=users["vonlery.villanueva@example.com"],
                purpose="Laboratory serial sensor multi-port communication logging",
                status=BorrowRequest.BorrowRequestStatus.ISSUED,
                due_at=now - timedelta(days=5),
            )
            BorrowRequest.objects.filter(pk=r17.pk).update(created_at=now - timedelta(days=12))
            ri17 = RequestItem.objects.create(borrow_request=r17, catalog_item=item_hub, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri17,
                equipment_unit=units["HUB-001"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=12),
            )
            lr17 = LoanRecord.objects.create(
                borrow_request=r17,
                user=admin_user,
                released_at=now - timedelta(days=12),
            )
            LoanRecord.objects.filter(pk=lr17.pk).update(created_at=now - timedelta(days=12))

            # Req 18: ISSUED LOAN #6 (PARTIALLY RETURNED: 1 unit returned, 1 still issued)
            r18 = BorrowRequest.objects.create(
                user=users["marc.pavia@example.com"],
                purpose="Network benchmarking and parallel switch performance test",
                status=BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED,
                due_at=now + timedelta(days=2),
            )
            BorrowRequest.objects.filter(pk=r18.pk).update(created_at=now - timedelta(days=5))
            ri18 = RequestItem.objects.create(borrow_request=r18, catalog_item=item_hub, quantity=2)
            UnitAllocation.objects.create(
                request_item=ri18,
                equipment_unit=units["HUB-002"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=5),
            )
            UnitAllocation.objects.create(
                request_item=ri18,
                equipment_unit=units["HUB-003"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=5),
            )
            lr18 = LoanRecord.objects.create(
                borrow_request=r18,
                user=admin_user,
                released_at=now - timedelta(days=5),
            )
            LoanRecord.objects.filter(pk=lr18.pk).update(created_at=now - timedelta(days=5))

            # Return of HUB-003 in FINE condition
            ret18 = ReturnRecord.objects.create(
                borrow_request=r18,
                equipment_unit=units["HUB-003"],
                condition=EquipmentUnit.EquipmentCondition.FINE,
            )
            ReturnRecord.objects.filter(pk=ret18.pk).update(created_at=now - timedelta(days=1))

            # Req 19: ISSUED LOAN #7 (FULLY RETURNED FINE)
            r19 = BorrowRequest.objects.create(
                user=users["lester.perez@example.com"],
                purpose="Cybersecurity workshop interactive session",
                status=BorrowRequest.BorrowRequestStatus.RETURNED,
                due_at=now - timedelta(days=2),
            )
            BorrowRequest.objects.filter(pk=r19.pk).update(created_at=now - timedelta(days=8))
            ri19 = RequestItem.objects.create(borrow_request=r19, catalog_item=item_clicker, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri19,
                equipment_unit=units["CLK-001"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=8),
            )
            lr19 = LoanRecord.objects.create(
                borrow_request=r19,
                user=admin_user,
                released_at=now - timedelta(days=8),
            )
            LoanRecord.objects.filter(pk=lr19.pk).update(created_at=now - timedelta(days=8))
            ret19 = ReturnRecord.objects.create(
                borrow_request=r19,
                equipment_unit=units["CLK-001"],
                condition=EquipmentUnit.EquipmentCondition.FINE,
            )
            ReturnRecord.objects.filter(pk=ret19.pk).update(created_at=now - timedelta(days=3))

            # Req 20: ISSUED LOAN #8 (FULLY RETURNED DAMAGED)
            r20 = BorrowRequest.objects.create(
                user=users["john.padilla@example.com"],
                purpose="Outdoor student orientation audio-visual setup",
                status=BorrowRequest.BorrowRequestStatus.RETURNED,
                due_at=now - timedelta(days=1),
            )
            BorrowRequest.objects.filter(pk=r20.pk).update(created_at=now - timedelta(days=7))
            ri20 = RequestItem.objects.create(borrow_request=r20, catalog_item=item_proj, quantity=1)
            UnitAllocation.objects.create(
                request_item=ri20,
                equipment_unit=units["PRJ-003"],
                status=UnitAllocation.UnitAllocationStatus.RELEASED,
                allocated_at=now - timedelta(days=7),
            )
            lr20 = LoanRecord.objects.create(
                borrow_request=r20,
                user=admin_user,
                released_at=now - timedelta(days=7),
            )
            LoanRecord.objects.filter(pk=lr20.pk).update(created_at=now - timedelta(days=7))
            ret20 = ReturnRecord.objects.create(
                borrow_request=r20,
                equipment_unit=units["PRJ-003"],
                condition=EquipmentUnit.EquipmentCondition.DAMAGED,
            )
            ReturnRecord.objects.filter(pk=ret20.pk).update(created_at=now - timedelta(days=2))

            # 7. Maintenance Records (4 Maintenance Records)
            # Record 1: The damaged return from Req 20 (PRJ-003)
            m1 = MaintenanceRecord.objects.create(
                maintainer=admin_user,
                unit=units["PRJ-003"],
                issue="Cracked HDMI port casing and loose female pin connector from BorrowRequest #20.",
                action="Ordered replacement daughterboard port; unit kept in storage.",
                status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
                resolved_at=now + timedelta(days=2),
            )
            MaintenanceRecord.objects.filter(pk=m1.pk).update(created_at=now - timedelta(days=2))

            # Record 2: Routine Calibration on DMM-001 (FINISHED)
            m2 = MaintenanceRecord.objects.create(
                maintainer=admin_user,
                unit=units["DMM-001"],
                issue="Annual scheduled ISO calibration verification and fuse health check.",
                action="Calibrated AC/DC voltage standards within 0.05% tolerance; replaced 9V battery.",
                status=MaintenanceRecord.MaintenanceStatus.FINISHED,
                resolved_at=now - timedelta(days=14),
            )
            MaintenanceRecord.objects.filter(pk=m2.pk).update(created_at=now - timedelta(days=15))

            # Record 3: Cable fix on PRJ-001 (FINISHED)
            m3 = MaintenanceRecord.objects.create(
                maintainer=admin_user,
                unit=units["PRJ-001"],
                issue="Flickering image output caused by internal ribbon cable strain.",
                action="Reseated and insulated internal LVDS flex cable; 4-hour soak test passed.",
                status=MaintenanceRecord.MaintenanceStatus.FINISHED,
                resolved_at=now - timedelta(days=18),
            )
            MaintenanceRecord.objects.filter(pk=m3.pk).update(created_at=now - timedelta(days=20))

            # Record 4: Soldering Iron Tip inspection on SLD-001 (ACTIVE)
            m4 = MaintenanceRecord.objects.create(
                maintainer=admin_user,
                unit=units["SLD-001"],
                issue="Temperature error code 54 displaying intermittently under heavy thermal load.",
                action="Disassembled ceramic heating core for resistance measurement and lead inspection.",
                status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
                resolved_at=now + timedelta(days=1),
            )
            MaintenanceRecord.objects.filter(pk=m4.pk).update(created_at=now - timedelta(days=1))

            # 8. Audit Logs
            logs = [
                (now - timedelta(days=25), "Configured system settings (Max borrow: 3 units, 7 days)."),
                (now - timedelta(days=24), "Created category 'IT & Computing'."),
                (now - timedelta(days=24), "Created category 'Audio-Visual Equipment'."),
                (now - timedelta(days=24), "Created category 'Laboratory & Electronics'."),
                (now - timedelta(days=24), "Created category 'Office & Facility Supplies'."),
                (now - timedelta(days=23), "Added catalog item 'Dell Latitude Laptop 14\"'."),
                (now - timedelta(days=23), "Added catalog item 'USB-C Multiport Hub'."),
                (now - timedelta(days=23), "Added catalog item 'Epson PowerLite Projector'."),
                (now - timedelta(days=23), "Added catalog item 'Logitech Wireless Presenter Clicker'."),
                (now - timedelta(days=22), "Batch registered 24 physical equipment units into inventory."),
                (now - timedelta(days=20), "Opened maintenance record #3 for projector unit 'PRJ-001'."),
                (now - timedelta(days=18), "Resolved maintenance record #3 for 'PRJ-001' (Repaired)."),
                (now - timedelta(days=15), "Opened maintenance record #2 for multimeter 'DMM-001'."),
                (now - timedelta(days=14), "Resolved maintenance record #2 for 'DMM-001' (Calibrated)."),
                (now - timedelta(days=12), "Released loan for BorrowRequest #17 to user 'vonlery.villanueva@example.com'."),
                (now - timedelta(days=10), "Released loan for BorrowRequest #16 to user 'beatrice.mendoza@example.com'."),
                (now - timedelta(days=8), "Released loan for BorrowRequest #19 to user 'lester.perez@example.com'."),
                (now - timedelta(days=7), "Released loan for BorrowRequest #20 to user 'john.padilla@example.com'."),
                (now - timedelta(days=5), "Released loan for BorrowRequest #18 to user 'marc.pavia@example.com'."),
                (now - timedelta(days=3), "Processed return of unit 'CLK-001' in FINE condition for BorrowRequest #19."),
                (now - timedelta(days=2), "Processed return of unit 'PRJ-003' in DAMAGED condition for BorrowRequest #20."),
                (now - timedelta(days=2), "Opened maintenance record #1 for damaged unit 'PRJ-003'."),
                (now - timedelta(days=2), "Rejected borrow request #8 for student 'beatrice.mendoza@example.com'."),
                (now - timedelta(days=2), "Rejected borrow request #9 for student 'vonlery.villanueva@example.com'."),
                (now - timedelta(days=2), "Released loan for BorrowRequest #13 to user 'janver.flores@example.com'."),
                (now - timedelta(days=1), "Released loan for BorrowRequest #14 to user 'denzelkeane.aquino@example.com'."),
                (now - timedelta(days=1), "Released loan for BorrowRequest #15 to user 'rafael.cruz@example.com'."),
                (now - timedelta(days=1), "Processed partial return of unit 'HUB-003' in FINE condition for BorrowRequest #18."),
                (now - timedelta(days=1), "Opened maintenance record #4 for soldering station 'SLD-001'."),
                (now - timedelta(hours=12), "Approved borrow request #5 for student 'janver.flores@example.com'."),
                (now - timedelta(hours=10), "Approved borrow request #6 for student 'denzelkeane.aquino@example.com'."),
                (now - timedelta(hours=8), "Approved borrow request #7 for student 'rafael.cruz@example.com'."),
            ]
            for log_time, action in logs:
                log_obj = AuditLog.objects.create(user=admin_user, action=action)
                AuditLog.objects.filter(pk=log_obj.pk).update(created_at=log_time)

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))

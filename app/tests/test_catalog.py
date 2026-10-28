from django.test import TestCase
from django.urls import reverse

from django.utils import timezone
from app.models import (
    BorrowRequest,
    CatalogItem,
    Category,
    EquipmentUnit,
    MaintenanceRecord,
    ReturnRecord,
    UnitAllocation,
)
from app.tests.helpers import (
    create_admin,
    create_borrow_request,
    create_catalog_item,
    create_category,
    create_request_item,
    create_units,
    create_user,
)


class CatalogTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)
        self.computing = create_category("Computing")
        self.audio = create_category("Audio")

    def test_catalog_shows_only_active_items_in_active_categories(self):
        visible = create_catalog_item("Laptop", category=self.computing)
        archived_item = create_catalog_item(
            "Old Laptop",
            category=self.computing,
            status=CatalogItem.CatalogItemStatus.ARCHIVED,
        )
        archived_category = create_category(
            "Retired", status=Category.CategoryStatus.ARCHIVED
        )
        hidden = create_catalog_item("Retired Projector", category=archived_category)

        response = self.client.get(reverse("portal:catalog"))

        self.assertContains(response, visible.name)
        self.assertNotContains(response, archived_item.name)
        self.assertNotContains(response, hidden.name)

    def test_catalog_shows_available_and_serviceable_counts(self):
        item = create_catalog_item("Laptop", category=self.computing)
        create_units(
            item,
            count=2,
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
        )
        create_units(
            item,
            count=1,
            inventory_status=EquipmentUnit.EquipmentStatus.RESERVED,
        )
        create_units(
            item,
            count=1,
            condition=EquipmentUnit.EquipmentCondition.DAMAGED,
        )
        create_units(
            item,
            count=1,
            inventory_status=EquipmentUnit.EquipmentStatus.MAINTENANCE,
        )

        response = self.client.get(reverse("portal:catalog"))

        self.assertContains(response, "2 available")
        self.assertContains(response, "3 serviceable")

    def test_catalog_shows_requestable_count_for_pending_demand(self):
        item = create_catalog_item("Laptop", category=self.computing)
        create_units(item, count=3)
        pending = create_borrow_request(user=self.user)
        create_request_item(pending, item, quantity=2)

        response = self.client.get(reverse("portal:catalog"))

        self.assertContains(response, "3 available")
        self.assertContains(response, "1 requestable")
        self.assertContains(response, "Request this item")

    def test_catalog_disables_requesting_when_pending_demand_uses_all_units(self):
        item = create_catalog_item("Laptop", category=self.computing)
        create_units(item, count=3)
        pending = create_borrow_request(user=self.user)
        create_request_item(pending, item, quantity=3)

        response = self.client.get(reverse("portal:catalog"))

        self.assertContains(response, "0 requestable")
        self.assertContains(response, "All available units are pending review")
        self.assertNotContains(response, "Request this item")

    def test_catalog_filters_by_selected_category(self):
        laptop = create_catalog_item("Laptop", category=self.computing)
        speaker = create_catalog_item("Speaker", category=self.audio)

        response = self.client.get(
            reverse("portal:catalog"),
            {"category": self.audio.pk},
        )

        self.assertContains(response, speaker.name)
        self.assertNotContains(response, laptop.name)
        self.assertContains(response, "Showing items in")
        self.assertContains(response, f'value="{self.audio.pk}" selected')

    def test_catalog_shows_all_items_without_filters(self):
        laptop = create_catalog_item("Laptop", category=self.computing)
        speaker = create_catalog_item("Speaker", category=self.audio)

        response = self.client.get(reverse("portal:catalog"))

        self.assertContains(response, laptop.name)
        self.assertContains(response, speaker.name)
        self.assertContains(response, "All categories")

    def test_catalog_searches_by_item_name(self):
        laptop = create_catalog_item("Laptop", category=self.computing)
        speaker = create_catalog_item("Speaker", category=self.audio)

        response = self.client.get(reverse("portal:catalog"), {"q": "laptop"})

        self.assertContains(response, laptop.name)
        self.assertNotContains(response, speaker.name)

    def test_catalog_searches_by_category_name(self):
        laptop = create_catalog_item("Laptop", category=self.computing)
        speaker = create_catalog_item("Speaker", category=self.audio)

        response = self.client.get(reverse("portal:catalog"), {"q": "audio"})

        self.assertContains(response, speaker.name)
        self.assertNotContains(response, laptop.name)

    def test_catalog_combines_search_and_category_filter(self):
        laptop = create_catalog_item("Laptop", category=self.computing)
        audio_laptop = create_catalog_item(
            "Audio Laptop",
            category=self.audio,
        )

        response = self.client.get(
            reverse("portal:catalog"),
            {"q": "laptop", "category": self.computing.pk},
        )

        self.assertContains(response, laptop.name)
        self.assertNotContains(response, audio_laptop.name)

    def test_catalog_lists_only_active_categories_in_filter(self):
        archived = create_category(
            "Retired",
            status=Category.CategoryStatus.ARCHIVED,
        )

        response = self.client.get(reverse("portal:catalog"))

        self.assertContains(response, self.computing.name)
        self.assertContains(response, self.audio.name)
        self.assertNotContains(response, archived.name)

    def test_catalog_handles_empty_search_results(self):
        create_catalog_item("Laptop", category=self.computing)

        response = self.client.get(
            reverse("portal:catalog"),
            {"q": "missing"},
        )

        self.assertContains(response, "No catalog items found")
        self.assertContains(response, "Try a different search.")

    def test_catalog_handles_empty_category(self):
        empty = create_category("Empty")

        response = self.client.get(
            reverse("portal:catalog"),
            {"category": empty.pk},
        )

        self.assertContains(response, "No catalog items found")
        self.assertContains(
            response,
            "There are no active catalog items in this category.",
        )

    def test_admin_cannot_access_catalog(self):
        admin = create_admin()
        self.client.force_login(admin)

        response = self.client.get(reverse("portal:catalog"))

        self.assertRedirects(response, reverse("manage"))


class ManageCatalogTests(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.client.force_login(self.admin)
        self.category = create_category("Electronics")

    def test_admin_create_category_success(self):
        response = self.client.post(
            reverse("catalogs_view", kwargs={"view": "category"}),
            {
                "name": "Robotics",
                "description": "Robotics equipment",
                "status": Category.CategoryStatus.ACTIVE,
            },
        )
        self.assertRedirects(response, reverse("catalogs_view", kwargs={"view": "category"}))
        self.assertTrue(Category.objects.filter(name="Robotics").exists())

    def test_admin_create_category_invalid(self):
        response = self.client.post(
            reverse("catalogs_view", kwargs={"view": "category"}),
            {
                "name": "",
                "description": "Invalid",
                "status": Category.CategoryStatus.ACTIVE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Category.objects.filter(description="Invalid").exists())

    def test_admin_edit_category(self):
        response = self.client.post(
            reverse("catalogs_edit", kwargs={"view": "category", "pk": self.category.pk}),
            {
                "name": "Consumer Electronics",
                "description": "Updated description",
                "status": Category.CategoryStatus.ACTIVE,
            },
        )
        self.assertRedirects(response, reverse("catalogs_view", kwargs={"view": "category"}))
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Consumer Electronics")

    def test_admin_archive_category_get_and_post(self):
        response = self.client.get(
            reverse("catalogs_archive", kwargs={"view": "category", "pk": self.category.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.category.refresh_from_db()
        self.assertEqual(self.category.status, Category.CategoryStatus.ACTIVE)

        response = self.client.post(
            reverse("catalogs_archive", kwargs={"view": "category", "pk": self.category.pk}),
        )
        self.assertRedirects(response, reverse("catalogs_view", kwargs={"view": "category"}))
        self.category.refresh_from_db()
        self.assertEqual(self.category.status, Category.CategoryStatus.ARCHIVED)

    def test_admin_item_catalog_filters_rendered(self):
        response = self.client.get(reverse("catalogs_view", kwargs={"view": "item"}))
        self.assertEqual(response.status_code, 200)
        # Category and status filters must be present
        self.assertContains(response, 'name="category"')
        self.assertContains(response, 'name="status"')
        # Unit-only filters must not be present
        self.assertNotContains(response, 'name="catalog_item"')
        self.assertNotContains(response, 'name="inventory_status"')
        # Filter and Clear buttons must be present
        self.assertContains(response, "Filter")
        self.assertContains(response, "Clear")

    def test_admin_unit_catalog_filters_rendered(self):
        response = self.client.get(reverse("catalogs_view", kwargs={"view": "unit"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="catalog_item"')
        self.assertContains(response, 'name="inventory_status"')
        self.assertContains(response, 'name="category"')

    def test_category_row_links_to_filtered_catalog_items(self):
        other_category = create_category("Audio-Visual")
        electronics_item = create_catalog_item("Digital Multimeter", category=self.category)
        av_item = create_catalog_item("4K Projector", category=other_category)

        cat_response = self.client.get(reverse("catalogs_view", kwargs={"view": "category"}))
        self.assertEqual(cat_response.status_code, 200)
        expected_href = f"{reverse('catalogs_view', kwargs={'view': 'item'})}?category={self.category.pk}"
        self.assertContains(cat_response, f'data-row-href="{expected_href}"')

        filtered_items_response = self.client.get(expected_href)
        self.assertEqual(filtered_items_response.status_code, 200)
        self.assertContains(filtered_items_response, electronics_item.name)
        self.assertNotContains(filtered_items_response, av_item.name)

    def test_catalog_item_row_links_to_filtered_equipment_units(self):
        item1 = create_catalog_item("Epson Projector", category=self.category)
        item2 = create_catalog_item("Fluke Multimeter", category=self.category)
        unit1 = EquipmentUnit.objects.create(
            catalog_item=item1,
            asset_code="PRJ-003",
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )
        unit2 = EquipmentUnit.objects.create(
            catalog_item=item2,
            asset_code="DMM-009",
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
            condition=EquipmentUnit.EquipmentCondition.FINE,
        )

        item_response = self.client.get(reverse("catalogs_view", kwargs={"view": "item"}))
        self.assertEqual(item_response.status_code, 200)
        expected_href = (
            f"{reverse('catalogs_view', kwargs={'view': 'unit'})}"
            f"?category={self.category.pk}&catalog_item={item1.pk}"
        )
        self.assertContains(item_response, f'data-row-href="{expected_href}"')

        filtered_units_response = self.client.get(expected_href)
        self.assertEqual(filtered_units_response.status_code, 200)
        self.assertContains(filtered_units_response, unit1.asset_code)
        self.assertNotContains(filtered_units_response, unit2.asset_code)

    def test_equipment_unit_row_links_to_unit_history_with_borrow_and_maintenance_records(self):
        projector = create_catalog_item("Epson PowerLite Projector", category=self.category)
        unit = EquipmentUnit.objects.create(
            catalog_item=projector,
            asset_code="PRJ-003",
            inventory_status=EquipmentUnit.EquipmentStatus.MAINTENANCE,
            condition=EquipmentUnit.EquipmentCondition.DAMAGED,
        )
        borrower = create_user("john.padilla@example.com")
        borrow_req = create_borrow_request(
            user=borrower,
            purpose="Senior capstone defense presentation",
            status=BorrowRequest.BorrowRequestStatus.RETURNED,
        )
        req_item = create_request_item(borrow_req, projector, quantity=1)
        UnitAllocation.objects.create(
            request_item=req_item,
            equipment_unit=unit,
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
            allocated_at=timezone.now(),
        )
        ReturnRecord.objects.create(
            borrow_request=borrow_req,
            equipment_unit=unit,
            condition=EquipmentUnit.EquipmentCondition.DAMAGED,
        )
        MaintenanceRecord.objects.create(
            maintainer=self.admin,
            unit=unit,
            issue="Cracked HDMI port casing from BorrowRequest.",
            action="Ordered replacement daughterboard port.",
            status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
            resolved_at=timezone.now(),
        )

        unit_list_response = self.client.get(
            reverse("catalogs_view", kwargs={"view": "unit"}),
            {"q": "PRJ-003"},
        )
        self.assertEqual(unit_list_response.status_code, 200)
        history_url = reverse("equipment_unit_history", args=[unit.pk])
        self.assertContains(unit_list_response, f'data-row-href="{history_url}"')

        history_response = self.client.get(history_url)
        self.assertEqual(history_response.status_code, 200)
        self.assertContains(history_response, "PRJ-003")
        self.assertContains(history_response, "Epson PowerLite Projector")
        self.assertContains(history_response, "Senior capstone defense presentation")
        self.assertContains(history_response, "john.padilla@example.com")
        self.assertContains(history_response, "Returned (Damaged)")
        self.assertContains(history_response, "Cracked HDMI port casing from BorrowRequest.")
        self.assertContains(history_response, "Ordered replacement daughterboard port.")
        content = history_response.content.decode("utf-8")
        maint_pos = content.index(f"Maintenance Ticket #")
        return_pos = content.index(f"Returned from Request #{borrow_req.pk}")
        alloc_pos = content.index(f"Allocated to Request #{borrow_req.pk}")
        acq_pos = content.index("Unit PRJ-003 Registered in Inventory")
        self.assertLess(maint_pos, return_pos)
        self.assertLess(return_pos, alloc_pos)
        self.assertLess(alloc_pos, acq_pos)

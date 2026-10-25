from django.test import TestCase
from django.urls import reverse

from app.models import CatalogItem, Category, EquipmentUnit
from app.tests.helpers import (
    create_admin,
    create_catalog_item,
    create_category,
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

    def test_catalog_handles_empty_results(self):
        create_catalog_item("Laptop", category=self.computing)

        response = self.client.get(reverse("portal:catalog"), {"q": "missing"})

        self.assertContains(response, "No catalog items found")

    def test_admin_cannot_access_catalog(self):
        admin = create_admin()
        self.client.force_login(admin)

        response = self.client.get(reverse("portal:catalog"))

        self.assertRedirects(response, reverse("manage"))

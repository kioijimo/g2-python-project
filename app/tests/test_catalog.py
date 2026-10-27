from django.test import TestCase
from django.urls import reverse

from app.models import CatalogItem, Category, EquipmentUnit
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

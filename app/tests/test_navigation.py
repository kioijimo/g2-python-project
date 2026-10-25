import re

from django.test import TestCase
from django.urls import reverse

from app.tests.helpers import create_admin, create_borrow_request, create_user


class UserNavigationTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_user_navbar_links_to_each_core_process(self):
        response = self.client.get(reverse("portal:home"))

        for url_name in (
            "portal:catalog",
            "portal:request_create",
            "portal:request_list",
            "portal:profile",
        ):
            self.assertContains(response, f'href="{reverse(url_name)}"')

    def test_user_navbar_shows_user_role_and_logout(self):
        response = self.client.get(reverse("portal:home"))

        self.assertContains(response, "Signed in as")
        self.assertContains(response, self.user.email)
        self.assertContains(response, "Log out")

    def test_catalog_tab_is_active(self):
        self._assert_active_tab("portal:catalog")

    def test_new_request_tab_is_active(self):
        self._assert_active_tab("portal:request_create")

    def test_request_list_tab_is_active(self):
        self._assert_active_tab("portal:request_list")

    def test_request_detail_highlights_my_requests_tab(self):
        borrow_request = create_borrow_request(self.user)
        response = self.client.get(
            reverse("portal:request_detail", args=[borrow_request.pk])
        )
        content = response.content.decode()

        self.assertRegex(
            content,
            rf'href="{re.escape(reverse("portal:request_list"))}"\s+aria-current="page"',
        )

    def test_profile_tab_is_active(self):
        self._assert_active_tab("portal:profile")

    def _assert_active_tab(self, url_name):
        response = self.client.get(reverse(url_name))
        content = response.content.decode()

        self.assertEqual(content.count('aria-current="page"'), 1)
        self.assertRegex(
            content,
            rf'href="{re.escape(reverse(url_name))}"\s+aria-current="page"',
        )


class AdminNavigationTests(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.client.force_login(self.admin)

    def test_admin_does_not_see_user_portal_tabs(self):
        response = self.client.get(reverse("manage"))

        for url_name in (
            "portal:catalog",
            "portal:request_create",
            "portal:request_list",
            "portal:profile",
        ):
            self.assertNotContains(response, reverse(url_name))

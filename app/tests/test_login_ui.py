from django.test import Client, TestCase
from django.urls import reverse

from app.models import User


class LoginUIRedesignTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="DemoPass123!",
        )
        self.basic_user = User.objects.create_user(
            email="user@example.com",
            password="DemoPass123!",
        )

    def test_login_page_renders_with_design_system_and_simplified_form(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        # 1. Check Brand Center Stack
        self.assertIn("CAMPUS EQUIPMENT", content)
        self.assertIn("BORROWING & INVENTORY SYSTEM", content)
        self.assertIn("typewriter-target", content)

        # 2. Check BulSU Crimson & Gold Design System Colors & Gradients
        self.assertIn("radial-gradient", content)
        self.assertIn("#AE0014", content)
        self.assertIn("#800000", content)
        self.assertIn("bg-brand-primary", content)

        # 3. Check Form Side & Elements
        self.assertIn("Sign in", content)
        self.assertIn("password-toggle-btn", content)
        self.assertIn("m@example.com", content)

        # 4. Confirm "Remember me" and "Forgot password" are REMOVED
        self.assertNotIn("Remember me", content)
        self.assertNotIn("Forgot password", content)

        # 5. Check Responsive Panels
        self.assertIn("w-[60%]", content)
        self.assertIn("md:w-[40%]", content)

    def test_login_submission_admin(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin@example.com", "password": "DemoPass123!"},
        )
        self.assertRedirects(response, reverse("manage"))

    def test_login_submission_basic_user(self):
        response = self.client.post(
            reverse("login"),
            {"username": "user@example.com", "password": "DemoPass123!"},
        )
        self.assertRedirects(response, reverse("portal:home"))

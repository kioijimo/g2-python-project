from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import (
    BorrowRequest,
    Category,
    CatalogItem,
    EquipmentUnit,
    MaintenanceRecord,
    User,
)
from app.tests.helpers import (
    create_admin,
    create_borrow_request,
    create_catalog_item,
    create_request_item,
    create_user,
)


class UnifiedConfirmModalTests(TestCase):
    def setUp(self):
        self.admin = create_admin("admin_modal@example.com")
        self.user = create_user("student_modal@example.com")

        self.item = create_catalog_item(
            name="Digital Multimeter",
        )
        self.unit = EquipmentUnit.objects.create(
            catalog_item=self.item,
            asset_code="MODAL-001",
            condition=EquipmentUnit.EquipmentCondition.FINE,
            inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE,
        )

    def test_modal_rendered_in_base_template(self):
        """Unified confirmation modal markup and script should be rendered on pages extending base.html."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"))
        self.assertEqual(response.status_code, 200)

        # Check modal container & accessibility attributes
        self.assertContains(response, 'id="unified-confirm-modal"')
        self.assertContains(response, 'role="dialog"')
        self.assertContains(response, 'aria-modal="true"')
        self.assertContains(response, 'aria-labelledby="confirm-modal-title"')
        self.assertContains(response, 'aria-describedby="confirm-modal-message"')
        self.assertContains(response, 'id="confirm-modal-confirm-btn"')
        self.assertContains(response, 'id="confirm-modal-cancel-btn"')
        self.assertContains(response, 'window.showConfirmModal')

    def test_account_list_deactivate_and_activate_have_confirm_attributes(self):
        """Account list should have declarative data-confirm attributes on deactivate and activate forms."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("account_list"))
        self.assertEqual(response.status_code, 200)

        # Deactivate form check
        self.assertContains(response, 'action="{}"'.format(reverse("deactivate_user", args=[self.user.pk])))
        self.assertContains(response, 'data-confirm="true"')
        self.assertContains(response, 'data-confirm-title="Deactivate User Account"')
        self.assertContains(response, 'data-confirm-variant="danger"')
        self.assertContains(response, 'data-confirm-button="Deactivate Account"')
        self.assertContains(response, 'data-confirm-detail="student_modal@example.com"')

        # Deactivate user, then check activate form
        self.user.is_active = False
        self.user.status = User.UserStatus.INACTIVE
        self.user.save()

        response = self.client.get(reverse("account_list"))
        self.assertContains(response, 'action="{}"'.format(reverse("activate_user", args=[self.user.pk])))
        self.assertContains(response, 'data-confirm-title="Activate User Account"')
        self.assertContains(response, 'data-confirm-variant="success"')
        self.assertContains(response, 'data-confirm-button="Activate Account"')

    def test_portal_request_cancel_has_confirm_attributes(self):
        """Cancel borrow request in portal should have declarative data-confirm attributes."""
        borrow_req = create_borrow_request(self.user, status=BorrowRequest.BorrowRequestStatus.PENDING)
        self.client.force_login(self.user)

        response = self.client.get(reverse("portal:request_detail", args=[borrow_req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="{}"'.format(reverse("portal:request_cancel", args=[borrow_req.pk])))
        self.assertContains(response, 'data-confirm="true"')
        self.assertContains(response, 'data-confirm-title="Cancel Borrow Request"')
        self.assertContains(response, 'data-confirm-variant="danger"')
        self.assertContains(response, 'data-confirm-button="Yes, Cancel Request"')

    def test_borrow_request_review_reject_and_release_have_confirm_attributes(self):
        """Borrow request review actions should have declarative data-confirm attributes."""
        borrow_req = create_borrow_request(self.user, status=BorrowRequest.BorrowRequestStatus.PENDING)
        req_item = create_request_item(borrow_req, self.item, quantity=1)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("borrow_request_review", args=[borrow_req.pk]))
        self.assertEqual(response.status_code, 200)

        # Reject form confirmation
        self.assertContains(response, 'action="{}"'.format(reverse("borrow_request_reject", args=[borrow_req.pk])))
        self.assertContains(response, 'data-confirm-title="Reject Borrow Request"')
        self.assertContains(response, 'data-confirm-variant="danger"')
        self.assertContains(response, 'data-confirm-button="Reject Request"')

        # Transition to APPROVED to test release form
        borrow_req.status = BorrowRequest.BorrowRequestStatus.APPROVED
        borrow_req.save()

        response = self.client.get(reverse("borrow_request_review", args=[borrow_req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="{}"'.format(reverse("borrow_request_release", args=[borrow_req.pk])))
        self.assertContains(response, 'data-confirm-title="Release Equipment Units"')
        self.assertContains(response, 'data-confirm-variant="primary"')
        self.assertContains(response, 'data-confirm-button="Confirm & Release Equipment"')

    def test_maintenance_repair_and_retire_have_confirm_attributes(self):
        """Maintenance resolution buttons should have declarative data-confirm attributes."""
        ticket = MaintenanceRecord.objects.create(
            maintainer=self.admin,
            unit=self.unit,
            issue="Frayed power cable",
            action="",
            status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
            resolved_at=timezone.now(),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("manage_maintenance"))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'data-confirm-title="Repair & Restock Equipment"')
        self.assertContains(response, 'data-confirm-variant="success"')
        self.assertContains(response, 'data-confirm-button="Restock Unit"')

        self.assertContains(response, 'data-confirm-title="Retire Equipment Unit"')
        self.assertContains(response, 'data-confirm-variant="danger"')
        self.assertContains(response, 'data-confirm-button="Retire Unit"')

        # Ensure the inline input field is removed from the table and shown inside the resolve modal instead
        self.assertNotContains(response, '<input type="text" name="action"')
        self.assertContains(response, 'id="resolveTicketModal"')
        self.assertContains(response, 'id="resolveModalActionInput"')
        self.assertContains(response, 'openResolveTicketModal(this)')

    def test_navbars_have_logout_confirm_attributes(self):
        """Both admin and user navbars should protect logout with confirmation."""
        # Admin navbar
        self.client.force_login(self.admin)
        response = self.client.get(reverse("manage"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-confirm-title="Sign Out"')
        self.assertContains(response, 'data-confirm-variant="warning"')

        # User navbar
        self.client.force_login(self.user)
        response = self.client.get(reverse("portal:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-confirm-title="Sign Out"')
        self.assertContains(response, 'data-confirm-variant="warning"')

    def test_functional_deactivate_and_activate_user(self):
        """Backend POST requests for activate/deactivate continue to function seamlessly."""
        self.client.force_login(self.admin)

        # Deactivate
        resp = self.client.post(reverse("deactivate_user", args=[self.user.pk]))
        self.assertRedirects(resp, reverse("account_list"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

        # Activate
        resp = self.client.post(reverse("activate_user", args=[self.user.pk]))
        self.assertRedirects(resp, reverse("account_list"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_functional_cancel_borrow_request(self):
        """Backend POST request for request cancellation functions properly."""
        borrow_req = create_borrow_request(self.user, status=BorrowRequest.BorrowRequestStatus.PENDING)
        self.client.force_login(self.user)

        resp = self.client.post(reverse("portal:request_cancel", args=[borrow_req.pk]))
        self.assertRedirects(resp, reverse("portal:request_detail", args=[borrow_req.pk]))
        borrow_req.refresh_from_db()
        self.assertEqual(borrow_req.status, BorrowRequest.BorrowRequestStatus.CANCELLED)

    def test_functional_resolve_maintenance_outcomes(self):
        """Backend POST requests with outcome=REPAIR and outcome=RETIRE resolve correctly."""
        self.client.force_login(self.admin)

        # Test REPAIR
        ticket_repair = MaintenanceRecord.objects.create(
            maintainer=self.admin,
            unit=self.unit,
            issue="Issue 1",
            action="",
            status=MaintenanceRecord.MaintenanceStatus.ACTIVE,
            resolved_at=timezone.now(),
        )
        resp = self.client.post(
            reverse("resolve_maintenance_ticket", args=[ticket_repair.id]),
            {"action": "Fixed cable", "outcome": "REPAIR"},
        )
        self.assertEqual(resp.status_code, 302)
        ticket_repair.refresh_from_db()
        self.assertEqual(ticket_repair.status, MaintenanceRecord.MaintenanceStatus.FINISHED)
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.inventory_status, EquipmentUnit.EquipmentStatus.AVAILABLE)

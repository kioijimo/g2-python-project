from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from app.models import AuditLog, BorrowRequest, LoanRecord
from app.services.approvals import reject_borrow_request
from app.tests.helpers import (
    create_admin,
    create_borrow_request,
    create_catalog_item,
    create_category,
    create_request_item,
    create_user,
)


class BorrowRequestReviewRejectTests(TestCase):
    def setUp(self):
        self.admin = create_admin("admin.approver@bulsu.edu.ph")
        self.borrower = create_user("student.borrower@bulsu.edu.ph")
        self.category = create_category("Electronics")
        self.catalog_item = create_catalog_item("Digital Multimeter", category=self.category)

    def _create_pending_request(self, purpose="Laboratory Circuit Analysis"):
        req = create_borrow_request(self.borrower, purpose=purpose)
        create_request_item(req, self.catalog_item, quantity=1)
        return req

    def test_reject_without_reason_fails_validation_and_redirects(self):
        """Rejecting without providing a reason fails validation and keeps request pending."""
        req = self._create_pending_request()
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("borrow_request_reject", args=[req.pk]),
            {"rejection_reason": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide a reason for rejecting the request.")
        req.refresh_from_db()
        self.assertEqual(req.status, BorrowRequest.BorrowRequestStatus.PENDING)
        self.assertEqual(req.rejection_reason, "")
        self.assertFalse(LoanRecord.objects.filter(borrow_request=req).exists())

    def test_reject_with_whitespace_reason_fails_validation(self):
        """Rejecting with only whitespace in the reason field is treated as empty."""
        req = self._create_pending_request()
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("borrow_request_reject", args=[req.pk]),
            {"rejection_reason": "   \n\t  "},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide a reason for rejecting the request.")
        req.refresh_from_db()
        self.assertEqual(req.status, BorrowRequest.BorrowRequestStatus.PENDING)

    def test_reject_with_valid_reason_succeeds(self):
        """Rejecting with a valid reason updates status, persists reason, creates LoanRecord and AuditLog."""
        req = self._create_pending_request()
        self.client.force_login(self.admin)
        reason_text = "Units are currently reserved for the upcoming College Accreditation inspection."

        response = self.client.post(
            reverse("borrow_request_reject", args=[req.pk]),
            {"rejection_reason": reason_text},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Borrow request rejected with reason provided.")

        req.refresh_from_db()
        self.assertEqual(req.status, BorrowRequest.BorrowRequestStatus.REJECTED)
        self.assertEqual(req.rejection_reason, reason_text)

        # Review record created
        loan_record = LoanRecord.objects.filter(borrow_request=req).first()
        self.assertIsNotNone(loan_record)
        self.assertEqual(loan_record.user, self.admin)
        self.assertIsNone(loan_record.released_at)

        # Audit log created with borrower email and reason
        audit = AuditLog.objects.filter(user=self.admin).order_by("-pk").first()
        self.assertIsNotNone(audit)
        self.assertIn(f"Rejected borrow request #{req.pk}", audit.action)
        self.assertIn(self.borrower.email, audit.action)
        self.assertIn(reason_text, audit.action)

    def test_service_reject_borrow_request_requires_reason(self):
        """Service function reject_borrow_request enforces non-empty reason parameter."""
        req = self._create_pending_request()

        with self.assertRaises(ValidationError) as ctx:
            reject_borrow_request(req, self.admin, reason="")
        self.assertIn("Please provide a reason", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            reject_borrow_request(req, self.admin, reason="   ")
        self.assertIn("Please provide a reason", str(ctx.exception))

    def test_reject_non_pending_request_fails(self):
        """Only pending requests can be rejected."""
        req = self._create_pending_request()
        req.status = BorrowRequest.BorrowRequestStatus.APPROVED
        req.save()

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("borrow_request_reject", args=[req.pk]),
            {"rejection_reason": "No longer needed."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only pending requests can be rejected.")
        req.refresh_from_db()
        self.assertEqual(req.status, BorrowRequest.BorrowRequestStatus.APPROVED)

    def test_non_admin_cannot_reject_request(self):
        """Regular non-admin users cannot call the reject endpoint."""
        req = self._create_pending_request()
        self.client.force_login(self.borrower)

        response = self.client.post(
            reverse("borrow_request_reject", args=[req.pk]),
            {"rejection_reason": "Trying to reject."},
        )

        # Non-admin redirected by @admin_required
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, BorrowRequest.BorrowRequestStatus.PENDING)

    def test_review_page_renders_rejection_textarea_when_pending(self):
        """Review page for a pending request renders the rejection reason textarea and required label."""
        req = self._create_pending_request()
        self.client.force_login(self.admin)

        response = self.client.get(reverse("borrow_request_review", args=[req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="rejection_reason"')
        self.assertContains(response, "Reason for Rejection")
        self.assertContains(response, "required")

    def test_review_page_renders_saved_rejection_reason_when_rejected(self):
        """Review page for an already rejected request displays the saved rejection reason."""
        req = self._create_pending_request()
        reason_text = "Insufficient justification provided for high-end equipment."
        reject_borrow_request(req, self.admin, reason=reason_text)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("borrow_request_review", args=[req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rejection reason")
        self.assertContains(response, reason_text)

    def test_portal_request_detail_displays_rejection_reason(self):
        """Borrower viewing their request in the portal sees the rejection reason banner."""
        req = self._create_pending_request()
        reason_text = "Required lab documentation was missing from the attachment."
        reject_borrow_request(req, self.admin, reason=reason_text)

        self.client.force_login(self.borrower)
        response = self.client.get(reverse("portal:request_detail", args=[req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reason for Rejection:")
        self.assertContains(response, reason_text)

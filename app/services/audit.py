from ..models import DESCRIPTION_LENGTH, AuditLog


def record_audit(actor, action):
    """Audits an action from a user with ADMIN role to the audit history."""
    return AuditLog.objects.create(
        user=actor,
        action=action[:DESCRIPTION_LENGTH],
    )

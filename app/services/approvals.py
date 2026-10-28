from collections import Counter

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import (
    BorrowRequest,
    EquipmentUnit,
    LoanRecord,
    UnitAllocation,
    User,
)
from .audit import record_audit


def _require_active_admin(actor):
    if not actor.is_authenticated or not actor.is_active:
        raise ValidationError("Only active administrators can perform this action.")
    if actor.role != User.UserRoles.ADMIN:
        raise ValidationError("Only administrators can perform this action.")


def _locked_request(borrow_request):
    return BorrowRequest.objects.select_for_update().get(pk=borrow_request.pk)


def _normalise_unit_ids(raw_ids):
    unit_ids = []
    for raw_id in raw_ids:
        try:
            unit_ids.append(int(raw_id))
        except (TypeError, ValueError):
            raise ValidationError("Select valid equipment units.")
    if len(set(unit_ids)) != len(unit_ids):
        raise ValidationError("Each equipment unit can only be selected once.")
    return unit_ids


def _collect_allocations(borrow_request, allocations_by_item):
    """Validate selected units and return them grouped by request item."""
    items = list(borrow_request.items.select_related("catalog_item").order_by("pk"))
    if not items:
        raise ValidationError("This request has no catalog items to allocate.")

    selected_unit_ids = set()
    validated = []

    for request_item in items:
        unit_ids = _normalise_unit_ids(allocations_by_item.get(request_item.pk, []))
        if len(unit_ids) != request_item.quantity:
            raise ValidationError(
                f"Select exactly {request_item.quantity} unit(s) for "
                f"{request_item.catalog_item.name}."
            )

        duplicate_ids = selected_unit_ids.intersection(unit_ids)
        if duplicate_ids:
            raise ValidationError(
                "The same equipment unit cannot be allocated more than once."
            )
        selected_unit_ids.update(unit_ids)

        units = list(
            EquipmentUnit.objects.select_for_update()
            .filter(pk__in=unit_ids)
            .order_by("pk")
        )
        units_by_id = {unit.pk: unit for unit in units}

        if len(units_by_id) != len(unit_ids):
            raise ValidationError("One or more selected equipment units do not exist.")

        for unit_id in unit_ids:
            unit = units_by_id[unit_id]
            if unit.catalog_item_id != request_item.catalog_item_id:
                raise ValidationError(
                    f"{unit.asset_code} does not belong to "
                    f"{request_item.catalog_item.name}."
                )
            if unit.condition != EquipmentUnit.EquipmentCondition.FINE:
                raise ValidationError(f"{unit.asset_code} is not in fine condition.")
            if unit.inventory_status != EquipmentUnit.EquipmentStatus.AVAILABLE:
                raise ValidationError(f"{unit.asset_code} is no longer available.")

        validated.append((request_item, [units_by_id[unit_id] for unit_id in unit_ids]))

    return validated


def approve_borrow_request(borrow_request, actor, allocations_by_item):
    """Approve a pending request and reserve the selected physical units."""
    _require_active_admin(actor)

    with transaction.atomic():
        request = _locked_request(borrow_request)

        if request.status != BorrowRequest.BorrowRequestStatus.PENDING:
            raise ValidationError("Only pending requests can be approved.")

        validated = _collect_allocations(request, allocations_by_item)
        now = timezone.now()

        try:
            with transaction.atomic():
                UnitAllocation.objects.bulk_create(
                    [
                        UnitAllocation(
                            request_item=request_item,
                            equipment_unit=unit,
                            status=UnitAllocation.UnitAllocationStatus.PENDING,
                            allocated_at=now,
                        )
                        for request_item, units in validated
                        for unit in units
                    ]
                )
        except IntegrityError:
            raise ValidationError(
                "One or more selected equipment units are already allocated."
            ) from None

        unit_ids = [unit.pk for _, units in validated for unit in units]
        EquipmentUnit.objects.filter(pk__in=unit_ids).update(
            inventory_status=EquipmentUnit.EquipmentStatus.RESERVED
        )

        request.status = BorrowRequest.BorrowRequestStatus.APPROVED
        request.save(update_fields=["status"])

        LoanRecord.objects.create(
            borrow_request=request,
            user=actor,
        )

        record_audit(
            actor, f"Approved borrow request #{request.pk} from user {actor.email}."
        )

    return request


def reject_borrow_request(borrow_request, actor):
    """Reject a pending request."""
    _require_active_admin(actor)

    with transaction.atomic():
        request = _locked_request(borrow_request)

        if request.status != BorrowRequest.BorrowRequestStatus.PENDING:
            raise ValidationError("Only pending requests can be rejected.")

        request.status = BorrowRequest.BorrowRequestStatus.REJECTED
        request.save(update_fields=["status"])

        LoanRecord.objects.create(
            borrow_request=request,
            user=actor,
        )

        record_audit(
            actor, f"Rejected borrow request #{request.pk} from user {actor.email}."
        )

    return request


def release_borrow_request(borrow_request, actor):
    """Convert a fully allocated approved request into an issued loan."""
    _require_active_admin(actor)

    with transaction.atomic():
        request = _locked_request(borrow_request)

        if request.status == BorrowRequest.BorrowRequestStatus.ISSUED:
            raise ValidationError("This request has already been released.")
        if request.status != BorrowRequest.BorrowRequestStatus.APPROVED:
            raise ValidationError("Only approved requests can be released.")

        loan = (
            LoanRecord.objects.select_for_update()
            .filter(borrow_request=request)
            .first()
        )
        if loan is None:
            raise ValidationError("Approve the request before releasing its equipment.")
        if loan.released_at is not None:
            raise ValidationError("This request has already been released.")

        allocations = list(
            UnitAllocation.objects.select_for_update()
            .filter(
                request_item__borrow_request=request,
                status=UnitAllocation.UnitAllocationStatus.PENDING,
            )
            .select_related("equipment_unit", "request_item")
            .order_by("pk")
        )

        if not allocations:
            raise ValidationError(
                "Allocate equipment units before releasing this request."
            )

        counts = Counter(allocation.request_item_id for allocation in allocations)
        items = list(request.items.order_by("pk"))

        for request_item in items:
            if counts[request_item.pk] != request_item.quantity:
                raise ValidationError(
                    f"{request_item.catalog_item.name} is not fully allocated."
                )

        for allocation in allocations:
            if (
                allocation.equipment_unit.inventory_status
                != EquipmentUnit.EquipmentStatus.RESERVED
            ):
                raise ValidationError(
                    f"{allocation.equipment_unit.asset_code} is not reserved for "
                    "this request."
                )

        now = timezone.now()
        loan.released_at = now
        loan.save(update_fields=["released_at"])

        UnitAllocation.objects.filter(
            pk__in=[allocation.pk for allocation in allocations]
        ).update(
            status=UnitAllocation.UnitAllocationStatus.RELEASED,
        )

        EquipmentUnit.objects.filter(
            pk__in=[allocation.equipment_unit_id for allocation in allocations]
        ).update(inventory_status=EquipmentUnit.EquipmentStatus.ISSUED)

        request.status = BorrowRequest.BorrowRequestStatus.ISSUED
        request.save(update_fields=["status"])

        record_audit(
            actor,
            f"Released borrow request #{request.pk} as a loan for user {actor.email}.",
        )

    return loan

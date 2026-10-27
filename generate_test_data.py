import os
import sys
from datetime import timedelta

import django
from django.utils import timezone

sys.path.insert(0, '/home/kioijimo/Projects/g2-equipment-system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app import models

User = models.User
Profile = models.Profile
Category = models.Category
CatalogItem = models.CatalogItem
EquipmentUnit = models.EquipmentUnit
BorrowRequest = models.BorrowRequest
RequestItem = models.RequestItem
LoanRecord = models.LoanRecord
UnitAllocation = models.UnitAllocation

UnitAllocation.objects.all().delete()
LoanRecord.objects.all().delete()
RequestItem.objects.all().delete()
BorrowRequest.objects.all().delete()
EquipmentUnit.objects.all().delete()
CatalogItem.objects.all().delete()
Category.objects.all().delete()
Profile.objects.all().delete()
User.objects.all().delete()

admin = User.objects.create_user(email='admin@test.com', password='pass1234')
admin.role = User.UserRoles.ADMIN
admin.status = User.UserStatus.ACTIVE
admin.save()
Profile.objects.create(user=admin, name='Admin User', contact_number='09171234567')

user1 = User.objects.create_user(email='alice@test.com', password='pass1234')
user1.role = User.UserRoles.USER
user1.status = User.UserStatus.ACTIVE
user1.save()
Profile.objects.create(user=user1, name='Alice Santos', contact_number='09181234567')

user2 = User.objects.create_user(email='bob@test.com', password='pass1234')
user2.role = User.UserRoles.USER
user2.status = User.UserStatus.ACTIVE
user2.save()
Profile.objects.create(user=user2, name='Bob Cruz', contact_number='09191234567')

cat_electronics = Category.objects.create(name='Electronics', description='Electronic devices', status=Category.CategoryStatus.ACTIVE)
cat_lab = Category.objects.create(name='Lab Equipment', description='Laboratory tools', status=Category.CategoryStatus.ACTIVE)
cat_audio = Category.objects.create(name='Audio', description='Audio equipment', status=Category.CategoryStatus.ACTIVE)

laptop = CatalogItem.objects.create(name='Laptop', description='14-inch laptop', category=cat_electronics, status=CatalogItem.CatalogItemStatus.ACTIVE)
projector = CatalogItem.objects.create(name='Projector', description='HD projector', category=cat_electronics, status=CatalogItem.CatalogItemStatus.ACTIVE)
multimeter = CatalogItem.objects.create(name='Multimeter', description='Digital multimeter', category=cat_lab, status=CatalogItem.CatalogItemStatus.ACTIVE)
mic = CatalogItem.objects.create(name='Microphone', description='Wireless microphone', category=cat_audio, status=CatalogItem.CatalogItemStatus.ACTIVE)

EquipmentUnit.objects.create(asset_code='LAP-001', catalog_item=laptop, inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE, condition=EquipmentUnit.EquipmentCondition.FINE)
EquipmentUnit.objects.create(asset_code='LAP-002', catalog_item=laptop, inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE, condition=EquipmentUnit.EquipmentCondition.FINE)
EquipmentUnit.objects.create(asset_code='LAP-003', catalog_item=laptop, inventory_status=EquipmentUnit.EquipmentStatus.MAINTENANCE, condition=EquipmentUnit.EquipmentCondition.DAMAGED)
EquipmentUnit.objects.create(asset_code='PRJ-001', catalog_item=projector, inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE, condition=EquipmentUnit.EquipmentCondition.FINE)
EquipmentUnit.objects.create(asset_code='PRJ-002', catalog_item=projector, inventory_status=EquipmentUnit.EquipmentStatus.RESERVED, condition=EquipmentUnit.EquipmentCondition.FINE)
EquipmentUnit.objects.create(asset_code='MUL-001', catalog_item=multimeter, inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE, condition=EquipmentUnit.EquipmentCondition.FINE)
EquipmentUnit.objects.create(asset_code='MUL-002', catalog_item=multimeter, inventory_status=EquipmentUnit.EquipmentStatus.ISSUED, condition=EquipmentUnit.EquipmentCondition.FINE)
EquipmentUnit.objects.create(asset_code='MIC-001', catalog_item=mic, inventory_status=EquipmentUnit.EquipmentStatus.AVAILABLE, condition=EquipmentUnit.EquipmentCondition.FINE)
EquipmentUnit.objects.create(asset_code='MIC-002', catalog_item=mic, inventory_status=EquipmentUnit.EquipmentStatus.RETIRED, condition=EquipmentUnit.EquipmentCondition.DAMAGED)

now = timezone.now()

br1 = BorrowRequest.objects.create(user=user1, purpose='Group presentation', status=BorrowRequest.BorrowRequestStatus.PENDING, due_at=now + timedelta(days=7))
RequestItem.objects.create(borrow_request=br1, catalog_item=laptop, quantity=2)
RequestItem.objects.create(borrow_request=br1, catalog_item=projector, quantity=1)

br2 = BorrowRequest.objects.create(user=user1, purpose='Thesis defense prep', status=BorrowRequest.BorrowRequestStatus.APPROVED, due_at=now + timedelta(days=3))
RequestItem.objects.create(borrow_request=br2, catalog_item=mic, quantity=1)

br3 = BorrowRequest.objects.create(user=user2, purpose='Lab experiment', status=BorrowRequest.BorrowRequestStatus.ISSUED, due_at=now - timedelta(days=2))
RequestItem.objects.create(borrow_request=br3, catalog_item=multimeter, quantity=1)
RequestItem.objects.create(borrow_request=br3, catalog_item=projector, quantity=1)

br4 = BorrowRequest.objects.create(user=user2, purpose='Class activity', status=BorrowRequest.BorrowRequestStatus.PARTIALLY_RETURNED, due_at=now + timedelta(days=5))
RequestItem.objects.create(borrow_request=br4, catalog_item=laptop, quantity=1)

br5 = BorrowRequest.objects.create(user=user1, purpose='Workshop', status=BorrowRequest.BorrowRequestStatus.RETURNED, due_at=now - timedelta(days=1))
RequestItem.objects.create(borrow_request=br5, catalog_item=mic, quantity=1)

br6 = BorrowRequest.objects.create(user=user2, purpose='Personal use', status=BorrowRequest.BorrowRequestStatus.REJECTED, due_at=now + timedelta(days=7))
RequestItem.objects.create(borrow_request=br6, catalog_item=laptop, quantity=1)

br7 = BorrowRequest.objects.create(user=user1, purpose='Changed plans', status=BorrowRequest.BorrowRequestStatus.CANCELLED, due_at=now + timedelta(days=7))
RequestItem.objects.create(borrow_request=br7, catalog_item=projector, quantity=1)

loan3 = LoanRecord.objects.create(borrow_request=br3, user=user2, released_by=admin, released_at=now - timedelta(days=5), due_at=br3.due_at)
UnitAllocation.objects.create(loan_record=loan3, equipment_unit=EquipmentUnit.objects.get(asset_code='MUL-002'), request_item=br3.items.get(catalog_item=multimeter), status=UnitAllocation.UnitAllocationStatus.RELEASED)
UnitAllocation.objects.create(loan_record=loan3, equipment_unit=EquipmentUnit.objects.get(asset_code='PRJ-002'), request_item=br3.items.get(catalog_item=projector), status=UnitAllocation.UnitAllocationStatus.RELEASED)

loan4 = LoanRecord.objects.create(borrow_request=br4, user=user2, released_by=admin, released_at=now - timedelta(days=3), due_at=br4.due_at)
UnitAllocation.objects.create(loan_record=loan4, equipment_unit=EquipmentUnit.objects.get(asset_code='LAP-001'), request_item=br4.items.get(catalog_item=laptop), status=UnitAllocation.UnitAllocationStatus.RETURNED, returned_at=now - timedelta(days=1), received_by=admin)

loan5 = LoanRecord.objects.create(borrow_request=br5, user=user1, released_by=admin, released_at=now - timedelta(days=10), due_at=br5.due_at)
UnitAllocation.objects.create(loan_record=loan5, equipment_unit=EquipmentUnit.objects.get(asset_code='MIC-001'), request_item=br5.items.get(catalog_item=mic), status=UnitAllocation.UnitAllocationStatus.RETURNED, returned_at=now - timedelta(days=2), received_by=admin)

print('Done creating test data')
print('Users:', User.objects.count())
print('Categories:', Category.objects.count())
print('CatalogItems:', CatalogItem.objects.count())
print('EquipmentUnits:', EquipmentUnit.objects.count())
print('BorrowRequests:', BorrowRequest.objects.count())
print('RequestItems:', RequestItem.objects.count())
print('LoanRecords:', LoanRecord.objects.count())
print('UnitAllocations:', UnitAllocation.objects.count())

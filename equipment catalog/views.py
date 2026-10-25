from django.shortcuts import render

from .models import Category
from .models import CatalogItem
from .models import EquipmentUnit


def unit_list(request):

    units = EquipmentUnit.objects.all()

    category = request.GET.get('category')
    item = request.GET.get('item')
    status = request.GET.get('status')

    if category:
        units = units.filter(
            catalog_item__category_id=category
        )

    if item:
        units = units.filter(
            catalog_item_id=item
        )

    if status:
        units = units.filter(
            status=status
        )

    context = {
        'units': units,
        'categories': Category.objects.all(),
        'items': CatalogItem.objects.all()
    }

    return render(
        request,
        'equipment/unit_list.html',
        context
    )
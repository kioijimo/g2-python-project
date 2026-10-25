from django.forms import ModelForm

from .models import Category
from .models import CatalogItem
from .models import EquipmentUnit


class CategoryForm(ModelForm):

    class Meta:
        model = Category
        fields = '__all__'


class CatalogItemForm(ModelForm):

    class Meta:
        model = CatalogItem
        fields = [
            'category',
            'name',
            'description'
        ]


class EquipmentUnitForm(ModelForm):

    class Meta:
        model = EquipmentUnit
        fields = [
            'catalog_item',
            'asset_code',
            'condition',
            'acquisition_date',
            'status'
        ]
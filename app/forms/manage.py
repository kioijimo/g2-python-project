from django import forms
from django.contrib.auth.password_validation import validate_password

from .. import models
from .styling import apply_widget_styling


def _status_choices(status_choices, empty_label="All statuses"):
    return [("", empty_label)] + [(value, label) for value, label in status_choices]


class UserForm(forms.ModelForm):
    class Meta:
        model = models.User
        exclude = ("status", "last_login")

    password = forms.CharField(
        widget=forms.PasswordInput(), validators=[validate_password]
    )

    def __init__(self, *args, authorized=False, **kwargs):
        super().__init__(*args, **kwargs)

        if not authorized and "role" in self.fields:
            del self.fields["role"]

        self.field_order = [
            "email",
            "password",
        ]

        self.order_fields(self.field_order)
        apply_widget_styling(self)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class BorrowRequestFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={"placeholder": "Search borrower, purpose, or request ID"}
        ),
    )
    status = forms.TypedChoiceField(
        required=False,
        label="Status",
        choices=_status_choices(models.BorrowRequest.BorrowRequestStatus.choices),
        coerce=int,
        empty_value=None,
    )
    date_from = forms.DateField(
        required=False,
        label="Created from",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    date_to = forms.DateField(
        required=False,
        label="Created to",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class AccountSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search Users",
        widget=forms.TextInput(
            attrs={"placeholder": "Search by email, name, or contact number..."}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class AuditLogSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={"placeholder": "Search for admin email or audit action"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = models.SystemSetting
        fields = ("max_borrow_days", "max_borrow_quantity")
        labels = {
            "max_borrow_days": "Max borrow days",
            "max_borrow_quantity": "Max quantity",
        }
        help_texts = {
            "max_borrow_days": "Maximum allowed days a borrower can keep equipment.",
            "max_borrow_quantity": "Maximum allowed units a borrower can request per item.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class CategoryFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Search categories"}),
    )
    status = forms.TypedChoiceField(
        required=False,
        label="Status",
        choices=_status_choices(models.Category.CategoryStatus.choices),
        coerce=int,
        empty_value=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class CatalogItemFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Search catalog items"}),
    )
    category = forms.ModelChoiceField(
        required=False,
        label="Category",
        queryset=models.Category.objects.none(),
        empty_label="All categories",
    )
    status = forms.TypedChoiceField(
        required=False,
        label="Status",
        choices=_status_choices(models.CatalogItem.CatalogItemStatus.choices),
        coerce=int,
        empty_value=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = models.Category.objects.order_by("name")
        apply_widget_styling(self)


class EquipmentUnitFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Search asset codes"}),
    )
    category = forms.ModelChoiceField(
        required=False,
        label="Category",
        queryset=models.Category.objects.none(),
        empty_label="All categories",
    )
    catalog_item = forms.ModelChoiceField(
        required=False,
        label="Catalog item",
        queryset=models.CatalogItem.objects.none(),
        empty_label="All catalog items",
    )
    inventory_status = forms.TypedChoiceField(
        required=False,
        label="Status",
        choices=_status_choices(models.EquipmentUnit.EquipmentStatus.choices),
        coerce=int,
        empty_value=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = models.Category.objects.order_by("name")
        self.fields[
            "catalog_item"
        ].queryset = models.CatalogItem.objects.select_related("category").order_by(
            "category__name", "name"
        )
        self.fields["catalog_item"].label_from_instance = lambda item: (
            f"{item.name} ({item.category.name})"
        )
        apply_widget_styling(self)


class CategoryForm(forms.ModelForm):
    description = forms.CharField(
        required=False,
        label="Description",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Write a brief, meaningful description",
                "rows": 6,
            }
        ),
    )

    class Meta:
        model = models.Category
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class CatalogItemForm(forms.ModelForm):
    class Meta:
        model = models.CatalogItem
        exclude = ()

    def __init__(self, *args, categories=None, status=None, **kwargs):
        super().__init__(*args, **kwargs)

        queryset = categories
        if queryset is None:
            queryset = models.Category.objects.all()
            if status is not None:
                queryset = queryset.filter(status=status)

        self.fields["category"].queryset = queryset.order_by("name")
        self.fields["category"].label_from_instance = lambda obj: obj.name
        apply_widget_styling(self)


class EquipmentUnitForm(forms.ModelForm):
    class Meta:
        model = models.EquipmentUnit
        fields = (
            "catalog_item",
            "asset_code",
            "condition",
            "inventory_status",
        )

    def __init__(self, *args, catalog_items=None, **kwargs):
        super().__init__(*args, **kwargs)

        if catalog_items is not None:
            self.fields["catalog_item"].queryset = catalog_items.order_by(
                "category__name", "name"
            )

        self.fields["catalog_item"].label_from_instance = lambda item: (
            f"{item.name} ({item.category.name})"
        )

        apply_widget_styling(self)

    def clean_asset_code(self):
        value = self.cleaned_data["asset_code"].strip()
        matches = models.EquipmentUnit.objects.filter(asset_code__iexact=value)
        if self.instance.pk:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise forms.ValidationError(
                "An equipment unit with this asset code already exists."
            )
        return value

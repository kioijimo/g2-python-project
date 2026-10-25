from django import forms
from django.forms.models import BaseInlineFormSet, inlineformset_factory

from .. import models
from ..services.borrowing import due_date_bounds
from ..services.catalog import active_catalog_items, available_units_count
from .styling import apply_widget_styling


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = models.Profile
        fields = ("first_name", "last_name", "contact_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class CatalogSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=models.NAME_LENGTH,
        label="Search",
        widget=forms.TextInput(
            attrs={"placeholder": "Search by item or category"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class BorrowRequestForm(forms.Form):
    purpose = forms.CharField(
        max_length=models.DESCRIPTION_LENGTH,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    desired_return_date = forms.DateField(
        label="Desired return date",
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"},
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        min_date, max_date = due_date_bounds()
        self.fields["desired_return_date"].widget.attrs.update(
            {
                "min": min_date.isoformat(),
                "max": max_date.isoformat(),
            }
        )
        apply_widget_styling(self)

    def clean_desired_return_date(self):
        value = self.cleaned_data["desired_return_date"]
        min_date, max_date = due_date_bounds()

        if value < min_date:
            raise forms.ValidationError("Choose a date after today.")
        if value > max_date:
            raise forms.ValidationError(
                f"Choose a date on or before {max_date.isoformat()}."
            )
        return value


class BorrowRequestItemForm(forms.ModelForm):
    class Meta:
        model = models.RequestItem
        fields = ("catalog_item", "quantity")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        catalog_field = self.fields["catalog_item"]
        catalog_field.queryset = active_catalog_items()
        catalog_field.empty_label = "Select a catalog item"
        catalog_field.label_from_instance = (
            lambda item: f"{item.name} ({item.category.name}) - "
            f"{item.available_count} available"
        )
        apply_widget_styling(self)


class BaseBorrowRequestItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        settings = models.SystemSetting.load()
        selected_ids = set()
        selected_count = 0

        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data:
                continue

            catalog_item = data.get("catalog_item")
            quantity = data.get("quantity")

            if catalog_item is None and quantity is None:
                continue

            selected_count += 1

            if catalog_item is None:
                continue

            if catalog_item.pk in selected_ids:
                form.add_error(
                    "catalog_item",
                    "This item is already included in the request.",
                )
                continue

            selected_ids.add(catalog_item.pk)

            if quantity is None:
                continue

            if quantity > settings.max_borrow_quantity:
                form.add_error(
                    "quantity",
                    f"Maximum {settings.max_borrow_quantity} unit(s) per item.",
                )

            available = available_units_count(catalog_item)
            if quantity > available:
                form.add_error(
                    "quantity",
                    f"Only {available} unit(s) are currently available.",
                )

        if selected_count == 0:
            raise forms.ValidationError("Add at least one catalog item.")


BorrowRequestItemFormSet = inlineformset_factory(
    models.BorrowRequest,
    models.RequestItem,
    form=BorrowRequestItemForm,
    formset=BaseBorrowRequestItemFormSet,
    extra=3,
    max_num=3,
    validate_max=True,
    can_delete=False,
)

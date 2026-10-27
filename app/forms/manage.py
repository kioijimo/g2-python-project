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


class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        exclude = ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


class CategoryItemForm(forms.ModelForm):
    class Meta:
        model = models.CatalogItem
        exclude = ()

    def __init__(self, status=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"] = forms.ModelChoiceField(
            models.Category.objects.filter(status=status)
        )

        self.fields["category"].label_from_instance = lambda obj: obj.name
        apply_widget_styling(self)


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
        exclude = ("max_borrow_quantity",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)

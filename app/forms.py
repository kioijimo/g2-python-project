from django import forms
from django.contrib.auth.password_validation import validate_password

from . import models


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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = models.Profile
        exclude = ("user",)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        exclude = ("status",)


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

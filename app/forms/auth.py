from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .. import models
from .styling import FORM_INPUT_CLASS


class LoginForm(AuthenticationForm):
    """Email-based login form backed by Django's authentication form."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
                "class": FORM_INPUT_CLASS,
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": FORM_INPUT_CLASS,
            }
        ),
    )


class RegisterForm(forms.Form):
    """Create a basic account without exposing role or activation fields."""

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "class": FORM_INPUT_CLASS}
        )
    )
    first_name = forms.CharField(
        max_length=models.NAME_LENGTH,
        widget=forms.TextInput(attrs={"class": FORM_INPUT_CLASS}),
    )
    last_name = forms.CharField(
        max_length=models.NAME_LENGTH,
        widget=forms.TextInput(attrs={"class": FORM_INPUT_CLASS}),
    )
    contact_number = forms.CharField(
        max_length=models.CONTACT_NUM_LENGTH,
        widget=forms.TextInput(
            attrs={"placeholder": "09XXXXXXXXX", "class": FORM_INPUT_CLASS}
        ),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password", "class": FORM_INPUT_CLASS}
        ),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password", "class": FORM_INPUT_CLASS}
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if models.User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )
        return email

    def clean_contact_number(self):
        value = self.cleaned_data["contact_number"].strip()
        models.Profile._meta.get_field("contact_number").run_validators(value)
        return value

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two password fields didn't match.")
        elif password1:
            user = models.User(email=cleaned_data.get("email", ""))
            try:
                validate_password(password1, user)
            except ValidationError as error:
                self.add_error("password1", error)

        return cleaned_data

    def save(self):
        with transaction.atomic():
            user = models.User.objects.create_user(
                email=self.cleaned_data["email"],
                password=self.cleaned_data["password1"],
            )
            models.Profile.objects.create(
                user=user,
                first_name=self.cleaned_data["first_name"],
                last_name=self.cleaned_data["last_name"],
                contact_number=self.cleaned_data["contact_number"],
            )
        return user

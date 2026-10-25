from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from . import models

# Design System Form Widget Classes
FORM_INPUT_CLASS = (
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 "
    "placeholder-gray-400 shadow-sm transition-colors duration-150 "
    "focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
)

FORM_SELECT_CLASS = (
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 "
    "shadow-sm transition-colors duration-150 "
    "focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
)

FORM_TEXTAREA_CLASS = (
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 "
    "placeholder-gray-400 shadow-sm transition-colors duration-150 "
    "focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
)

FORM_CHECKBOX_CLASS = (
    "h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
)

# Backward-compatible alias
INPUT_CLASS = FORM_INPUT_CLASS


def apply_widget_styling(form):
    """Apply design system classes to all fields in a form according to widget type."""
    for field_name, field in form.fields.items():
        widget = field.widget
        if isinstance(widget, (forms.Select, forms.SelectMultiple)):
            css = FORM_SELECT_CLASS
        elif isinstance(widget, forms.Textarea):
            css = FORM_TEXTAREA_CLASS
        elif isinstance(widget, forms.CheckboxInput):
            css = FORM_CHECKBOX_CLASS
        else:
            css = FORM_INPUT_CLASS

        existing = widget.attrs.get("class", "")
        if existing:
            widget.attrs["class"] = f"{css} {existing}".strip()
        else:
            widget.attrs["class"] = css


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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = models.Profile
        exclude = ("user",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)


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

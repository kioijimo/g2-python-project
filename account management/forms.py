from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class RegisterForm(UserCreationForm):

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'contact_no',
            'password1',
            'password2'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        # Never allow admin registration
        user.role = 'USER'
        user.is_active = True

        if commit:
            user.save()

        return user

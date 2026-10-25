from django import forms

from .. import models
from .styling import apply_widget_styling


class ProfileForm(forms.ModelForm):
    class Meta:
        model = models.Profile
        exclude = ("user",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)

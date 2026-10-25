from .auth import LoginForm, RegisterForm
from .manage import CategoryForm, CategoryItemForm, UserForm
from .profile import ProfileForm
from .styling import (
    FORM_CHECKBOX_CLASS,
    FORM_INPUT_CLASS,
    FORM_SELECT_CLASS,
    FORM_TEXTAREA_CLASS,
    INPUT_CLASS,
    apply_widget_styling,
)

__all__ = [
    "CategoryForm",
    "CategoryItemForm",
    "FORM_CHECKBOX_CLASS",
    "FORM_INPUT_CLASS",
    "FORM_SELECT_CLASS",
    "FORM_TEXTAREA_CLASS",
    "INPUT_CLASS",
    "LoginForm",
    "ProfileForm",
    "RegisterForm",
    "UserForm",
    "apply_widget_styling",
]

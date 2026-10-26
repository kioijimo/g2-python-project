from .auth import LoginForm, RegisterForm
from .manage import (
    BorrowRequestFilterForm,
    CategoryForm,
    CategoryItemForm,
    UserForm,
)
from .portal import (
    BorrowRequestForm,
    BorrowRequestItemForm,
    BorrowRequestItemFormSet,
    CatalogSearchForm,
    ProfileUpdateForm,
)
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
    "BorrowRequestForm",
    "BorrowRequestItemForm",
    "BorrowRequestItemFormSet",
    "BorrowRequestFilterForm",
    "CatalogSearchForm",
    "CategoryForm",
    "CategoryItemForm",
    "FORM_CHECKBOX_CLASS",
    "FORM_INPUT_CLASS",
    "FORM_SELECT_CLASS",
    "FORM_TEXTAREA_CLASS",
    "INPUT_CLASS",
    "LoginForm",
    "ProfileForm",
    "ProfileUpdateForm",
    "RegisterForm",
    "UserForm",
    "apply_widget_styling",
]

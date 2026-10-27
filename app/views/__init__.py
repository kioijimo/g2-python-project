from .auth import login_view, logout_view, register_view
from .manage import (
    account_list,
    activate_user,
    deactivate_user,
    user_borrowing_history,
    borrow_request_approve,
    borrow_request_reject,
    borrow_request_release,
    borrow_request_review,
    borrow_request_slip,
    borrow_requests,
    catalogs,
    manage,
    sample,
)
from .portal import (
    catalog,
    portal_home,
    profile,
    request_create,
    request_detail,
    request_list,
)

__all__ = [
    "account_list",
    "activate_user",
    "deactivate_user",
    "user_borrowing_history",
    "catalog",  # For basic users
    "catalogs",  # Admin
    "login_view",
    "logout_view",
    "manage",
    "portal_home",
    "profile",
    "register_view",
    "request_create",
    "request_detail",
    "request_list",
    "borrow_requests",
    "borrow_request_review",
    "borrow_request_reject",
    "borrow_request_approve",
    "borrow_request_release",
    "borrow_request_slip",
    "sample",
]

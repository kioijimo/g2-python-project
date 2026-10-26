from django.urls import include, path
from django.views.generic import RedirectView

from .views.auth import login_view, logout_view
from .views.manage import (
    borrow_request_approve,
    borrow_request_reject,
    borrow_request_release,
    borrow_request_review,
    borrow_request_slip,
    borrow_requests,
    category,
    loans_list,
    manage,
    process_returns,
    sample,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("manage/", manage, name="manage"),
    path(
        "admin/",
        RedirectView.as_view(pattern_name="manage", permanent=False),
    ),
    path("category/", category, name="category"),
    path("sample/", sample, name="sample"),
    path("portal/", include("app.portal_urls")),
    path(route="manage/requests/", view=borrow_requests, name="borrow_requests"),
    path(
        "manage/requests/<int:pk>/",
        borrow_request_review,
        name="borrow_request_review",
    ),
    path(
        "manage/requests/<int:pk>/approve/",
        borrow_request_approve,
        name="borrow_request_approve",
    ),
    path(
        "manage/requests/<int:pk>/reject/",
        borrow_request_reject,
        name="borrow_request_reject",
    ),
    path(
        "manage/requests/<int:pk>/release/",
        borrow_request_release,
        name="borrow_request_release",
    ),
    path(
        "manage/requests/<int:pk>/slip/",
        borrow_request_slip,
        name="borrow_request_slip",
    ),
    path("manage/loans/", loans_list, name="loans_list"),
    path(
        "manage/loans/<int:request_id>/return/", process_returns, name="process_returns"
    ),
]

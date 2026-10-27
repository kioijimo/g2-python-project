from django.urls import include, path
from django.views.generic import RedirectView

from .views.auth import login_view, logout_view
from .views.manage import (
    audit,
    borrow_request_approve,
    borrow_request_reject,
    borrow_request_release,
    borrow_request_review,
    borrow_request_slip,
    borrow_requests,
    catalogs,
    loans_list,
    maintenance_manage_view,
    manage,
    open_maintenance_ticket,
    process_returns,
    process_unit_return,
    resolve_maintenance_ticket,
    returns_manage_view,
    sample,
    settings,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path(
        "admin/",
        RedirectView.as_view(pattern_name="manage", permanent=False),
    ),
    path("sample/", sample, name="sample"),
    path("portal/", include("app.portal_urls")),
    path("manage/", manage, name="manage"),
    path(route="manage/catalogs", view=catalogs, name="catalogs"),
    path(route="manage/catalogs/<str:view>", view=catalogs, name="catalogs_view"),
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
    path("manage/returns/", returns_manage_view, name="manage_returns"),
    path("manage/returns/process/", process_unit_return, name="process_unit_return"),
    path("manage/maintenance/", maintenance_manage_view, name="manage_maintenance"),
    path(
        "manage/maintenance/open/",
        open_maintenance_ticket,
        name="open_maintenance_ticket",
    ),
    path(
        "manage/maintenance/<int:ticket_id>/resolve/",
        resolve_maintenance_ticket,
        name="resolve_maintenance_ticket",
    ),
    path(route="manage/audit", view=audit, name="audit"),
    path(route="manage/settings", view=settings, name="settings"),
]

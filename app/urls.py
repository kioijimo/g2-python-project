from django.urls import include, path
from django.views.generic import RedirectView

from .views.auth import login_view, logout_view
from .views.manage import (
    category,
    manage,
    sample,
    returns_manage_view,
    process_unit_return,
    maintenance_manage_view,
    open_maintenance_ticket,
    resolve_maintenance_ticket,
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
    path('manage/returns/', returns_manage_view, name='manage_returns'),
    path('manage/returns/process/', process_unit_return, name='process_unit_return'),
    path('manage/maintenance/', maintenance_manage_view, name='manage_maintenance'),
    path('manage/maintenance/open/', open_maintenance_ticket, name='open_maintenance_ticket'),
    path('manage/maintenance/<int:ticket_id>/resolve/', resolve_maintenance_ticket,name='resolve_maintenance_ticket'),
]

from django.urls import include, path
from django.views.generic import RedirectView

from .views.auth import login_view, logout_view
from .views.manage import category, manage, sample

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
]

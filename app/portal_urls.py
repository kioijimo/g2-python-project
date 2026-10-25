from django.urls import path

from .views.auth import register_view
from .views.portal import (
    catalog,
    portal_home,
    profile,
    request_cancel,
    request_create,
    request_detail,
    request_list,
)

app_name = "portal"

urlpatterns = [
    path("", portal_home, name="home"),
    path("register/", register_view, name="register"),
    path("catalog/", catalog, name="catalog"),
    path("profile/", profile, name="profile"),
    path("requests/", request_list, name="request_list"),
    path("requests/new/", request_create, name="request_create"),
    path("requests/<int:pk>/", request_detail, name="request_detail"),
    path("requests/<int:pk>/cancel/", request_cancel, name="request_cancel"),
]

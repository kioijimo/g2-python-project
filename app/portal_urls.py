from django.urls import path

from .views.auth import register_view
from .views.portal import portal_home

app_name = "portal"

urlpatterns = [
    path("", portal_home, name="home"),
    path("register/", register_view, name="register"),
]

from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.portal_home, name="home"),
    path("register/", views.register_view, name="register"),
]

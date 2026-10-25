from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from .. import forms
from ..decorators import redirect_for_user


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_active:
            return redirect_for_user(request.user)
        auth_logout(request)

    form = forms.LoginForm(request=request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        return redirect_for_user(user)

    return render(request, "auth/login.html", {"form": form})


@require_POST
def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        if request.user.is_active:
            return redirect_for_user(request.user)
        auth_logout(request)

    form = forms.RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("portal:home")

    return render(request, "auth/register.html", {"form": form})

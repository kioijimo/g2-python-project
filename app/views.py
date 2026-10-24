from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from . import forms, models
from .decorators import admin_required, basic_user_required, redirect_for_user


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

    return render(request, "login.html", {"form": form})


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

    return render(request, "register.html", {"form": form})


@basic_user_required
def portal_home(request):
    return render(request, "portal/home.html")


@admin_required
def manage(request):
    context = {}

    user_form = forms.UserForm(request.POST or None)
    profile_form = forms.ProfileForm(data=request.POST or None)

    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user = user_form.save()
        profile = profile_form.save(commit=False)
        profile.user = user
        profile.save()

        user_form = forms.UserForm()
        profile_form = forms.ProfileForm()
        messages.success(request, "Account created successfully.")

    context["forms"] = {"user": user_form, "profile": profile_form}

    return render(request, "manage/home.html", context)


@admin_required
def category(request):
    context = {}

    catalog_item_form = forms.CategoryItemForm(
        data=request.POST or None,
        status=models.CatalogItem.CatalogItemStatus.ACTIVE,
    )

    if request.method == "POST" and catalog_item_form.is_valid():
        catalog_item_form.save()

        catalog_item_form = forms.CategoryItemForm(
            status=models.CatalogItem.CatalogItemStatus.ACTIVE
        )

        messages.success(request, "Added category item successfully.")

    context["forms"] = {"catalog_item": catalog_item_form}

    return render(request, "category.html", context)

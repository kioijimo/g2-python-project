from django.contrib import messages
from django.shortcuts import render

from .. import forms, models
from ..decorators import admin_required


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

    return render(request, "manage/catalog.html", context)

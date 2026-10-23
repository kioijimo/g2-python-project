from django.contrib import messages
from django.shortcuts import render

<<<<<<< Updated upstream
=======
from . import forms, models

>>>>>>> Stashed changes

def login(request):
    # Sample MTV with tailwindcss

    return render(request, "login.html")


def admin(request):
<<<<<<< Updated upstream
    return render(request, template_name="admin.html")
=======
    context = {}

    user_form = forms.UserForm(request.POST or None, authorized=True)
    profile_form = forms.ProfileForm(request.POST or None)

    if user_form.is_valid() and profile_form.is_valid():
        user = user_form.save()
        profile = profile_form.save(commit=False)
        profile.user = user
        profile.save()

        user_form = forms.UserForm()
        profile_form = forms.ProfileForm()
        messages.success(request, "Account created successfully.")

    context["forms"] = {"user": user_form, "profile": profile_form}

    return render(request, "admin.html", context)


def category(request):
    context = {}

    catalogItemForm = forms.CategoryItemForm(
        data=request.POST or None, status=models.CatalogItem.CatalogItemStatus.ACTIVE
    )

    if catalogItemForm.is_valid():
        catalogItemForm.save()

        catalogItemForm = forms.CategoryItemForm(
            status=models.CatalogItem.CatalogItemStatus.ACTIVE
        )

        messages.success(request, "Added category item successfully.")

    context["forms"] = {"catalog_item": catalogItemForm}

    return render(request, "category.html", context)
>>>>>>> Stashed changes

from django.contrib import messages
from django.shortcuts import redirect, render

from .. import forms, models
from ..decorators import basic_user_required
from ..services.catalog import active_catalog_items


def _placeholder(request, title, description):
    return render(
        request,
        "portal/placeholder.html",
        {
            "page_title": title,
            "page_description": description,
        },
    )


@basic_user_required
def portal_home(request):
    return render(request, "portal/home.html")


@basic_user_required
def catalog(request):
    search_form = forms.CatalogSearchForm(request.GET or None)
    query = ""

    if search_form.is_valid():
        query = search_form.cleaned_data["q"].strip()

    return render(
        request,
        "portal/catalog.html",
        {
            "search_form": search_form,
            "query": query,
            "items": active_catalog_items(query),
        },
    )


@basic_user_required
def profile(request):
    profile_record = models.Profile.objects.filter(user=request.user).first()
    form = forms.ProfileUpdateForm(
        request.POST if request.method == "POST" else None,
        instance=profile_record,
    )

    if request.method == "POST" and form.is_valid():
        profile_record = form.save(commit=False)
        profile_record.user = request.user
        profile_record.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("portal:profile")

    return render(
        request,
        "portal/profile.html",
        {
            "form": form,
        },
    )


@basic_user_required
def request_create(request):
    return _placeholder(
        request,
        "New Request",
        "Submit a new equipment borrowing request.",
    )


@basic_user_required
def request_list(request):
    return _placeholder(
        request,
        "My Requests",
        "Review the borrowing requests you have submitted.",
    )


@basic_user_required
def request_detail(request, pk):
    return _placeholder(
        request,
        "Request Details",
        f"View the details of request #{pk}.",
    )

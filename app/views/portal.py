from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .. import forms, models
from ..decorators import basic_user_required
from ..services.borrowing import create_borrow_request, due_at_for_date
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
    initial = []
    item_id = request.GET.get("item", "")

    if item_id.isdigit():
        selected_item = active_catalog_items().filter(pk=item_id).first()
        if selected_item:
            initial = [{"catalog_item": selected_item.pk}]

    form = forms.BorrowRequestForm(
        request.POST if request.method == "POST" else None
    )
    formset = forms.BorrowRequestItemFormSet(
        request.POST if request.method == "POST" else None,
        instance=models.BorrowRequest(),
        initial=initial,
    )

    if request.method == "POST":
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()

        if form_valid and formset_valid:
            items = []

            for item_form in formset.forms:
                data = item_form.cleaned_data
                if data and data.get("catalog_item"):
                    items.append((data["catalog_item"], data["quantity"]))

            try:
                borrow_request = create_borrow_request(
                    request.user,
                    form.cleaned_data["purpose"],
                    due_at_for_date(form.cleaned_data["desired_return_date"]),
                    items,
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "Borrow request submitted successfully.")
                return redirect("portal:request_detail", pk=borrow_request.pk)

    settings = models.SystemSetting.load()

    return render(
        request,
        "portal/request_form.html",
        {
            "form": form,
            "formset": formset,
            "max_borrow_quantity": settings.max_borrow_quantity,
            "max_borrow_days": settings.max_borrow_days,
        },
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

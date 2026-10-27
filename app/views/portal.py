from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .. import forms, models
from ..decorators import basic_user_required
from ..services.borrowing import (
    cancel_borrow_request,
    create_borrow_request,
    due_at_for_date,
)
from ..services.catalog import active_catalog_items


@basic_user_required
def portal_home(request):
    return render(request, "portal/home.html")


@basic_user_required
def catalog(request):
    filter_form = forms.CatalogFilterForm(request.GET or None)
    query = ""
    selected_category = None

    if filter_form.is_valid():
        query = filter_form.cleaned_data["q"].strip()
        selected_category = filter_form.cleaned_data["category"]

    return render(
        request,
        "portal/catalog.html",
        {
            "filter_form": filter_form,
            "query": query,
            "selected_category": selected_category,
            "items": active_catalog_items(
                category=selected_category,
                search=query,
            ),
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
            "max_borrow_days": settings.max_borrow_days,
        },
    )


@basic_user_required
def request_list(request):
    borrow_requests = (
        models.BorrowRequest.objects.filter(user=request.user)
        .prefetch_related("items__catalog_item")
        .order_by("-created_at")
    )

    return render(
        request,
        "portal/request_list.html",
        {
            "borrow_requests": borrow_requests,
        },
    )


@basic_user_required
def request_detail(request, pk):
    borrow_request = get_object_or_404(
        models.BorrowRequest.objects.select_related("user").prefetch_related(
            "items__catalog_item__category",
            "items__allocations__equipment_unit",
        ),
        pk=pk,
        user=request.user,
    )

    return render(
        request,
        "portal/request_detail.html",
        {
            "borrow_request": borrow_request,
            "overdue_days": borrow_request.overdue_days(),
        },
    )


@basic_user_required
@require_POST
def request_cancel(request, pk):
    borrow_request = get_object_or_404(
        models.BorrowRequest,
        pk=pk,
        user=request.user,
    )

    try:
        cancel_borrow_request(borrow_request)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Borrow request cancelled successfully.")

    return redirect("portal:request_detail", pk=pk)

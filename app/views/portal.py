from django.shortcuts import render

from ..decorators import basic_user_required


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
    return _placeholder(
        request,
        "Catalog",
        "Browse the equipment catalog and check current availability.",
    )


@basic_user_required
def profile(request):
    return _placeholder(
        request,
        "Profile",
        "Update your personal details and contact information.",
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

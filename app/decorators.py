from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import User


def _inactive_response(request):
    logout(request)
    messages.error(
        request,
        "Your account is inactive. Please contact an administrator.",
    )
    return redirect("login")


def active_account_required(view_func):
    """Require an authenticated account that is still active."""

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_active:
            return _inactive_response(request)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def basic_user_required(view_func):
    """Allow active basic users only; admins are sent to the manage area."""

    @active_account_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role != User.UserRoles.USER:
            return redirect("manage")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def admin_required(view_func):
    """Allow active administrators only; everyone else goes to the portal."""

    @active_account_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role != User.UserRoles.ADMIN:
            return redirect("portal:home")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def redirect_for_user(user):
    """Send each role to its own home after authentication."""
    if user.role == User.UserRoles.ADMIN:
        return redirect("manage")
    return redirect("portal:home")

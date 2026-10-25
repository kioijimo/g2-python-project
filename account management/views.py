from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import User


@login_required
def account_list(request):

    search = request.GET.get('search')

    users = User.objects.filter(role='USER')

    if search:
        users = users.filter(
            username__icontains=search
        )

    context = {
        'users': users
    }

    return render(
        request,
        'account/account_list.html',
        context
    )


@login_required
def activate_user(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    user.is_active = True
    user.save()

    return redirect('account_list')


@login_required
def deactivate_user(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    user.is_active = False
    user.save()

    return redirect('account_list')
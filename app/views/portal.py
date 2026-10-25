from django.shortcuts import render

from ..decorators import basic_user_required


@basic_user_required
def portal_home(request):
    return render(request, "portal/home.html")

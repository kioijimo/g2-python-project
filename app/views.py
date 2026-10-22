from django.shortcuts import render


def login(request):
    # Sample MTV with tailwindcss

    return render(request, "login.html")


def admin(request):
    return render(request, template_name="admin.html")

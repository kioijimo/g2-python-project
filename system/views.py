from django.shortcuts import render


# Sample MTV with tailwindcss
def login(request):
    return render(request, "login.html")


def admin(request):
    return render(request, template_name="admin.html")

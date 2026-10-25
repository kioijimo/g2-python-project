from django.urls import path
from . import views

urlpatterns = [

    path(
        'units/',
        views.unit_list,
        name='unit_list'
    ),

]
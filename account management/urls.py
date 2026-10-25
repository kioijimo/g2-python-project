from django.urls import path
from . import views

urlpatterns = [

    path(
        '',
        views.account_list,
        name='account_list'
    ),

    path(
        'activate/<int:pk>/',
        views.activate_user,
        name='activate_user'
    ),

    path(
        'deactivate/<int:pk>/',
        views.deactivate_user,
        name='deactivate_user'
    ),

]
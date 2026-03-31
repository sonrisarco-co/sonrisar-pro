from django.urls import path
from . import views

urlpatterns = [
    path('', views.prosthesis_list, name='prosthesis_list'),
]

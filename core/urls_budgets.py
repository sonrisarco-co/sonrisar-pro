from django.urls import path
from . import views

urlpatterns = [
    path('', views.budgets_list, name='budgets_list'),
]


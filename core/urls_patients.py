from django.urls import path
from . import views

urlpatterns = [
    path('', views.patients_list, name='patients_list'),
    path('nuevo/', views.patient_new, name='patient_new'),
    path('editar/<int:pk>/', views.patient_edit, name='patient_edit'),
    path('borrar/<int:pk>/', views.patient_delete, name='patient_delete'),
]

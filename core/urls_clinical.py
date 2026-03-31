from django.urls import path
from . import views

urlpatterns = [
    path('', views.clinical_records_list, name='clinical_records_list'),
    path('nuevo/', views.clinical_record_new, name='clinical_record_new'),
    path('editar/<int:pk>/', views.clinical_record_edit, name='clinical_record_edit'),
    path('borrar/<int:pk>/', views.clinical_record_delete, name='clinical_record_delete'),
]

from django.urls import path
from .views import api_clinical_records
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [

    path("clinical-records/<int:patient_id>/", api_clinical_records, name="api_clinical_records"),
    
    # LOGIN JWT
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]


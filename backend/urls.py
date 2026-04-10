from django.contrib import admin
from django.urls import path, include
from core import views as core_views


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('core.urls')),

    path('api/', include('core.api.urls')),

    path("service-worker.js", core_views.service_worker, name="service-worker"),

    

]

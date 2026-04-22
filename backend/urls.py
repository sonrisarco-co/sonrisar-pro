from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('core.urls')),

    path('api/', include('core.api.urls')),

    path("service-worker.js", core_views.service_worker, name="service-worker"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
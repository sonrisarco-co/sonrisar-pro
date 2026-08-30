from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path
from core import views as core_views


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('core.urls')),

    path('api/', include('core.api.urls')),

    path("service-worker.js", core_views.service_worker, name="service-worker"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Los archivos subidos no son servidos por WhiteNoise. En producción,
    # Django atiende /media/ desde el disco persistente montado en /var/data.
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]

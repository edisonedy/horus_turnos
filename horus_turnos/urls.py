from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('apps.core.urls')),
    path('', include('apps.negocios.urls')),
    path('', include('apps.agenda.urls')),
    path('', include('apps.whatsapp_api.panel_urls')),
    path('', include('apps.bot_turnos.urls')),
    path('whatsapp/', include('apps.whatsapp_api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

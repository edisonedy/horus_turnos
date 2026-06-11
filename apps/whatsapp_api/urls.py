from django.urls import path
from . import views
from .webhook import whatsapp_webhook

urlpatterns = [
    path('webhook/', whatsapp_webhook, name='whatsapp_webhook'),
    path('probar-envio/', views.probar_envio_whatsapp, name='probar_envio'),
]

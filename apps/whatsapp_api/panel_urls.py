from django.urls import path
from . import views

urlpatterns = [
    path('panel/whatsapp/', views.configuracion_whatsapp, name='configuracion_whatsapp'),
    path('panel/conversaciones/', views.conversaciones, name='conversaciones'),
    path('panel/conversaciones/<int:conversacion_id>/', views.conversacion_detalle, name='conversacion_detalle'),
    path('panel/recordatorios/', views.recordatorios, name='recordatorios'),
    path('panel/errores-whatsapp/', views.errores_webhook, name='errores_webhook'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('panel/simulador/', views.simulador, name='simulador_bot'),
    path('panel/simulador/mensaje/', views.simulador_mensaje, name='simulador_bot_mensaje'),
    path('panel/simulador/reset/', views.simulador_reset, name='simulador_bot_reset'),
]

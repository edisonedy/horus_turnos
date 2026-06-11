from django.urls import path
from . import views

urlpatterns = [
    path('panel/negocio/', views.configuracion_negocio, name='configuracion_negocio'),
    path('panel/configuracion/', views.configuracion_negocio, name='configuracion_panel'),
    path('panel/horarios/', views.horarios, name='horarios'),
    path('panel/horarios/<int:horario_id>/', views.horarios, name='horario_editar'),
]

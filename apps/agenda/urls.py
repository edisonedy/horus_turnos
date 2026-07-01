from django.urls import path
from . import views

urlpatterns = [
    path('panel/servicios/', views.servicios, name='servicios'),
    path('panel/servicios/<int:servicio_id>/', views.servicios, name='servicio_editar'),
    path('panel/productos/', views.productos, name='productos'),
    path('panel/productos/<int:producto_id>/', views.productos, name='producto_editar'),
    path('panel/preguntas-frecuentes/', views.preguntas_frecuentes, name='preguntas_frecuentes'),
    path('panel/preguntas-frecuentes/<int:pregunta_id>/', views.preguntas_frecuentes, name='pregunta_frecuente_editar'),
    path('panel/promociones/', views.promociones, name='promociones'),
    path('panel/promociones/<int:promocion_id>/', views.promociones, name='promocion_editar'),
    path('panel/pedidos/', views.pedidos, name='pedidos'),
    path('panel/pedidos/<int:pedido_id>/', views.pedidos, name='pedido_editar'),
    path('panel/profesionales/', views.profesionales, name='profesionales'),
    path('panel/profesionales/<int:profesional_id>/', views.profesionales, name='profesional_editar'),
    path('panel/clientes/', views.clientes, name='clientes'),
    path('panel/clientes/<int:cliente_id>/', views.cliente_detalle, name='cliente_detalle'),
    path('panel/controles/', views.controles, name='controles'),
    path('panel/retencion/', views.retencion, name='retencion'),
    path('panel/reactivar/', views.reactivar, name='reactivar'),
    path('panel/turnos/', views.turnos, name='turnos'),
    path('panel/turnos/<int:turno_id>/', views.turnos, name='turno_editar'),
]

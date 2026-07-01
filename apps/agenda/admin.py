from django.contrib import admin
from .models import BloqueoHorario, Cliente, ListaEspera, PedidoWhatsApp, PreguntaFrecuente, Producto, Profesional, PromocionWhatsApp, RegistroAtencion, Servicio, Turno


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'negocio', 'sucursal', 'telefono', 'especialidad', 'activo')
    list_filter = ('negocio', 'sucursal', 'activo')
    search_fields = ('nombre', 'telefono', 'especialidad')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'negocio', 'duracion_minutos', 'precio', 'activo')
    list_filter = ('negocio', 'activo')
    search_fields = ('nombre', 'descripcion')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'negocio', 'precio', 'stock', 'activo', 'permite_pedido_whatsapp')
    list_filter = ('negocio', 'activo', 'permite_pedido_whatsapp')
    search_fields = ('nombre', 'descripcion')


@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(admin.ModelAdmin):
    list_display = ('pregunta', 'negocio', 'orden', 'activo')
    list_filter = ('negocio', 'activo')
    search_fields = ('pregunta', 'respuesta', 'palabras_clave')


@admin.register(PromocionWhatsApp)
class PromocionWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'negocio', 'codigo', 'fecha_inicio', 'fecha_fin', 'orden', 'activo')
    list_filter = ('negocio', 'activo', 'fecha_inicio', 'fecha_fin')
    search_fields = ('titulo', 'descripcion', 'codigo')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email', 'negocio', 'fecha_creacion')
    list_filter = ('negocio',)
    search_fields = ('nombre', 'telefono', 'email')


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'servicio', 'profesional', 'negocio', 'fecha_hora_inicio', 'estado', 'origen')
    list_filter = ('negocio', 'estado', 'origen', 'fecha_hora_inicio')
    search_fields = ('cliente__nombre', 'cliente__telefono', 'servicio__nombre', 'profesional__nombre')
    date_hierarchy = 'fecha_hora_inicio'


@admin.register(PedidoWhatsApp)
class PedidoWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'producto', 'cantidad', 'total', 'negocio', 'estado', 'fecha_creacion')
    list_filter = ('negocio', 'estado', 'fecha_creacion')
    search_fields = ('cliente__nombre', 'cliente__telefono', 'producto__nombre')
    date_hierarchy = 'fecha_creacion'


@admin.register(ListaEspera)
class ListaEsperaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'servicio', 'negocio', 'fecha_deseada', 'estado', 'fecha_creacion')
    list_filter = ('negocio', 'estado', 'fecha_deseada')
    search_fields = ('cliente__nombre', 'cliente__telefono', 'servicio__nombre')


@admin.register(RegistroAtencion)
class RegistroAtencionAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'fecha', 'servicio', 'producto', 'producto_accion', 'proximo_control', 'profesional', 'negocio')
    list_filter = ('negocio', 'producto_accion', 'fecha', 'proximo_control')
    search_fields = ('cliente__nombre', 'cliente__telefono', 'descripcion', 'producto_libre')
    date_hierarchy = 'fecha'


@admin.register(BloqueoHorario)
class BloqueoHorarioAdmin(admin.ModelAdmin):
    list_display = ('negocio', 'profesional', 'fecha_hora_inicio', 'fecha_hora_fin', 'activo', 'motivo')
    list_filter = ('negocio', 'activo', 'fecha_hora_inicio')
    search_fields = ('motivo', 'profesional__nombre')

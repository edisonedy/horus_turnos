from django.contrib import admin
from .models import ConfiguracionNegocioBot, HorarioAtencion, Negocio, Sucursal


class SucursalInline(admin.TabularInline):
    model = Sucursal
    extra = 0


class HorarioAtencionInline(admin.TabularInline):
    model = HorarioAtencion
    extra = 0


@admin.register(Negocio)
class NegocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'propietario', 'telefono_principal', 'telefono_whatsapp', 'activo', 'fecha_creacion')
    list_filter = ('activo',)
    search_fields = ('nombre', 'telefono_principal', 'telefono_whatsapp', 'propietario__username')
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [SucursalInline, HorarioAtencionInline]


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'negocio', 'telefono', 'activo')
    list_filter = ('activo', 'negocio')
    search_fields = ('nombre', 'direccion', 'telefono')


@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    list_display = ('negocio', 'sucursal', 'dia_semana', 'hora_inicio', 'hora_fin', 'activo')
    list_filter = ('negocio', 'dia_semana', 'activo')


@admin.register(ConfiguracionNegocioBot)
class ConfiguracionNegocioBotAdmin(admin.ModelAdmin):
    list_display = (
        'negocio',
        'permite_agendar_automatico',
        'requiere_confirmacion_manual',
        'envia_recordatorio_24h',
        'envia_recordatorio_2h',
        'notificar_dueno_whatsapp',
    )
    list_filter = ('permite_agendar_automatico', 'requiere_confirmacion_manual', 'notificar_dueno_whatsapp')

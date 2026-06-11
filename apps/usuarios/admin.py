from django.contrib import admin
from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'telefono', 'recibe_notificaciones', 'fecha_creacion')
    search_fields = ('usuario__username', 'usuario__email', 'telefono')
    list_filter = ('recibe_notificaciones',)

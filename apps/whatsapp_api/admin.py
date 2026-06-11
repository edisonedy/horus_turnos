from django.contrib import admin
from .models import (
    ConfiguracionWhatsApp,
    ConversacionWhatsApp,
    ErrorWebhookWhatsApp,
    MensajeWhatsApp,
    RecordatorioWhatsApp,
)


@admin.register(ConfiguracionWhatsApp)
class ConfiguracionWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('negocio', 'phone_number_id', 'business_account_id', 'numero_whatsapp', 'activo')
    list_filter = ('activo',)
    search_fields = ('negocio__nombre', 'phone_number_id', 'business_account_id', 'numero_whatsapp')


@admin.register(MensajeWhatsApp)
class MensajeWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('negocio', 'cliente', 'tipo', 'telefono', 'estado', 'fecha_creacion')
    list_filter = ('negocio', 'tipo', 'estado', 'fecha_creacion')
    search_fields = ('telefono', 'mensaje', 'whatsapp_message_id', 'cliente__nombre')
    readonly_fields = ('payload', 'fecha_creacion')


@admin.register(ConversacionWhatsApp)
class ConversacionWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('negocio', 'cliente', 'estado', 'actualizado')
    list_filter = ('negocio', 'estado', 'actualizado')
    search_fields = ('cliente__nombre', 'cliente__telefono')
    readonly_fields = ('datos', 'actualizado')


@admin.register(RecordatorioWhatsApp)
class RecordatorioWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('turno', 'tipo', 'fecha_programada', 'enviado', 'intentos')
    list_filter = ('tipo', 'enviado', 'fecha_programada')
    search_fields = ('turno__cliente__nombre', 'turno__cliente__telefono')


@admin.register(ErrorWebhookWhatsApp)
class ErrorWebhookWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('negocio', 'phone_number_id', 'resuelto', 'fecha_creacion')
    list_filter = ('resuelto', 'fecha_creacion')
    search_fields = ('phone_number_id', 'error')
    readonly_fields = ('payload', 'fecha_creacion')

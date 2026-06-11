from .models import PerfilUsuario


def perfil_usuario(usuario):
    return PerfilUsuario.objects.filter(usuario=usuario).first()

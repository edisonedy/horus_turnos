"""Lista los usuarios del sistema (para saber con cuál entrar al panel).

Uso:  python manage.py listar_usuarios
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Muestra los usuarios existentes y si son administradores.'

    def handle(self, *args, **options):
        User = get_user_model()
        usuarios = User.objects.all().order_by('username')
        if not usuarios:
            self.stdout.write(self.style.WARNING(
                'No hay usuarios. Corre: python manage.py crear_daya'))
            return
        self.stdout.write(f'Usuarios ({usuarios.count()}):')
        for u in usuarios:
            rol = 'superusuario' if u.is_superuser else ('staff' if u.is_staff else 'normal')
            estado = 'activo' if u.is_active else 'inactivo'
            self.stdout.write(f'  - {u.username}  ({rol}, {estado})  {u.email}')

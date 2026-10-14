from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
class Command(BaseCommand):
    help = 'Crea Andrés, Rodrigo y Geisha con contraseñas individuales, sin modificar usuarios existentes.'
    @transaction.atomic
    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name='Responsables Sonrisar')
        for username, name, responsible in [('andres','Andrés',True),('rodrigo','Rodrigo',True),('geisha','Geisha',False)]:
            User = get_user_model()
            if User.objects.filter(username=username).exists():
                raise CommandError(f'Ya existe {username}. No se modificó ningún usuario. Revisar sus permisos antes de continuar.')
            user = User(username=username, first_name=name, is_staff=False, is_superuser=False)
            while True:
                password = getpass(f'Contraseña para {name}: ')
                if password != getpass('Repetir contraseña: '):
                    self.stdout.write('Las contraseñas no coinciden.'); continue
                try: validate_password(password, user)
                except ValidationError as exc:
                    self.stdout.write('; '.join(exc.messages)); continue
                break
            user.set_password(password); user.save()
            if responsible: user.groups.add(group)
        self.stdout.write(self.style.SUCCESS('Tres usuarios creados correctamente.'))

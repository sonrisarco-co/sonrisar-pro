import os
import django

# 1) Configurar Django
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

# 2) Importar tu tarea real
from core.tasks import enviar_recordatorios_automaticos

# 3) Ejecutarla
if __name__ == "__main__":
    enviar_recordatorios_automaticos()

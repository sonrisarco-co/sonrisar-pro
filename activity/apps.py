from django.apps import AppConfig
class ActivityConfig(AppConfig):
    name = 'activity'
    default_auto_field = 'django.db.models.BigAutoField'
    def ready(self):
        from . import signals
